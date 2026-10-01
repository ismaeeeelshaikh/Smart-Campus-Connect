"""Public chat for people without an APSIT account (future students, parents). Nothing is saved."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..services.rag import get_rag_service, MAX_HISTORY_TURNS
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/guest", tags=["guest"])


class GuestTurn(BaseModel):
    question: str
    answer: str


class GuestChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    # Earlier turns of this conversation, kept by the browser (only the last few are used)
    history: list[GuestTurn] = []


class GuestChatResponse(BaseModel):
    answer: str


@router.post("/chat", response_model=GuestChatResponse)
async def guest_chat(payload: GuestChatRequest):
    history = [(t.question, t.answer) for t in payload.history[-MAX_HISTORY_TURNS:]]
    try:
        answer = await get_rag_service().answer(payload.question.strip(), history)
    except Exception:
        logger.exception("Guest chat failed")
        raise HTTPException(status_code=500, detail="Could not answer right now. Please try again.")
    return GuestChatResponse(answer=answer)
