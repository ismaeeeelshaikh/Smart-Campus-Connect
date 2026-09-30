from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # Updated relationships
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")  # Keep old model
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")  # New

    # Add inside class User:
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")