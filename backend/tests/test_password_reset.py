"""Forgot password: OTP by email, single use, logs out other sessions."""
import asyncio

from sqlalchemy import select

from app.database import async_session
from app.models import User

EMAIL = "student@apsit.edu.in"


async def test_reset_flow_and_session_revocation(client, outbox, auth_headers):
    r = await client.post("/password-reset/request-reset", json={"email": EMAIL})
    assert r.status_code == 200 and EMAIL in outbox
    assert (await client.get("/chat-sessions", headers=auth_headers)).status_code == 200

    await asyncio.sleep(1.1)  # tokens carry whole seconds; the reset must come after the login
    r = await client.post("/password-reset/reset-password", json={"email": EMAIL, "otp": outbox[EMAIL], "new_password": "NewSecret456"})
    assert r.status_code == 200, r.text

    # the old login is logged out, the new password works
    assert (await client.get("/chat-sessions", headers=auth_headers)).status_code == 401
    r = await client.post("/auth/login", json={"email": EMAIL, "password": "NewSecret456"})
    assert r.status_code == 200
    new_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert (await client.get("/chat-sessions", headers=new_headers)).status_code == 200

    # the code can't be used twice
    r = await client.post("/password-reset/reset-password", json={"email": EMAIL, "otp": outbox[EMAIL], "new_password": "Another789"})
    assert r.status_code == 400

    async with async_session() as db:
        hashed = (await db.execute(select(User.hashed_password).where(User.email == EMAIL))).scalar_one()
    assert hashed.startswith("$argon2")


async def test_wrong_code_and_unknown_email_look_the_same(client, outbox, create_user):
    await create_user()
    await client.post("/password-reset/request-reset", json={"email": EMAIL})
    wrong = "000000" if outbox[EMAIL] != "000000" else "111111"
    r1 = await client.post("/password-reset/reset-password", json={"email": EMAIL, "otp": wrong, "new_password": "NewSecret456"})
    r2 = await client.post("/password-reset/reset-password", json={"email": "nobody@apsit.edu.in", "otp": "123456", "new_password": "NewSecret456"})
    assert r1.status_code == r2.status_code == 400
    assert r1.json() == r2.json() == {"detail": "Invalid or expired OTP"}


async def test_unknown_email_gets_the_same_request_message(client, outbox):
    r = await client.post("/password-reset/request-reset", json={"email": "nobody@apsit.edu.in"})
    assert r.status_code == 200 and outbox == {}


async def test_weak_new_password_is_rejected(client, outbox, create_user):
    await create_user()
    await client.post("/password-reset/request-reset", json={"email": EMAIL})
    r = await client.post("/password-reset/reset-password", json={"email": EMAIL, "otp": outbox[EMAIL], "new_password": "weakpass"})
    assert r.status_code == 422


async def test_reset_request_rate_limit(client, create_user):
    await create_user()
    codes = [(await client.post("/password-reset/request-reset", json={"email": EMAIL})).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]
