from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from ..models.chat_session import ChatSession, ChatMessage
from ..models.user import User
from ..schemas.chat_session import ChatSessionResponse, ChatSessionDetail, ChatMessageResponse
from .rag import rag_service
from typing import List
import logging
import re

logger = logging.getLogger(__name__)

class ChatSessionService:
    @staticmethod
    def _generate_smart_title(question: str) -> str:
        """Generate a smart title from the user's first question"""
        # Remove common question words and clean up
        question = question.strip()
        
        # Common patterns to create smart titles
        if len(question) > 50:
            # Take first meaningful part
            words = question.split()[:6]
            title = " ".join(words)
            if not title.endswith(('?', '!', '.')):
                title += "..."
        else:
            title = question
            
        # Clean up and capitalize
        title = re.sub(r'^(what|how|can|tell|show|explain)\s+', '', title, flags=re.IGNORECASE)
        title = title.strip()
        if title:
            title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()
        else:
            title = "New Chat"
            
        # Limit length
        if len(title) > 40:
            title = title[:37] + "..."
            
        return title

    @staticmethod
    async def create_chat_session(user_id: int, title: str, db: AsyncSession) -> ChatSessionResponse:
        # For ChatGPT-like experience, always create with provided title
        # Don't auto-generate "Chat X" numbers anymore
        if not title:
            title = "New Chat"
            
        chat_session = ChatSession(
            user_id=user_id,
            title=title
        )
        
        db.add(chat_session)
        await db.commit()
        await db.refresh(chat_session)
        
        return ChatSessionResponse(
            id=chat_session.id,
            title=chat_session.title,
            created_at=chat_session.created_at,
            updated_at=chat_session.updated_at,
            message_count=0
        )
        
    @staticmethod
    async def create_session_with_first_message(user_id: int, question: str, db: AsyncSession) -> tuple[ChatSessionResponse, ChatMessageResponse]:
        """Create a new session and add the first message - ChatGPT style"""
        # Generate smart title from the question
        smart_title = ChatSessionService._generate_smart_title(question)
        
        # Create the session
        chat_session = ChatSession(
            user_id=user_id,
            title=smart_title
        )
        
        db.add(chat_session)
        await db.flush()  # Get the ID without committing
        
        # Get AI response
        answer = rag_service.get_response_for_session(question, user_id, chat_session.id)
        
        # Save the first message
        message = ChatMessage(
            chat_session_id=chat_session.id,
            user_id=user_id,
            question=question,
            answer=answer
        )
        
        db.add(message)
        await db.commit()
        await db.refresh(chat_session)
        await db.refresh(message)
        
        session_response = ChatSessionResponse(
            id=chat_session.id,
            title=chat_session.title,
            created_at=chat_session.created_at,
            updated_at=chat_session.updated_at,
            message_count=1
        )
        
        message_response = ChatMessageResponse(
            id=message.id,
            question=message.question,
            answer=message.answer,
            timestamp=message.timestamp
        )
        
        return session_response, message_response
        
    @staticmethod
    async def get_user_chat_sessions(user_id: int, db: AsyncSession) -> List[ChatSessionResponse]:
        # Get sessions with message count - only return sessions that have messages
        result = await db.execute(
            select(
                ChatSession,
                func.count(ChatMessage.id).label('message_count')
            )
            .outerjoin(ChatMessage)
            .filter(ChatSession.user_id == user_id)
            .group_by(ChatSession.id)
            .having(func.count(ChatMessage.id) > 0)  # Only sessions with messages
            .order_by(desc(ChatSession.updated_at))
        )
        
        sessions_with_count = result.all()
        
        return [
            ChatSessionResponse(
                id=session.id,
                title=session.title,
                created_at=session.created_at,
                updated_at=session.updated_at,
                message_count=message_count or 0
            )
            for session, message_count in sessions_with_count
        ]
        
    @staticmethod
    async def get_chat_session_detail(session_id: int, user_id: int, db: AsyncSession) -> ChatSessionDetail:
        result = await db.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )
        
        session = result.scalar_one_or_none()
        if not session:
            raise ValueError("Chat session not found")
            
        return ChatSessionDetail(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            messages=[
                ChatMessageResponse(
                    id=msg.id,
                    question=msg.question,
                    answer=msg.answer,
                    timestamp=msg.timestamp
                ) 
                for msg in sorted(session.messages, key=lambda x: x.timestamp)
            ]
        )
        
    @staticmethod
    async def add_message_to_session(session_id: int, user_id: int, question: str, db: AsyncSession) -> ChatMessageResponse:
        # Verify session belongs to user
        result = await db.execute(
            select(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise ValueError("Chat session not found")
            
        # Get AI response using session-specific memory
        answer = rag_service.get_response_for_session(question, user_id, session_id)
        
        # Save message
        message = ChatMessage(
            chat_session_id=session_id,
            user_id=user_id,
            question=question,
            answer=answer
        )
        
        db.add(message)
        
        # Update session's updated_at timestamp
        session.updated_at = func.now()
        
        await db.commit()
        await db.refresh(message)
        
        return ChatMessageResponse(
            id=message.id,
            question=message.question,
            answer=message.answer,
            timestamp=message.timestamp
        )
        
    @staticmethod
    async def update_session_title(session_id: int, user_id: int, title: str, db: AsyncSession) -> ChatSessionResponse:
        result = await db.execute(
            select(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise ValueError("Chat session not found")
            
        session.title = title
        session.updated_at = func.now()
        
        await db.commit()
        await db.refresh(session)
        
        return ChatSessionResponse(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=0  # We don't need to calculate this for title update
        )
        
    @staticmethod
    async def delete_chat_session(session_id: int, user_id: int, db: AsyncSession) -> bool:
        result = await db.execute(
            select(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            return False
            
        # Clear session memory from RAG service
        rag_service.clear_session_memory(user_id, session_id)
        
        await db.delete(session)
        await db.commit()
        
        return True