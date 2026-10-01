"""Saved chats: create, follow up (history from the DB), rename, delete, streaming, sources, privacy."""
from helpers import STUB_SOURCES, parse_sse


async def start_chat(client, headers, question="Who is the HOD of IT?"):
    r = await client.post("/chat-sessions/start", json={"question": question}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


async def test_chat_lifecycle(client, auth_headers, fake_rag):
    data = await start_chat(client, auth_headers)
    sid = data["session"]["id"]
    assert data["message"]["answer"].startswith("stub answer")
    assert data["message"]["sources"] == STUB_SOURCES
    assert fake_rag.last_history == []

    r = await client.post(f"/chat-sessions/{sid}/messages", json={"question": "and Civil?"}, headers=auth_headers)
    assert r.status_code == 200
    # the follow-up got the first exchange as history, loaded from the database
    assert fake_rag.last_history == [("Who is the HOD of IT?", data["message"]["answer"])]

    r = await client.put(f"/chat-sessions/{sid}/title", json={"title": "  HOD questions  "}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["title"] == "HOD questions"

    r = await client.get(f"/chat-sessions/{sid}", headers=auth_headers)
    detail = r.json()
    assert len(detail["messages"]) == 2 and detail["messages"][0]["sources"] == STUB_SOURCES

    r = await client.get("/chat-sessions", headers=auth_headers)
    assert [s["id"] for s in r.json()["sessions"]] == [sid]

    assert (await client.delete(f"/chat-sessions/{sid}", headers=auth_headers)).status_code == 200
    assert (await client.delete(f"/chat-sessions/{sid}", headers=auth_headers)).status_code == 404


async def test_validation_and_not_found(client, auth_headers):
    sid = (await start_chat(client, auth_headers))["session"]["id"]
    assert (await client.put(f"/chat-sessions/{sid}/title", json={"title": ""}, headers=auth_headers)).status_code == 422
    assert (await client.put(f"/chat-sessions/{sid}/title", json={"wrong": "x"}, headers=auth_headers)).status_code == 422
    assert (await client.post(f"/chat-sessions/{sid}/messages", json={"question": ""}, headers=auth_headers)).status_code == 422
    r = await client.get("/chat-sessions/999999", headers=auth_headers)
    assert r.status_code == 404 and r.json()["detail"] == "Chat session not found"


async def test_needs_login(client):
    assert (await client.get("/chat-sessions")).status_code in (401, 403)
    assert (await client.get("/chat-sessions", headers={"Authorization": "Bearer nope"})).status_code == 401


async def test_users_cannot_see_each_others_chats(client, auth_headers, create_user, login):
    sid = (await start_chat(client, auth_headers))["session"]["id"]
    await create_user(email="other@apsit.edu.in", full_name="Other Student")
    other = await login("other@apsit.edu.in")
    assert (await client.get(f"/chat-sessions/{sid}", headers=other)).status_code == 404
    assert (await client.post(f"/chat-sessions/{sid}/messages", json={"question": "hi"}, headers=other)).status_code == 404
    assert (await client.put(f"/chat-sessions/{sid}/title", json={"title": "mine"}, headers=other)).status_code == 404
    assert (await client.delete(f"/chat-sessions/{sid}", headers=other)).status_code == 404
    assert (await client.get("/chat-sessions", headers=other)).json()["sessions"] == []


async def test_streamed_new_chat_and_follow_up(client, auth_headers, fake_rag):
    r = await client.post("/chat-sessions/start/stream", json={"question": "Stream me"}, headers=auth_headers)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(r.text)
    tokens = "".join(d["text"] for e, d in events if e == "token")
    done = [d for e, d in events if e == "done"]
    assert sum(e == "token" for e, _ in events) > 3 and len(done) == 1
    assert done[0]["message"]["answer"] == tokens and done[0]["message"]["sources"] == STUB_SOURCES
    sid = done[0]["session"]["id"]

    r = await client.post(f"/chat-sessions/{sid}/messages/stream", json={"question": "and more?"}, headers=auth_headers)
    assert [e for e, _ in parse_sse(r.text)][-1] == "done"
    assert fake_rag.last_history == [("Stream me", tokens)]
    assert len((await client.get(f"/chat-sessions/{sid}", headers=auth_headers)).json()["messages"]) == 2


async def test_stream_errors(client, auth_headers):
    assert (await client.post("/chat-sessions/999999/messages/stream", json={"question": "x"}, headers=auth_headers)).status_code == 404
    assert (await client.post("/chat-sessions/start/stream", json={"question": "x"})).status_code in (401, 403)


async def test_ai_failures_give_friendly_messages(client, auth_headers):
    from app.services.rag import AssistantBusy, set_rag_service

    class Broken:
        async def answer(self, question, history=None):
            raise RuntimeError("LLM exploded")

        async def stream(self, question, history=None):
            raise RuntimeError("LLM exploded")
            yield  # makes this an async generator

    class Busy:
        async def answer(self, question, history=None):
            raise AssistantBusy()

        async def stream(self, question, history=None):
            raise AssistantBusy()
            yield

    set_rag_service(Broken())
    r = await client.post("/chat-sessions/start/stream", json={"question": "x"}, headers=auth_headers)
    last = parse_sse(r.text)[-1]
    assert last[0] == "error" and "exploded" not in r.text
    r = await client.post("/chat-sessions/start", json={"question": "x"}, headers=auth_headers)
    assert r.status_code == 500 and "exploded" not in r.text

    set_rag_service(Busy())
    r = await client.post("/chat-sessions/start", json={"question": "x"}, headers=auth_headers)
    assert r.status_code == 503 and "try again in a minute" in r.json()["detail"]
    r = await client.post("/chat-sessions/start/stream", json={"question": "x"}, headers=auth_headers)
    assert "try again in a minute" in parse_sse(r.text)[-1][1]["detail"]
