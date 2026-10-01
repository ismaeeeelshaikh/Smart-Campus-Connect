from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status

from sqlalchemy import desc, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.user import User
from ..models.password_reset_token import PasswordResetToken
from ..utils.security import generate_otp, get_password_hash, hash_otp, otp_matches  # noqa: F401 (generate_otp re-exported)
from .email import send_reset_email  # noqa: F401 (re-exported for routers/password_reset.py)

INVALID_OTP = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP")
OTP_VALID_MINUTES = 15
MAX_OTP_ATTEMPTS = 5  # after this many wrong guesses the code stops working


async def create_password_reset_token(db: AsyncSession, user: User, otp: str):
    # Only one active code per user: requesting a new one cancels the old ones
    await db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used == 0)
        .values(used=1)
    )
    token = PasswordResetToken(
        user_id=user.id,
        otp_hash=hash_otp(user.email, otp),
        expires_at=datetime.utcnow() + timedelta(minutes=OTP_VALID_MINUTES),
    )
    db.add(token)
    await db.commit()
    return token


async def verify_password_reset_token(db: AsyncSession, email: str, otp: str):
    user = (await db.execute(select(User).filter(User.email == email))).scalars().first()
    if not user:
        # Same error as a wrong OTP, so this endpoint can't be used to find out which emails are registered
        raise INVALID_OTP

    token = (await db.execute(
        select(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used == 0,
            PasswordResetToken.expires_at > datetime.utcnow(),
        )
        .order_by(desc(PasswordResetToken.id)).limit(1)
    )).scalars().first()
    if not token:
        raise INVALID_OTP
    if not otp_matches(email, otp, token.otp_hash):
        token.attempts += 1
        if token.attempts >= MAX_OTP_ATTEMPTS:
            token.used = 1  # too many wrong guesses: this code is dead, request a new one
        await db.commit()
        raise INVALID_OTP

    return user, token


async def mark_token_used(db: AsyncSession, token: PasswordResetToken):
    token.used = 1
    db.add(token)
    await db.commit()


async def update_user_password(db: AsyncSession, user: User, new_password: str):
    # Same hasher (argon2) as signup, from utils/security.py
    user.hashed_password = get_password_hash(new_password)
    # Login tokens issued before now stop working (see dependencies.get_current_user)
    user.password_changed_at = datetime.now(timezone.utc)
    db.add(user)
    await db.commit()
