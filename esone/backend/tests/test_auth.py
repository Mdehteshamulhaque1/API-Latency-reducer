from jose import jwt

from tests.conftest import bearer, login, register


async def test_register_returns_viewer_and_ignores_role(client):
    res = await client.post(
        "/api/v1/auth/register",
        json={"username": "bob", "email": "bob@example.com", "password": "bob-pass-123", "role": "admin"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["username"] == "bob"
    assert body["role"] == "viewer"
    assert body["is_active"] is True
    assert "hashed_password" not in body


async def test_register_rejects_duplicates_and_short_passwords(client):
    assert (await register(client)).status_code == 201
    dup = await register(client, email="other@example.com")
    assert dup.status_code == 409
    dup_email = await register(client, username="someone-else")
    assert dup_email.status_code == 409
    short = await register(client, username="carol", email="carol@example.com", password="short")
    assert short.status_code == 422


async def test_login_returns_token_pair_with_claims(client):
    await register(client)
    tokens = await login(client)
    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] == 15 * 60
    access = jwt.get_unverified_claims(tokens["access_token"])
    refresh = jwt.get_unverified_claims(tokens["refresh_token"])
    assert access["type"] == "access" and refresh["type"] == "refresh"
    assert access["role"] == "viewer"
    assert access["sub"] == refresh["sub"]


async def test_login_wrong_password_is_401(client):
    await register(client)
    res = await client.post("/api/v1/auth/login", json={"username": "alice", "password": "nope-nope-1"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid username or password"
    unknown = await client.post("/api/v1/auth/login", json={"username": "ghost", "password": "nope-nope-1"})
    assert unknown.status_code == 401


async def test_refresh_rotates_and_old_token_is_rejected(client):
    await register(client)
    first = await login(client)

    res = await client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert res.status_code == 200, res.text
    second = res.json()
    assert second["refresh_token"] != first["refresh_token"]

    # The rotated-out token no longer works.
    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert reuse.status_code == 401

    # Reuse detection revoked the whole family, including the newest token.
    newest = await client.post("/api/v1/auth/refresh", json={"refresh_token": second["refresh_token"]})
    assert newest.status_code == 401


async def test_access_token_cannot_be_used_as_refresh_and_vice_versa(client):
    await register(client)
    tokens = await login(client)
    res = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert res.status_code == 401
    me = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert me.status_code == 401


async def test_logout_revokes_refresh_token(client):
    await register(client)
    tokens = await login(client)
    res = await client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert res.status_code == 204
    again = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert again.status_code == 401
    # Idempotent and tolerant of garbage.
    assert (await client.post("/api/v1/auth/logout", json={"refresh_token": "garbage"})).status_code == 204


async def test_protected_route_requires_bearer(client):
    assert (await client.get("/api/v1/users/me")).status_code == 401
    bad = await client.get("/api/v1/users/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert bad.status_code == 401
    await register(client)
    ok = await client.get("/api/v1/users/me", headers=bearer(await login(client)))
    assert ok.status_code == 200


async def test_health_and_ping(client):
    res = await client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy", "database": "healthy", "version": "1.0.0"}
    assert (await client.get("/api/v1/ping")).json() == {"message": "pong"}
