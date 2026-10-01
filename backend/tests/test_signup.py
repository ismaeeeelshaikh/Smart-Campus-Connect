"""Signup with a college email + OTP."""
from sqlalchemy import select

from app.database import async_session
from app.models import SignupOtpToken

STUDENT = "new.student@apsit.edu.in"


async def signup(client, outbox, email=STUDENT, full_name="New Student", password="Secret123"):
    r = await client.post("/auth/request-signup-otp", json={"email": email})
    assert r.status_code == 200, r.text
    return await client.post("/auth/complete-signup", json={
        "full_name": full_name, "email": email, "password": password, "otp": outbox[email]})


async def test_only_college_emails_can_sign_up(client, outbox):
    r = await client.post("/auth/request-signup-otp", json={"email": "someone@gmail.com"})
    assert r.status_code == 400
    assert "apsit.edu.in" in r.json()["detail"]
    assert outbox == {}


async def test_admin_email_can_sign_up_with_any_domain(client, outbox, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "admin_email", "boss@gmail.com")
    r = await client.post("/auth/request-signup-otp", json={"email": "boss@gmail.com"})
    assert r.status_code == 200


async def test_full_signup_flow(client, outbox):
    r = await client.post("/auth/request-signup-otp", json={"email": STUDENT.upper()})
    assert r.status_code == 200
    assert STUDENT in outbox  # email was lowercased

    wrong = "000000" if outbox[STUDENT] != "000000" else "111111"
    r = await client.post("/auth/complete-signup", json={"full_name": "New Student", "email": STUDENT, "password": "Secret123", "otp": wrong})
    assert r.status_code == 400 and r.json()["detail"] == "Invalid or expired OTP"

    r = await client.post("/auth/complete-signup", json={"full_name": "New Student", "email": STUDENT, "password": "Secret123", "otp": outbox[STUDENT]})
    assert r.status_code == 200, r.text

    r = await client.post("/auth/login", json={"email": STUDENT, "password": "Secret123"})
    assert r.status_code == 200 and r.json()["user"]["full_name"] == "New Student"


async def test_otp_is_single_use(client, outbox):
    assert (await signup(client, outbox)).status_code == 200
    r = await client.post("/auth/complete-signup", json={"full_name": "Someone Else", "email": STUDENT, "password": "Secret123", "otp": outbox[STUDENT]})
    assert r.status_code == 400


async def test_registered_email_is_told_to_log_in(client, outbox):
    await signup(client, outbox)
    r = await client.post("/auth/request-signup-otp", json={"email": STUDENT})
    assert r.status_code == 400 and "already exists" in r.json()["detail"]


async def test_no_signup_without_otp(client):
    r = await client.post("/auth/register", json={"full_name": "X Y", "email": "x@gmail.com", "password": "Secret123"})
    assert r.status_code in (404, 405)


async def test_otp_is_stored_hashed(client, outbox):
    await client.post("/auth/request-signup-otp", json={"email": STUDENT})
    async with async_session() as db:
        stored = (await db.execute(select(SignupOtpToken.otp_hash).where(SignupOtpToken.email == STUDENT))).scalar_one()
    assert stored != outbox[STUDENT] and len(stored) == 64


async def test_five_wrong_otps_kill_the_code(client, outbox):
    await client.post("/auth/request-signup-otp", json={"email": STUDENT})
    wrong = "000000" if outbox[STUDENT] != "000000" else "111111"
    body = {"full_name": "New Student", "email": STUDENT, "password": "Secret123"}
    for _ in range(5):
        await client.post("/auth/complete-signup", json={**body, "otp": wrong})
    r = await client.post("/auth/complete-signup", json={**body, "otp": outbox[STUDENT]})
    assert r.status_code == 400


async def test_new_otp_cancels_the_old_one(client, outbox):
    await client.post("/auth/request-signup-otp", json={"email": STUDENT})
    first = outbox[STUDENT]
    await client.post("/auth/request-signup-otp", json={"email": STUDENT})
    if first != outbox[STUDENT]:
        r = await client.post("/auth/complete-signup", json={"full_name": "New Student", "email": STUDENT, "password": "Secret123", "otp": first})
        assert r.status_code == 400


async def test_email_failure_gives_friendly_503(client, monkeypatch):
    import app.routers.auth as auth_router

    async def broken(email, otp):
        raise RuntimeError("SMTP down")

    monkeypatch.setattr(auth_router, "send_otp_email", broken)
    r = await client.post("/auth/request-signup-otp", json={"email": STUDENT})
    assert r.status_code == 503 and "SMTP" not in r.text


async def test_two_students_can_share_a_name(client, outbox):
    assert (await signup(client, outbox, email="a@apsit.edu.in", full_name="Rohan Sawant")).status_code == 200
    assert (await signup(client, outbox, email="b@apsit.edu.in", full_name="Rohan Sawant")).status_code == 200


async def test_signup_validation(client, outbox):
    await client.post("/auth/request-signup-otp", json={"email": STUDENT})
    base = {"full_name": "New Student", "email": STUDENT, "password": "Secret123", "otp": outbox[STUDENT]}
    for field, bad, expected in [
        ("password", "weak", "8-128"),
        ("full_name", "R2-D2 #1", "full name"),
        ("otp", "12ab56", None),
    ]:
        r = await client.post("/auth/complete-signup", json={**base, field: bad})
        assert r.status_code == 422, (field, r.text)
        if expected:
            assert expected in r.text
