from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from ..models.chat import Chat
from ..models.user import User
from ..schemas.chat import ChatResponse
from .rag import rag_service
from typing import List

class ChatService:
    @staticmethod
    async def get_chat_history(user_id: int, db: AsyncSession) -> List[ChatResponse]:
        result = await db.execute(
            select(Chat)
            .filter(Chat.user_id == user_id)
            .order_by(desc(Chat.timestamp))
            .limit(50)
        )
        chats = result.scalars().all()
        return [ChatResponse.from_orm(chat) for chat in reversed(chats)]
    
    @staticmethod
    async def create_chat(user_id: int, question: str, db: AsyncSession) -> ChatResponse:
        # Get AI response
        answer = rag_service.get_response(question, user_id)
        
        # Save to database
        chat = Chat(
            user_id=user_id,
            question=question,
            answer=answer
        )
        
        db.add(chat)
        await db.commit()
        await db.refresh(chat)
        
        return ChatResponse.from_orm(chat)
