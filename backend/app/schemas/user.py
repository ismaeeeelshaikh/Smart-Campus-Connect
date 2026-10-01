from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from ..utils.security import check_password_strength, check_username


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def valid_username(cls, v: str) -> str:
        return check_username(v)

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return check_password_strength(v)


class SignupWithOtp(UserCreate):
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class UserLogin(BaseModel):
    email: EmailStr
    # No strength rule here (older accounts may have weaker passwords); the max length stops
    # someone from sending a huge "password" that takes the server a long time to hash.
    password: str = Field(min_length=1, max_length=128)


class EmailSchema(BaseModel):
    email: EmailStr
