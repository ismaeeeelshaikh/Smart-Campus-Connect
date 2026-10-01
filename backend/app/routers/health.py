"""Health check for Docker and uptime monitors: database, knowledge base and LLM server."""
import asyncio
import time
from typing import Optional

import httpx
from fastapi import APIRouter, Response
from sqlalchemy import text

from ..config import settings
from ..database import async_session
from ..services.rag import get_rag_service

router = APIRouter(tags=["health"])

LLM_CHECK_SECONDS = 300  # ask the LLM server at most every 5 minutes, not on every probe
_llm_status: Optional[tuple[float, str]] = None


async def check_llm() -> str:
    """Whether the LLM server lists its models (cheap: uses no tokens)."""
    global _llm_status
    if _llm_status and time.monotonic() - _llm_status[0] < LLM_CHECK_SECONDS:
        return _llm_status[1]
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"} if settings.llm_api_key else {}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{settings.llm_base_url.rstrip('/')}/models", headers=headers)
        status = "ok" if r.is_success else f"error (HTTP {r.status_code})"
    except httpx.HTTPError:
        status = "unreachable"
    _llm_status = (time.monotonic(), status)
    return status


@router.get("/health")
async def health(response: Response):
    """200 when the database and the knowledge base work, 503 otherwise. The LLM is reported but
    doesn't make the backend unhealthy: restarting the backend wouldn't fix a down LLM server."""
    result = {"status": "healthy", "database": "ok", "knowledge_base": "ok", "knowledge_base_chunks": 0}
    try:
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
    except Exception:
        result["database"] = "error"
    try:
        result["knowledge_base_chunks"] = await asyncio.to_thread(get_rag_service().kb.collection.count)
    except Exception:
        result["knowledge_base"] = "error"
    result["llm"] = await check_llm()
    if result["database"] != "ok" or result["knowledge_base"] != "ok":
        result["status"] = "unhealthy"
        response.status_code = 503
    return result
