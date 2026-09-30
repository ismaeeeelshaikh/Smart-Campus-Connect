from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from ..database import get_db
from ..schemas.user import UserCreate, UserResponse, Token, UserLogin
from ..services.auth import AuthService
from ..utils.security import create_access_token
from ..config import settings
from ..services.signup_otp import generate_and_store_otp, verify_otp   # << Added
from ..services.email import send_otp_email  # << Added
import logging
from app.schemas.user import EmailSchema

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        logger.info(f"Registration attempt for email: {user_data.email}")
        user = await AuthService.create_user(user_data, db)
        logger.info(f"User created successfully: {user.id}")
        return UserResponse.from_orm(user)
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login")
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    try:
        logger.info(f"Login attempt for email: {user_data.email}")
        user = await AuthService.authenticate_user(user_data.email, user_data.password, db)
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        logger.info(f"Login successful for user: {user.email}")
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        }
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {str(e)}"
        )

# ---- Signup OTP related additions ----
class SignupWithOtp(BaseModel):
    username: str
    email: str
    password: str
    otp: str

@router.post("/request-signup-otp")
async def request_signup_otp(payload: EmailSchema, db: AsyncSession = Depends(get_db)):
    otp = await generate_and_store_otp(payload.email, db)
    await send_otp_email(payload.email, otp)
    return {"message": "OTP sent to email if it exists."}

@router.post("/complete-signup")
async def complete_signup(data: SignupWithOtp, db: AsyncSession = Depends(get_db)):
    is_valid = await verify_otp(data.email, data.otp, db)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP")

    user = await AuthService.create_user(UserCreate(
        username=data.username,
        email=data.email,
        password=data.password
    ), db)

    return {"message": "User created successfully", "user_id": user.id}
