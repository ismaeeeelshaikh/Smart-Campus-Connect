"""Small in-memory rate limiter for login, OTP and password-reset endpoints.

Chat is intentionally NOT limited (decision 2026-10-01). Limits live in this process's memory,
so they reset on restart and aren't shared between several worker processes (fine for one
backend process; use Redis if you ever run several).
"""
import math
import threading
import time
from collections import deque

from fastapi import HTTPException, Request

from ..config import settings

# action -> (max requests, window in seconds)
LIMITS = {
    "login:ip": (20, 15 * 60),
    "login:email": (10, 15 * 60),
    "signup_otp:ip": (10, 60 * 60),
    "signup_otp:email": (3, 15 * 60),
    "complete_signup:email": (10, 15 * 60),
    "reset_request:ip": (10, 60 * 60),
    "reset_request:email": (3, 15 * 60),
    "reset_password:email": (10, 15 * 60),
}


class RateLimiter:
    def __init__(self):
        self._hits: dict[str, deque] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window: int) -> int:
        """Record one request. Returns 0 if allowed, else seconds until the next one is allowed."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - window:
                hits.popleft()
            if len(hits) >= limit:
                return max(1, math.ceil(hits[0] + window - now))
            hits.append(now)
            if len(self._hits) > 50_000:  # keep memory bounded: drop keys with no recent hits
                for k in [k for k, v in self._hits.items() if not v or v[-1] <= now - 3600]:
                    del self._hits[k]
            return 0

    def reset(self):
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def client_ip(request: Request) -> str:
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce(action: str, key: str):
    """Raise 429 if `key` (an IP or email) made too many `action` requests recently."""
    limit, window = LIMITS[action]
    retry_after = limiter.hit(f"{action}:{key.lower()}", limit, window)
    if retry_after:
        minutes = math.ceil(retry_after / 60)
        raise HTTPException(
            status_code=429,
            detail=f"Too many attempts. Please try again in {minutes} minute{'s' if minutes != 1 else ''}.",
            headers={"Retry-After": str(retry_after)},
        )
