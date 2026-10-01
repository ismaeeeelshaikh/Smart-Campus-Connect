"""Test setup.

- Tests use their own database: TEST_DATABASE_URL, or the DATABASE_URL from backend/.env with
  "_test" added to the database name. They refuse to run on a database whose name doesn't end in
  "_test", so your real data is never touched. The database is created and migrated automatically.
- Email sending and the AI (RAG/LLM) are always stubbed: no real emails, no LLM calls.
- Every test starts with empty tables and fresh rate limits.
"""
import asyncio
import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))  # for `helpers`


def _test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        from dotenv import dotenv_values
        base = os.environ.get("DATABASE_URL") or dotenv_values(BACKEND_DIR / ".env").get("DATABASE_URL")
        if not base:
            raise RuntimeError("Set TEST_DATABASE_URL, or DATABASE_URL in backend/.env")
        head, _, name = base.rpartition("/")
        url = f"{head}/{name.split('?')[0]}_test"
    if not url.rsplit("/", 1)[-1].endswith("_test"):
        raise RuntimeError(f"Refusing to run tests on {url!r}: the database name must end in '_test'")
    return url


TEST_DATABASE_URL = _test_database_url()

# Must happen before anything imports app.config. Environment variables win over backend/.env,
# so the tests never use the real mail account or API key.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.update({
    "LLM_API_KEY": "test-key",
    "JWT_SECRET": "test-secret-" + "x" * 48,
    "MAIL_USERNAME": "noreply@example.com",
    "MAIL_PASSWORD": "test",
    "MAIL_FROM": "noreply@example.com",
    "ADMIN_EMAIL": "admin@apsit.edu.in",
    "ALLOWED_SIGNUP_DOMAINS": "apsit.edu.in",
    "CRAWL_INTERVAL_HOURS": "0",
})


def _create_database_if_missing():
    import asyncpg

    async def create():
        dsn = TEST_DATABASE_URL.replace("+asyncpg", "")
        head, _, name = dsn.rpartition("/")
        conn = await asyncpg.connect(f"{head}/postgres")
        try:
            if not await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", name):
                await conn.execute(f'CREATE DATABASE "{name}"')
        finally:
            await conn.close()

    asyncio.run(create())


def _migrate():
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(cfg, "head")  # also checks that the migrations work on an empty database


_create_database_if_missing()
_migrate()

from helpers import FakeRag  # noqa: E402

TABLES = "users, chat_sessions, chat_messages, signup_otp_tokens, password_reset_tokens, crawled_pages, crawl_runs"


@pytest.fixture(scope="session")
def app():
    from app.main import app as fastapi_app
    return fastapi_app  # note: ASGITransport doesn't run the lifespan, so no model is loaded


@pytest.fixture
async def client(app):
    import httpx
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
async def clean_db():
    from sqlalchemy import text
    from app.database import async_session
    async with async_session() as db:
        await db.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
        await db.commit()
    yield


@pytest.fixture(autouse=True)
def reset_rate_limits():
    from app.utils.rate_limit import limiter
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture(autouse=True)
def fake_rag():
    from app.services.rag import set_rag_service
    fake = FakeRag()
    set_rag_service(fake)
    yield fake
    set_rag_service(None)


@pytest.fixture(autouse=True)
def outbox(monkeypatch):
    """Emails that would have been sent: {email: otp}."""
    import app.routers.auth as auth_router
    import app.routers.password_reset as reset_router
    sent = {}

    async def capture(email, otp):
        sent[email] = otp

    monkeypatch.setattr(auth_router, "send_otp_email", capture)
    monkeypatch.setattr(reset_router, "send_reset_email", capture)
    return sent


@pytest.fixture(autouse=True)
def admin_alerts(monkeypatch):
    """Alert emails to the admins (e.g. a failed website sync) that would have been sent: [(subject, body)]."""
    from app.services import website_sync
    sent = []

    async def capture(subject, body):
        sent.append((subject, body))

    monkeypatch.setattr(website_sync, "send_admin_alert", capture)
    monkeypatch.setattr(website_sync, "_last_alert", None)
    return sent


@pytest.fixture
def create_user():
    async def _create(email="student@apsit.edu.in", password="Secret123", full_name="Test Student"):
        from app.database import async_session
        from app.models import User
        from app.utils.security import get_password_hash
        async with async_session() as db:
            user = User(full_name=full_name, email=email, hashed_password=get_password_hash(password))
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return user
    return _create


@pytest.fixture
def login(client):
    async def _login(email="student@apsit.edu.in", password="Secret123"):
        r = await client.post("/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    return _login


@pytest.fixture
async def auth_headers(create_user, login):
    """A logged-in student (student@apsit.edu.in)."""
    await create_user()
    return await login()


@pytest.fixture
async def admin_headers(create_user, login):
    """A logged-in admin (admin@apsit.edu.in, see ADMIN_EMAIL above)."""
    await create_user(email="admin@apsit.edu.in", full_name="Admin User")
    return await login("admin@apsit.edu.in")
