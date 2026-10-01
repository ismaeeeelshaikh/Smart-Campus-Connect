from sqlalchemy import Column, Integer, String, DateTime, func
from datetime import datetime, timedelta
from ..database import Base

class SignupOtpToken(Base):
    __tablename__ = "signup_otp_tokens"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    otp_hash = Column(String, nullable=False)  # never the plain code (see utils/security.hash_otp)
    expires_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow() + timedelta(minutes=10))  # UTC
    created_at = Column(DateTime, nullable=False, default=func.now())
    attempts = Column(Integer, nullable=False, default=0, server_default="0")  # wrong guesses so far
