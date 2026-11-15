from tests.conftest import bearer, login, register


async def test_me_returns_profile(client):
    await register(client)
    tokens = await login(client)
    res = await client.get("/api/v1/users/me", headers=bearer(tokens))
    assert res.status_code == 200
    body = res.json()
    assert body["username"] == "alice"
    assert body["email"] == "alice@example.com"
    assert body["role"] == "viewer"
    assert "created_at" in body


async def test_change_password_revokes_sessions(client):
    await register(client)
    tokens = await login(client)

    wrong = await client.post(
        "/api/v1/users/me/password",
        json={"current_password": "wrong-pass-123", "new_password": "new-pass-12345"},
        headers=bearer(tokens),
    )
    assert wrong.status_code == 400

    same = await client.post(
        "/api/v1/users/me/password",
        json={"current_password": "alice-pass-123", "new_password": "alice-pass-123"},
        headers=bearer(tokens),
    )
    assert same.status_code == 400

    ok = await client.post(
        "/api/v1/users/me/password",
        json={"current_password": "alice-pass-123", "new_password": "new-pass-12345"},
        headers=bearer(tokens),
    )
    assert ok.status_code == 204

    # Old refresh token is dead, old password no longer works, new one does.
    dead = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert dead.status_code == 401
    old = await client.post("/api/v1/auth/login", json={"username": "alice", "password": "alice-pass-123"})
    assert old.status_code == 401
    await login(client, password="new-pass-12345")
