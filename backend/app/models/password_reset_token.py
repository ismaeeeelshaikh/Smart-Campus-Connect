from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    otp_hash = Column(String, nullable=False)  # never the plain code (see utils/security.hash_otp)
    expires_at = Column(DateTime, nullable=False)  # UTC
    created_at = Column(DateTime, server_default=func.now())
    used = Column(Integer, default=0)  # 0 = not used, 1 = used (or replaced / too many attempts)
    attempts = Column(Integer, nullable=False, default=0, server_default="0")  # wrong guesses so far

    user = relationship("User", back_populates="password_reset_tokens")
