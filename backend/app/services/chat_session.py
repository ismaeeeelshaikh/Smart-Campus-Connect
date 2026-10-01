from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from ..database import async_session
from ..models.chat_session import ChatSession, ChatMessage
from ..schemas.chat_session import ChatSessionResponse, ChatSessionDetail, ChatMessageResponse
from ..utils.sse import sse
from .rag import Answer, get_rag_service, History, MAX_HISTORY_TURNS
from typing import AsyncIterator, List
import logging
import re

logger = logging.getLogger(__name__)


def _message_response(message: ChatMessage) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        question=message.question,
        answer=message.answer,
        sources=message.sources or [],
        timestamp=message.timestamp,
    )


def _session_response(session: ChatSession, message_count: int) -> ChatSessionResponse:
    return ChatSessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=message_count,
    )


class ChatSessionService:
    @staticmethod
    def _generate_smart_title(question: str) -> str:
        """Generate a smart title from the user's first question"""
        question = question.strip()
        if len(question) > 50:
            words = question.split()[:6]
            title = " ".join(words)
            if not title.endswith(('?', '!', '.')):
                title += "..."
        else:
            title = question

        title = re.sub(r'^(what|how|can|tell|show|explain)\s+', '', title, flags=re.IGNORECASE).strip()
        if title:
            title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()
        else:
            title = "New Chat"
        if len(title) > 40:
            title = title[:37] + "..."
        return title

    @staticmethod
    async def _recent_history(session_id: int, db: AsyncSession) -> History:
        """Last few (question, answer) pairs of the session, oldest first."""
        result = await db.execute(
            select(ChatMessage.question, ChatMessage.answer)
            .filter(ChatMessage.chat_session_id == session_id)
            .order_by(desc(ChatMessage.timestamp), desc(ChatMessage.id))
            .limit(MAX_HISTORY_TURNS)
        )
        return [(q, a) for q, a in reversed(result.all())]

    @staticmethod
    async def create_chat_session(user_id: int, title: str, db: AsyncSession) -> ChatSessionResponse:
        chat_session = ChatSession(user_id=user_id, title=title or "New Chat")
        db.add(chat_session)
        await db.commit()
        await db.refresh(chat_session)
        return _session_response(chat_session, 0)

    # ---- new chat (first message) ----
    @staticmethod
    async def _save_new_session(user_id: int, question: str, answer: Answer, db: AsyncSession):
        chat_session = ChatSession(user_id=user_id, title=ChatSessionService._generate_smart_title(question))
        db.add(chat_session)
        await db.flush()  # get the session ID for the message
        message = ChatMessage(chat_session_id=chat_session.id, user_id=user_id, question=question,
                              answer=answer.text, sources=answer.sources)
        db.add(message)
        await db.commit()
        await db.refresh(chat_session)
        await db.refresh(message)
        return _session_response(chat_session, 1), _message_response(message)

    @staticmethod
    async def create_session_with_first_message(user_id: int, question: str, db: AsyncSession) -> tuple[ChatSessionResponse, ChatMessageResponse]:
        """Create a new session and add the first message - ChatGPT style"""
        # Get the AI answer first, so no DB transaction is held open while waiting for the LLM
        answer = await get_rag_service().answer(question, history=[])
        return await ChatSessionService._save_new_session(user_id, question, answer, db)

    @staticmethod
    async def stream_new_session(user_id: int, question: str) -> AsyncIterator[str]:
        """Same as create_session_with_first_message, but streams the answer as server-sent events."""
        try:
            answer = None
            async for piece in get_rag_service().stream(question, history=[]):
                if isinstance(piece, Answer):
                    answer = piece
                else:
                    yield sse("token", {"text": piece})
            async with async_session() as db:  # own session: the request's one may already be closed
                session, message = await ChatSessionService._save_new_session(user_id, question, answer, db)
            yield sse("done", {"session": session.model_dump(mode="json"), "message": message.model_dump(mode="json")})
        except Exception:
            logger.exception("Streaming a new chat failed")
            yield sse("error", {"detail": "Could not answer right now. Please try again."})

    # ---- follow-up messages ----
    @staticmethod
    async def get_history_for_message(session_id: int, user_id: int, db: AsyncSession) -> History:
        """Check the session belongs to the user and return its recent history. Raises ValueError."""
        session = (await db.execute(
            select(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )).scalar_one_or_none()
        if not session:
            raise ValueError("Chat session not found")
        history = await ChatSessionService._recent_history(session_id, db)
        # End the read transaction before the slow LLM call, so the DB connection isn't held
        await db.commit()
        return history

    @staticmethod
    async def _save_message(session_id: int, user_id: int, question: str, answer: Answer, db: AsyncSession) -> ChatMessageResponse:
        message = ChatMessage(chat_session_id=session_id, user_id=user_id, question=question,
                              answer=answer.text, sources=answer.sources)
        db.add(message)
        session = await db.get(ChatSession, session_id)
        if session is not None:
            session.updated_at = func.now()
        await db.commit()
        await db.refresh(message)
        return _message_response(message)

    @staticmethod
    async def add_message_to_session(session_id: int, user_id: int, question: str, db: AsyncSession) -> ChatMessageResponse:
        history = await ChatSessionService.get_history_for_message(session_id, user_id, db)
        answer = await get_rag_service().answer(question, history)
        return await ChatSessionService._save_message(session_id, user_id, question, answer, db)

    @staticmethod
    async def stream_message(session_id: int, user_id: int, question: str, history: History) -> AsyncIterator[str]:
        """Streams a follow-up answer (history already checked by get_history_for_message)."""
        try:
            answer = None
            async for piece in get_rag_service().stream(question, history):
                if isinstance(piece, Answer):
                    answer = piece
                else:
                    yield sse("token", {"text": piece})
            async with async_session() as db:
                message = await ChatSessionService._save_message(session_id, user_id, question, answer, db)
            yield sse("done", {"message": message.model_dump(mode="json")})
        except Exception:
            logger.exception("Streaming a follow-up message failed")
            yield sse("error", {"detail": "Could not answer right now. Please try again."})

    # ---- listing, rename, delete ----
    @staticmethod
    async def get_user_chat_sessions(user_id: int, db: AsyncSession) -> List[ChatSessionResponse]:
        # Only sessions that have messages, newest activity first
        result = await db.execute(
            select(ChatSession, func.count(ChatMessage.id).label('message_count'))
            .outerjoin(ChatMessage)
            .filter(ChatSession.user_id == user_id)
            .group_by(ChatSession.id)
            .having(func.count(ChatMessage.id) > 0)
            .order_by(desc(ChatSession.updated_at))
        )
        return [_session_response(session, count or 0) for session, count in result.all()]

    @staticmethod
    async def get_chat_session_detail(session_id: int, user_id: int, db: AsyncSession) -> ChatSessionDetail:
        session = (await db.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )).scalar_one_or_none()
        if not session:
            raise ValueError("Chat session not found")
        return ChatSessionDetail(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            messages=[_message_response(m) for m in sorted(session.messages, key=lambda x: (x.timestamp, x.id))],
        )

    @staticmethod
    async def update_session_title(session_id: int, user_id: int, title: str, db: AsyncSession) -> ChatSessionResponse:
        session = (await db.execute(
            select(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )).scalar_one_or_none()
        if not session:
            raise ValueError("Chat session not found")
        session.title = title
        session.updated_at = func.now()
        await db.commit()
        await db.refresh(session)
        return _session_response(session, 0)  # count isn't needed for a rename

    @staticmethod
    async def delete_chat_session(session_id: int, user_id: int, db: AsyncSession) -> bool:
        session = (await db.execute(
            select(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )).scalar_one_or_none()
        if not session:
            return False
        await db.delete(session)
        await db.commit()
        return True
