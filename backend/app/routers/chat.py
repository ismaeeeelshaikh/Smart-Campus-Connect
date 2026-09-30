from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..schemas.chat import ChatMessage, ChatResponse, ChatHistory
from ..services.chat import ChatService
from ..services.auth import AuthService
from ..utils.security import verify_token
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    email = verify_token(credentials.credentials)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    user = await AuthService.get_user_by_email(email, db)
    return user

@router.post("", response_model=ChatResponse)
async def chat(
    message: ChatMessage,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"Chat request from user {user.id}: {message.question}")
    try:
        response = await ChatService.create_chat(user.id, message.question, db)
        logger.info(f"✅ Chat response generated for user {user.id}")
        return response
    except Exception as e:
        logger.error(f"❌ Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=ChatHistory)
async def get_history(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        chats = await ChatService.get_chat_history(user.id, db)
        return ChatHistory(chats=chats)
    except Exception as e:
        logger.error(f"❌ History error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
