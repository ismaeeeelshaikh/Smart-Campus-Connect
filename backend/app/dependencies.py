from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from .config import settings
from .database import get_db
from .models.user import User
from .services.auth import AuthService
from .utils.security import decode_token

security = HTTPBearer()
INVALID_CREDENTIALS = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise INVALID_CREDENTIALS
    try:
        user = await AuthService.get_user_by_email(payload["sub"], db)
    except HTTPException:
        raise INVALID_CREDENTIALS  # token is valid but the account no longer exists
    # Tokens issued before the last password change are revoked (e.g. after "forgot password")
    if user.password_changed_at is not None:
        issued_at = payload.get("iat", 0)
        if issued_at < int(user.password_changed_at.timestamp()):
            raise INVALID_CREDENTIALS
    return user


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not settings.is_admin(user.email):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins only")
    return user
