from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from datetime import datetime
from ..utils.security import check_full_name, check_password_strength


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str

    @field_validator("full_name")
    @classmethod
    def valid_full_name(cls, v: str) -> str:
        return check_full_name(v)

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return check_password_strength(v)


class SignupWithOtp(UserCreate):
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class ProfileUpdate(BaseModel):
    full_name: str

    @field_validator("full_name")
    @classmethod
    def valid_full_name(cls, v: str) -> str:
        return check_full_name(v)


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
