from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..dependencies import get_current_user
from ..schemas.chat_session import (
    ChatSessionCreate, ChatSessionResponse, ChatSessionDetail,
    ChatSessionList, ChatMessageCreate, ChatMessageResponse, ChatSessionTitleUpdate)
from ..services.chat_session import ChatSessionService
from ..services.rag import AssistantBusy
from ..utils.sse import sse_response
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat-sessions", tags=["chat-sessions"])

NOT_FOUND = "Chat session not found"


def _server_error(action: str) -> HTTPException:
    # Full details go to the server log only; the user gets a generic message
    logger.exception(f"Error while trying to {action}")
    return HTTPException(status_code=500, detail=f"Could not {action}. Please try again.")


@router.post("", response_model=ChatSessionResponse)
async def create_chat_session(
    session_data: ChatSessionCreate,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    """Create a new chat session"""
    try:
        return await ChatSessionService.create_chat_session(user.id, session_data.title, db)
    except Exception:
        raise _server_error("create the chat")

@router.post("/start", response_model=dict)
async def start_chat_session(
    message: ChatMessageCreate,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    """Start a new chat session with first message (ChatGPT-like)"""
    try:
        session_response, message_response = await ChatSessionService.create_session_with_first_message(
            user.id, message.question, db
        )
        logger.info(f"Chat session {session_response.id} started for user {user.id}")
        return {"session": session_response, "message": message_response}
    except AssistantBusy:
        raise HTTPException(status_code=503, detail=AssistantBusy.USER_MESSAGE)
    except Exception:
        raise _server_error("start the chat")

@router.post("/start/stream")
async def start_chat_session_stream(message: ChatMessageCreate, user=Depends(get_current_user)):
    """Like /start, but the answer arrives word by word as server-sent events
    ("token" events, then "done" with the saved session and message)."""
    return sse_response(ChatSessionService.stream_new_session(user.id, message.question))

@router.get("", response_model=ChatSessionList)
async def get_chat_sessions(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    """Get all chat sessions for the user"""
    try:
        sessions = await ChatSessionService.get_user_chat_sessions(user.id, db)
        return ChatSessionList(sessions=sessions)
    except Exception:
        raise _server_error("load your chats")

@router.get("/{session_id}", response_model=ChatSessionDetail)
async def get_chat_session_detail(
    session_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    """Get specific chat session with all messages"""
    try:
        return await ChatSessionService.get_chat_session_detail(session_id, user.id, db)
    except ValueError:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    except Exception:
        raise _server_error("load this chat")

@router.post("/{session_id}/messages", response_model=ChatMessageResponse)
async def send_message_to_session(
    session_id: int,
    message: ChatMessageCreate,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    """Send a message to a specific chat session"""
    try:
        return await ChatSessionService.add_message_to_session(session_id, user.id, message.question, db)
    except ValueError:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    except AssistantBusy:
        raise HTTPException(status_code=503, detail=AssistantBusy.USER_MESSAGE)
    except Exception:
        raise _server_error("send your message")

@router.post("/{session_id}/messages/stream")
async def send_message_to_session_stream(
    session_id: int,
    message: ChatMessageCreate,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    """Like /messages, but streamed as server-sent events ("token" ..., then "done")."""
    try:
        history = await ChatSessionService.get_history_for_message(session_id, user.id, db)
    except ValueError:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return sse_response(ChatSessionService.stream_message(session_id, user.id, message.question, history))

@router.put("/{session_id}/title", response_model=ChatSessionResponse)
async def update_session_title(
    session_id: int,
    title_data: ChatSessionTitleUpdate,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    """Update chat session title"""
    try:
        return await ChatSessionService.update_session_title(session_id, user.id, title_data.title.strip(), db)
    except ValueError:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    except Exception:
        raise _server_error("rename the chat")

@router.delete("/{session_id}")
async def delete_chat_session(
    session_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    """Delete a chat session"""
    try:
        success = await ChatSessionService.delete_chat_session(session_id, user.id, db)
    except Exception:
        raise _server_error("delete the chat")
    if not success:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return {"message": "Chat session deleted successfully"}
