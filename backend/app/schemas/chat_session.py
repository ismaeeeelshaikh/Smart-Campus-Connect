from pydantic import BaseModel, ConfigDict, Field
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

    model_config = ConfigDict(from_attributes=True)

class DocumentInfo(BaseModel):
    """A PDF uploaded to a chat."""
    filename: str
    pages: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New Chat"

class ChatSessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0
    has_document: bool = False

    model_config = ConfigDict(from_attributes=True)

class ChatSessionDetail(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageResponse]
    document: Optional[DocumentInfo] = None

    model_config = ConfigDict(from_attributes=True)

class DocumentUploadResponse(BaseModel):
    session: ChatSessionResponse
    document: DocumentInfo

class ChatSessionList(BaseModel):
    sessions: List[ChatSessionResponse]
