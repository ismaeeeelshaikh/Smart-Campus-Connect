from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import status
from ..schemas.password_reset import PasswordResetRequest, PasswordResetVerify, PasswordResetResponse
from ..services.password_reset import (
    generate_otp,
    send_reset_email,
    create_password_reset_token,
    verify_password_reset_token,
    mark_token_used,
    update_user_password,
)
from ..database import get_db
from ..models.user import User

router = APIRouter(prefix="/password-reset", tags=["Password Reset"])

@router.post("/request-reset", response_model=PasswordResetResponse)
async def request_password_reset(payload: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.email == payload.email))
    user = result.scalars().first()
    if not user:
        # Do not reveal if email exists for security reasons
        return PasswordResetResponse(message="If your email exists, you will receive an OTP.")
    
    otp = generate_otp()
    await create_password_reset_token(db, user, otp)
    await send_reset_email(payload.email, otp)

    return PasswordResetResponse(message="If your email exists, you will receive an OTP.")

@router.post("/reset-password", response_model=PasswordResetResponse)
async def reset_password(payload: PasswordResetVerify, db: AsyncSession = Depends(get_db)):
    user, token = await verify_password_reset_token(db, payload.email, payload.otp)
    await update_user_password(db, user, payload.new_password)
    await mark_token_used(db, token)

    return PasswordResetResponse(message="Password updated successfully.")
