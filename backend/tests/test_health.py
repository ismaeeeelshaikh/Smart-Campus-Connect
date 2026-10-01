"""/health: database and knowledge base decide the status; the LLM is only reported."""
from types import SimpleNamespace

import pytest

from app.routers import health
from app.services.rag import set_rag_service


@pytest.fixture
def llm_status(monkeypatch):
    status = {"value": "ok"}

    async def check_llm():
        return status["value"]

    monkeypatch.setattr(health, "check_llm", check_llm)
    return status


def with_chunks(n):
    set_rag_service(SimpleNamespace(kb=SimpleNamespace(collection=SimpleNamespace(count=lambda: n))))


async def test_healthy(client, llm_status):
    with_chunks(2591)
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy", "database": "ok", "knowledge_base": "ok",
                        "knowledge_base_chunks": 2591, "llm": "ok"}


async def test_llm_down_is_reported_but_backend_stays_healthy(client, llm_status):
    with_chunks(10)
    llm_status["value"] = "unreachable"
    r = await client.get("/health")
    assert r.status_code == 200 and r.json()["llm"] == "unreachable"


async def test_knowledge_base_not_loaded_is_unhealthy(client, llm_status):
    set_rag_service(None)
    r = await client.get("/health")
    assert r.status_code == 503
    assert r.json()["status"] == "unhealthy" and r.json()["knowledge_base"] == "error"


async def test_check_llm_asks_the_model_list_and_caches(monkeypatch):
    import httpx

    calls = []
    replies = iter([httpx.Response(200, json={"data": []}), httpx.Response(401)])

    def handler(request):
        calls.append(request)
        return next(replies)

    real_client = httpx.AsyncClient
    monkeypatch.setattr(health.httpx, "AsyncClient",
                        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
    monkeypatch.setattr(health.settings, "llm_base_url", "http://dgx.local:8000/v1/")
    monkeypatch.setattr(health.settings, "llm_api_key", "secret")
    monkeypatch.setattr(health, "_llm_status", None)

    assert await health.check_llm() == "ok"
    assert str(calls[0].url) == "http://dgx.local:8000/v1/models"
    assert calls[0].headers["authorization"] == "Bearer secret"
    assert await health.check_llm() == "ok" and len(calls) == 1  # cached

    monkeypatch.setattr(health, "_llm_status", None)
    assert await health.check_llm() == "error (HTTP 401)"

    def down(request):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(health.httpx, "AsyncClient",
                        lambda **kw: real_client(transport=httpx.MockTransport(down), **kw))
    monkeypatch.setattr(health, "_llm_status", None)
    assert await health.check_llm() == "unreachable"
