"""Guest chat: no login, nothing saved."""
from sqlalchemy import func, select

from app.database import async_session
from app.models import ChatMessage, ChatSession
from helpers import STUB_SOURCES, parse_sse


async def count_saved():
    async with async_session() as db:
        sessions = (await db.execute(select(func.count()).select_from(ChatSession))).scalar_one()
        messages = (await db.execute(select(func.count()).select_from(ChatMessage))).scalar_one()
    return sessions, messages


async def test_guest_chat(client):
    r = await client.post("/guest/chat", json={"question": "What are the fees?"})
    assert r.status_code == 200
    assert r.json()["answer"].startswith("stub answer") and r.json()["sources"] == STUB_SOURCES


async def test_guest_history_is_capped_at_four_turns(client, fake_rag):
    turns = [{"question": f"q{i}", "answer": f"a{i}"} for i in range(6)]
    await client.post("/guest/chat", json={"question": "and hostel?", "history": turns})
    assert fake_rag.last_history == [(f"q{i}", f"a{i}") for i in range(2, 6)]


async def test_guest_input_limits(client):
    assert (await client.post("/guest/chat", json={"question": ""})).status_code == 422
    assert (await client.post("/guest/chat", json={"question": "x" * 5000})).status_code == 422
    big_history = [{"question": "q", "answer": "a"}] * 60
    assert (await client.post("/guest/chat", json={"question": "hi", "history": big_history})).status_code == 422


async def test_guest_chat_saves_nothing(client):
    before = await count_saved()
    await client.post("/guest/chat", json={"question": "hi"})
    await client.post("/guest/chat/stream", json={"question": "hi"})
    assert await count_saved() == before


async def test_guest_stream(client):
    r = await client.post("/guest/chat/stream", json={"question": "fees?", "history": [{"question": "q", "answer": "a"}]})
    done = [d for e, d in parse_sse(r.text) if e == "done"]
    assert len(done) == 1 and done[0]["sources"] == STUB_SOURCES and done[0]["answer"].startswith("stub answer")
