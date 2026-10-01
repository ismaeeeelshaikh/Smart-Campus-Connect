from sqlalchemy import Column, DateTime, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class ChatDocument(Base):
    """A PDF a student uploaded to one chat (one per chat). Only its text is kept, not the file."""
    __tablename__ = "chat_documents"

    id = Column(Integer, primary_key=True)
    chat_session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, unique=True)
    filename = Column(String(255), nullable=False)
    pages = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chat_session = relationship("ChatSession", back_populates="document")
    chunks = relationship("ChatDocumentChunk", back_populates="document", cascade="all, delete-orphan",
                          passive_deletes=True, order_by="ChatDocumentChunk.position")


class ChatDocumentChunk(Base):
    __tablename__ = "chat_document_chunks"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("chat_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    position = Column(Integer, nullable=False)
    page = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    # float32 vector from the knowledge base's embedding model; empty until the background indexing reaches it
    embedding = Column(LargeBinary, nullable=True)

    document = relationship("ChatDocument", back_populates="chunks")
