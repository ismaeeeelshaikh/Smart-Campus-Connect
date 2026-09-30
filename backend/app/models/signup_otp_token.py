from sqlalchemy import Column, Integer, String, DateTime, func
from datetime import datetime, timedelta
from ..database import Base

class SignupOtpToken(Base):
    __tablename__ = "signup_otp_tokens"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    otp = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow() + timedelta(minutes=10))
    created_at = Column(DateTime, nullable=False, default=func.now())
