from pydantic import BaseModel, EmailStr, Field
from typing import Annotated

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetVerify(BaseModel):
    email: EmailStr
    # Use Annotated and Field for constraints
    otp: Annotated[str, Field(min_length=6, max_length=6)]
    new_password: Annotated[str, Field(min_length=8)]

class PasswordResetResponse(BaseModel):
    message: str