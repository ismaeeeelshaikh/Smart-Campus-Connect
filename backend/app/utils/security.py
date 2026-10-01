import hashlib
import hmac
import re
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from ..config import settings

# Use argon2 instead of bcrypt (more secure and no compatibility issues)
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# ---- Password and name rules (used by the signup, profile and reset schemas) ----
PASSWORD_RULE = "Password must be 8-128 characters and include an uppercase letter, a lowercase letter and a number."
FULL_NAME_RULE = "Please enter your full name (2-60 characters: letters, spaces, . ' -)."

def check_password_strength(password: str) -> str:
    if not (8 <= len(password) <= 128 and re.search(r"[a-z]", password)
            and re.search(r"[A-Z]", password) and re.search(r"\d", password)):
        raise ValueError(PASSWORD_RULE)
    return password

def check_full_name(name: str) -> str:
    """Display name, e.g. "Rohan Sawant" or "Dr. A. D'Souza". Any script is allowed (Devanagari vowel
    signs count as letters). Names don't have to be unique: people log in with their email."""
    name = " ".join(name.split())  # trim and collapse spaces
    letters = sum(1 for ch in name if unicodedata.category(ch)[0] in "LM")
    allowed = all(unicodedata.category(ch)[0] in "LM" or ch in " .'-" for ch in name)
    if not (2 <= len(name) <= 60 and letters >= 2 and allowed):
        raise ValueError(FULL_NAME_RULE)
    return name


def utc_now_naive() -> datetime:
    """Current UTC time without tzinfo, for the OTP tables' plain (UTC) DateTime columns.
    (Replaces the deprecated datetime.utcnow().)"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---- One-time passwords ----
def generate_otp() -> str:
    """6-digit code from a cryptographically secure source (not `random`)."""
    return f"{secrets.randbelow(1_000_000):06d}"

def hash_otp(email: str, otp: str) -> str:
    """OTPs are stored hashed. HMAC with the server secret, so a leaked database
    can't be brute-forced offline (there are only a million 6-digit codes)."""
    return hmac.new(settings.jwt_secret.encode(), f"{email.lower()}:{otp}".encode(), hashlib.sha256).hexdigest()

def otp_matches(email: str, otp: str, otp_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(email, otp), otp_hash)


# ---- Access tokens ----
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    # "iat" (issued at) lets us reject tokens created before the user's last password change
    to_encode = {**data, "exp": expire, "iat": now}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def decode_token(token: str) -> Optional[dict]:
    """The token's claims if it is valid and not expired, else None."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    return payload if payload.get("sub") else None
