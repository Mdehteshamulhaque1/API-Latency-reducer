from tests.conftest import ADMIN, bearer, login, register


async def test_seeded_admin_can_list_users(client):
    await register(client)
    admin = await login(client, ADMIN["username"], ADMIN["password"])
    res = await client.get("/api/v1/admin/users", headers=bearer(admin))
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 2
    names = {u["username"] for u in body["items"]}
    assert names == {"root", "alice"}


async def test_viewer_cannot_use_admin_routes(client):
    await register(client)
    viewer = await login(client)
    assert (await client.get("/api/v1/admin/users", headers=bearer(viewer))).status_code == 403
    res = await client.patch("/api/v1/admin/users/1", json={"role": "admin"}, headers=bearer(viewer))
    assert res.status_code == 403


async def test_admin_can_change_role_and_deactivate(client):
    created = (await register(client)).json()
    alice = await login(client)
    admin = await login(client, ADMIN["username"], ADMIN["password"])

    promoted = await client.patch(
        f"/api/v1/admin/users/{created['id']}", json={"role": "operator"}, headers=bearer(admin)
    )
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "operator"

    deactivated = await client.patch(
        f"/api/v1/admin/users/{created['id']}", json={"is_active": False}, headers=bearer(admin)
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    # Deactivated user is locked out everywhere.
    assert (await client.get("/api/v1/users/me", headers=bearer(alice))).status_code == 403
    assert (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": alice["refresh_token"]})
    ).status_code == 401
    relogin = await client.post("/api/v1/auth/login", json={"username": "alice", "password": "alice-pass-123"})
    assert relogin.status_code == 403

    bad_role = await client.patch(
        f"/api/v1/admin/users/{created['id']}", json={"role": "superuser"}, headers=bearer(admin)
    )
    assert bad_role.status_code == 422
    missing = await client.patch("/api/v1/admin/users/9999", json={"role": "viewer"}, headers=bearer(admin))
    assert missing.status_code == 404


async def test_admin_cannot_demote_or_deactivate_self(client):
    admin = await login(client, ADMIN["username"], ADMIN["password"])
    me = (await client.get("/api/v1/users/me", headers=bearer(admin))).json()
    demote = await client.patch(f"/api/v1/admin/users/{me['id']}", json={"role": "viewer"}, headers=bearer(admin))
    assert demote.status_code == 400
    off = await client.patch(f"/api/v1/admin/users/{me['id']}", json={"is_active": False}, headers=bearer(admin))
    assert off.status_code == 400
