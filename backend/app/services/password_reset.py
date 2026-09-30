import random
from datetime import datetime, timedelta
from fastapi import HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.user import User
from ..models.password_reset_token import PasswordResetToken
from ..utils.security import get_password_hash
from .email import send_reset_email  # re-exported for routers/password_reset.py

INVALID_OTP = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP")

def generate_otp() -> str:
    return f"{random.randint(100000, 999999)}"

async def create_password_reset_token(db: AsyncSession, user: User, otp: str):
    expiry = datetime.utcnow() + timedelta(minutes=15)
    token = PasswordResetToken(user_id=user.id, otp=otp, expires_at=expiry)
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token

async def verify_password_reset_token(db: AsyncSession, email: str, otp: str):
    result = await db.execute(select(User).filter(User.email == email))
    user = result.scalars().first()
    if not user:
        # Same error as a wrong OTP, so this endpoint can't be used to find out which emails are registered
        raise INVALID_OTP

    result_token = await db.execute(
        select(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.otp == otp,
            PasswordResetToken.used == 0,
            PasswordResetToken.expires_at > datetime.utcnow(),
        )
    )
    token = result_token.scalars().first()
    if not token:
        raise INVALID_OTP

    return user, token

async def mark_token_used(db: AsyncSession, token: PasswordResetToken):
    token.used = 1
    db.add(token)
    await db.commit()

async def update_user_password(db: AsyncSession, user: User, new_password: str):
    # Same hasher (argon2) as signup, from utils/security.py
    user.hashed_password = get_password_hash(new_password)
    db.add(user)
    await db.commit()
