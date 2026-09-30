import random
from datetime import datetime, timedelta
from sqlalchemy.future import select
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.signup_otp_token import SignupOtpToken

def generate_random_otp(length=6):
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])

async def generate_and_store_otp(email: str, db: AsyncSession) -> str:
    otp = generate_random_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    # Remove existing OTPs for the email to avoid multiple valid ones
    await db.execute(delete(SignupOtpToken).where(SignupOtpToken.email == email))

    token = SignupOtpToken(email=email, otp=otp, expires_at=expires_at)
    db.add(token)
    await db.commit()
    await db.refresh(token)

    return otp

async def verify_otp(email: str, otp: str, db: AsyncSession) -> bool:
    result = await db.execute(
        select(SignupOtpToken).where(
            SignupOtpToken.email == email,
            SignupOtpToken.otp == otp,
            SignupOtpToken.expires_at > datetime.utcnow()
        )
    )
    token = result.scalar_one_or_none()
    return token is not None
