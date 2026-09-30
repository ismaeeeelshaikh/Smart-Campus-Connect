from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class ChatMessageCreate(BaseModel):
    question: str

class ChatMessageResponse(BaseModel):
    id: int
    question: str
    answer: str
    timestamp: datetime
    
    class Config:
        from_attributes = True

class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New Chat"

class ChatSessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

class ChatSessionDetail(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageResponse]
    
    class Config:
        from_attributes = True

class ChatSessionList(BaseModel):
    sessions: List[ChatSessionResponse]
