from pydantic import BaseModel
from datetime import datetime
from typing import List

class ChatMessage(BaseModel):
    question: str

class ChatResponse(BaseModel):
    id: int
    question: str
    answer: str
    timestamp: datetime
    
    class Config:
        from_attributes = True

class ChatHistory(BaseModel):
    chats: List[ChatResponse]
