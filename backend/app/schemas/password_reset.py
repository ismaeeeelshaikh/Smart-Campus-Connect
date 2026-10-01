from pydantic import BaseModel, EmailStr, Field, field_validator
from ..utils.security import check_password_strength


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetVerify(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    new_password: str

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return check_password_strength(v)


class PasswordResetResponse(BaseModel):
    message: str
