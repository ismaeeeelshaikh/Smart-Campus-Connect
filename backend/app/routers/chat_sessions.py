from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..schemas.chat_session import (
    ChatSessionCreate, ChatSessionResponse, ChatSessionDetail, 
    ChatSessionList, ChatMessageCreate, ChatMessageResponse)
from ..services.chat_session import ChatSessionService
from ..services.auth import AuthService
from ..utils.security import verify_token
import logging
import traceback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat-sessions", tags=["chat-sessions"])
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)):
    email = verify_token(credentials.credentials)
    if email is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    return await AuthService.get_user_by_email(email, db)

@router.post("", response_model=ChatSessionResponse)
async def create_chat_session(
    session_data: ChatSessionCreate,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    """Create a new chat session"""
    try:
        logger.info(f"Creating chat session for user {user.id}")
        result = await ChatSessionService.create_chat_session(user.id, session_data.title, db)
        logger.info(f"Chat session created: {result.id}")
        return result
    except Exception as e:
        logger.error(f"Error creating chat session: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to create chat session: {str(e)}")

# NEW ENDPOINT: ChatGPT-like experience - create session with first message
@router.post("/start", response_model=dict)
async def start_chat_session(
    message: ChatMessageCreate,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    """Start a new chat session with first message (ChatGPT-like)"""
    try:
        logger.info(f"Starting new chat session for user {user.id} with message: {message.question[:50]}...")
        
        session_response, message_response = await ChatSessionService.create_session_with_first_message(
            user.id, message.question, db
        )
        
        logger.info(f"Chat session started: {session_response.id} with title: {session_response.title}")
        
        return {
            "session": session_response,
            "message": message_response
        }
    except Exception as e:
        logger.error(f"Error starting chat session: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to start chat session: {str(e)}")

@router.get("", response_model=ChatSessionList)
async def get_chat_sessions(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    """Get all chat sessions for the user"""
    try:
        logger.info(f"Getting chat sessions for user {user.id}")
        sessions = await ChatSessionService.get_user_chat_sessions(user.id, db)
        logger.info(f"Found {len(sessions)} sessions")
        return ChatSessionList(sessions=sessions)
    except Exception as e:
        logger.error(f"Error getting chat sessions: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get chat sessions: {str(e)}")

@router.get("/{session_id}", response_model=ChatSessionDetail)
async def get_chat_session_detail(
    session_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    """Get specific chat session with all messages"""
    try:
        return await ChatSessionService.get_chat_session_detail(session_id, user.id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting chat session detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/messages", response_model=ChatMessageResponse)
async def send_message_to_session(
    session_id: int,
    message: ChatMessageCreate,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    """Send a message to a specific chat session"""
    try:
        return await ChatSessionService.add_message_to_session(session_id, user.id, message.question, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{session_id}/title", response_model=ChatSessionResponse)
async def update_session_title(
    session_id: int,
    title_data: dict,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    """Update chat session title"""
    try:
        return await ChatSessionService.update_session_title(session_id, user.id, title_data["title"], db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{session_id}")
async def delete_chat_session(
    session_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    """Delete a chat session"""
    try:
        success = await ChatSessionService.delete_chat_session(session_id, user.id, db)
        if not success:
            raise HTTPException(status_code=404, detail="Chat session not found")
        return {"message": "Chat session deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))