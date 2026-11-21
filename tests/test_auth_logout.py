"""
Logout and token revocation: the access token stops working immediately,
the refresh token can no longer be exchanged, and Redis outages fail open.
"""
from app.core.security import JWTHandler
from app.utils.redis_client import redis_client


async def _login(client, username="viewer", password="viewer-pass-123"):
    res = await client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert res.status_code == 200
    return res.json()


async def test_tokens_carry_unique_ids():
    first = JWTHandler.decode_token(JWTHandler.create_access_token({"sub": "1", "role": "admin"}))
    second = JWTHandler.decode_token(JWTHandler.create_access_token({"sub": "1", "role": "admin"}))
    assert first["jti"] and second["jti"]
    assert first["jti"] != second["jti"]


async def test_logout_revokes_access_and_refresh_tokens(client):
    tokens = await _login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    before = await client.get("/api/v1/rate-limits/config", headers=headers)
    assert before.status_code == 200

    res = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["message"] == "Logged out"

    after = await client.get("/api/v1/rate-limits/config", headers=headers)
    assert after.status_code == 401
    assert "revoked" in after.json()["detail"].lower()

    refresh = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh.status_code == 401


async def test_logout_rejects_another_users_refresh_token(client):
    viewer = await _login(client)
    operator = await _login(client, "operator", "operator-pass-123")
    headers = {"Authorization": f"Bearer {viewer['access_token']}"}

    res = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": operator["refresh_token"]},
        headers=headers,
    )
    assert res.status_code == 401

    # The operator's session is untouched.
    refresh = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": operator["refresh_token"]}
    )
    assert refresh.status_code == 200


async def test_logout_requires_a_refresh_token_not_an_access_token(client):
    tokens = await _login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    res = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["access_token"]},
        headers=headers,
    )
    assert res.status_code == 401


async def test_revocation_fails_open_when_redis_is_down(client, monkeypatch):
    tokens = await _login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    monkeypatch.setattr(redis_client, "client", None)
    res = await client.get("/api/v1/rate-limits/config", headers=headers)
    assert res.status_code == 200
