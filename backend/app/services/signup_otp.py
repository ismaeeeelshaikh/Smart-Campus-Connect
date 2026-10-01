from datetime import datetime, timedelta
from sqlalchemy.future import select
from sqlalchemy import delete, desc
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.signup_otp_token import SignupOtpToken
from ..utils.security import generate_otp, hash_otp, otp_matches

OTP_VALID_MINUTES = 10
MAX_OTP_ATTEMPTS = 5  # after this many wrong guesses the code stops working


async def generate_and_store_otp(email: str, db: AsyncSession) -> str:
    """Create a new code for `email` (replacing any older one) and return it, to be emailed."""
    otp = generate_otp()
    await db.execute(delete(SignupOtpToken).where(SignupOtpToken.email == email))
    db.add(SignupOtpToken(
        email=email,
        otp_hash=hash_otp(email, otp),
        expires_at=datetime.utcnow() + timedelta(minutes=OTP_VALID_MINUTES),
    ))
    await db.commit()
    return otp


async def delete_otps(email: str, db: AsyncSession):
    await db.execute(delete(SignupOtpToken).where(SignupOtpToken.email == email))
    await db.commit()


async def verify_otp(email: str, otp: str, db: AsyncSession) -> bool:
    token = (await db.execute(
        select(SignupOtpToken)
        .where(SignupOtpToken.email == email, SignupOtpToken.expires_at > datetime.utcnow())
        .order_by(desc(SignupOtpToken.id)).limit(1)
    )).scalar_one_or_none()
    if token is None or token.attempts >= MAX_OTP_ATTEMPTS:
        return False
    if otp_matches(email, otp, token.otp_hash):
        return True
    token.attempts += 1  # a wrong guess uses up one of the 5 attempts
    await db.commit()
    return False
