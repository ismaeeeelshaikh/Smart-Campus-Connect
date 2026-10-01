from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class ChatMessageCreate(BaseModel):
    question: str = Field(min_length=1, max_length=4000)

class ChatSessionTitleUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=100)

class SourceLink(BaseModel):
    title: str
    url: str

class ChatMessageResponse(BaseModel):
    id: int
    question: str
    answer: str
    sources: List[SourceLink] = []
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
