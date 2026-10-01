"""Admin-only website sync endpoints."""


async def test_non_admins_are_refused(client, auth_headers):
    assert (await client.get("/admin/website-sync", headers=auth_headers)).status_code == 403
    assert (await client.post("/admin/website-sync", headers=auth_headers)).status_code == 403
    r = await client.post("/admin/website-sync/page", json={"url": "https://www.apsit.edu.in/"}, headers=auth_headers)
    assert r.status_code == 403
    assert (await client.get("/admin/website-sync")).status_code in (401, 403)


async def test_admin_sees_sync_status(client, admin_headers):
    r = await client.get("/admin/website-sync", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["running"] is False and body["last"] is None and body["pages_indexed"] == 0


async def test_several_admins_comma_separated(client, create_user, login, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "admin_email", "someone@else.com, second.admin@apsit.edu.in")
    await create_user(email="second.admin@apsit.edu.in")
    headers = await login("second.admin@apsit.edu.in")
    assert (await client.get("/admin/website-sync", headers=headers)).status_code == 200


async def test_single_page_sync_only_for_the_college_site(client, admin_headers):
    r = await client.post("/admin/website-sync/page", json={"url": "https://evil.example.com/page"}, headers=admin_headers)
    assert r.status_code == 400
