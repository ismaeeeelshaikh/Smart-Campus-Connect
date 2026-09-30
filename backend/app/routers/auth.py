from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from ..database import get_db
from ..models.user import User
from ..schemas.user import UserCreate, UserLogin, EmailSchema
from ..services.auth import AuthService
from ..utils.security import create_access_token
from ..config import settings
from ..services.signup_otp import generate_and_store_otp, verify_otp, delete_otps
from ..services.email import send_otp_email
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


def _check_signup_domain(email: str):
    if not settings.email_can_sign_up(email):
        domains = ", ".join("@" + d.strip().lstrip("@") for d in settings.allowed_signup_domains.split(",") if d.strip())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Please sign up with your college email ({domains}).",
        )


@router.post("/login")
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    email = user_data.email.lower()
    logger.info(f"Login attempt for email: {email}")
    user = await AuthService.authenticate_user(email, user_data.password, db)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {"id": user.id, "username": user.username, "email": user.email},
    }


# ---- Signup with email OTP ----
class SignupWithOtp(BaseModel):
    username: str
    email: EmailStr
    password: str
    otp: str


@router.post("/request-signup-otp")
async def request_signup_otp(payload: EmailSchema, db: AsyncSession = Depends(get_db)):
    email = payload.email.lower()
    _check_signup_domain(email)

    existing = await db.execute(select(User).filter(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists. Please log in.",
        )

    otp = await generate_and_store_otp(email, db)
    try:
        await send_otp_email(email, otp)
    except Exception:
        logger.exception(f"Failed to send signup OTP to {email}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not send the OTP email right now. Please try again later.",
        )
    return {"message": "OTP sent to your email."}


@router.post("/complete-signup")
async def complete_signup(data: SignupWithOtp, db: AsyncSession = Depends(get_db)):
    email = data.email.lower()
    _check_signup_domain(email)

    if not await verify_otp(email, data.otp.strip(), db):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP")

    user = await AuthService.create_user(
        UserCreate(username=data.username.strip(), email=email, password=data.password), db
    )
    await delete_otps(email, db)  # an OTP must not be reusable
    logger.info(f"User created via OTP signup: {user.id}")
    return {"message": "User created successfully", "user_id": user.id}
