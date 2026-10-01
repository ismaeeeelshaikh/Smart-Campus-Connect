"""Server-sent events: how streamed answers are sent to the browser.

Each event looks like:
    event: token
    data: {"text": "Hel"}

Events used: "token" (a piece of the answer), "done" (final answer, sources, saved ids),
"error" (something went wrong; {"detail": "..."}).
"""
import json

from fastapi.responses import StreamingResponse

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",  # tell nginx (production) not to buffer the stream
}


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def sse_response(generator) -> StreamingResponse:
    return StreamingResponse(generator, media_type="text/event-stream", headers=SSE_HEADERS)
