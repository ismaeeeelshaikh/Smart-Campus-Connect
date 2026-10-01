"""Login, the /auth/me profile endpoints, and rate limits."""


async def test_login(client, create_user):
    await create_user()
    r = await client.post("/auth/login", json={"email": "STUDENT@APSIT.EDU.IN", "password": "Secret123"})
    assert r.status_code == 200
    user = r.json()["user"]
    assert user["full_name"] == "Test Student" and user["is_admin"] is False


async def test_wrong_password_is_a_clean_401(client, create_user):
    await create_user()
    r = await client.post("/auth/login", json={"email": "student@apsit.edu.in", "password": "Wrong123"})
    assert r.status_code == 401 and r.json()["detail"] == "Incorrect email or password"


async def test_admin_flag(client, create_user):
    await create_user(email="admin@apsit.edu.in")
    r = await client.post("/auth/login", json={"email": "admin@apsit.edu.in", "password": "Secret123"})
    assert r.json()["user"]["is_admin"] is True


async def test_huge_password_is_rejected_before_hashing(client):
    r = await client.post("/auth/login", json={"email": "student@apsit.edu.in", "password": "x" * 200})
    assert r.status_code == 422


async def test_profile_get_and_update(client, auth_headers):
    r = await client.get("/auth/me", headers=auth_headers)
    assert r.status_code == 200 and r.json()["full_name"] == "Test Student"

    r = await client.patch("/auth/me", json={"full_name": "  Rohan   Sawant "}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["full_name"] == "Rohan Sawant"

    r = await client.patch("/auth/me", json={"full_name": "मुग्धा अगरवाडकर"}, headers=auth_headers)
    assert r.status_code == 200  # names in Devanagari are allowed

    r = await client.patch("/auth/me", json={"full_name": "x"}, headers=auth_headers)
    assert r.status_code == 422


async def test_profile_needs_login(client):
    assert (await client.get("/auth/me")).status_code in (401, 403)
    assert (await client.patch("/auth/me", json={"full_name": "Rohan"})).status_code in (401, 403)
    assert (await client.get("/auth/me", headers={"Authorization": "Bearer not-a-token"})).status_code == 401


async def test_login_rate_limit_per_email(client, create_user):
    await create_user()
    codes = [(await client.post("/auth/login", json={"email": "attacker@apsit.edu.in", "password": "Wrong123"})).status_code
             for _ in range(11)]
    assert codes[:10] == [401] * 10 and codes[10] == 429
    r = await client.post("/auth/login", json={"email": "attacker@apsit.edu.in", "password": "Wrong123"})
    assert "Too many attempts" in r.json()["detail"] and "Retry-After" in r.headers
    # another account is not affected
    r = await client.post("/auth/login", json={"email": "student@apsit.edu.in", "password": "Secret123"})
    assert r.status_code == 200


async def test_signup_otp_rate_limit(client):
    codes = [(await client.post("/auth/request-signup-otp", json={"email": "flood@apsit.edu.in"})).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]


async def test_security_headers(client):
    r = await client.get("/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
