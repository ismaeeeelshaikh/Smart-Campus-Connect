"""Public chat for people without an APSIT account (future students, parents). Nothing is saved."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..schemas.chat_session import SourceLink
from ..services.rag import Answer, AssistantBusy, get_rag_service, MAX_HISTORY_TURNS
from ..utils.sse import sse, sse_response
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/guest", tags=["guest"])


class GuestTurn(BaseModel):
    question: str = Field(max_length=4000)
    answer: str = Field(max_length=20000)


class GuestChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    # Earlier turns of this conversation, kept by the browser (only the last few are used)
    history: list[GuestTurn] = Field(default=[], max_length=50)

    def history_pairs(self):
        return [(t.question, t.answer) for t in self.history[-MAX_HISTORY_TURNS:]]


class GuestChatResponse(BaseModel):
    answer: str
    sources: list[SourceLink] = []


@router.post("/chat", response_model=GuestChatResponse)
async def guest_chat(payload: GuestChatRequest):
    try:
        answer = await get_rag_service().answer(payload.question.strip(), payload.history_pairs())
    except AssistantBusy:
        raise HTTPException(status_code=503, detail=AssistantBusy.USER_MESSAGE)
    except Exception:
        logger.exception("Guest chat failed")
        raise HTTPException(status_code=500, detail="Could not answer right now. Please try again.")
    return GuestChatResponse(answer=answer.text, sources=answer.sources)


@router.post("/chat/stream")
async def guest_chat_stream(payload: GuestChatRequest):
    """Streamed version: "token" events, then "done" with {answer, sources}."""
    async def events():
        try:
            async for piece in get_rag_service().stream(payload.question.strip(), payload.history_pairs()):
                if isinstance(piece, Answer):
                    yield sse("done", {"answer": piece.text, "sources": piece.sources})
                else:
                    yield sse("token", {"text": piece})
        except AssistantBusy:
            yield sse("error", {"detail": AssistantBusy.USER_MESSAGE})
        except Exception:
            logger.exception("Guest chat stream failed")
            yield sse("error", {"detail": "Could not answer right now. Please try again."})
    return sse_response(events())
