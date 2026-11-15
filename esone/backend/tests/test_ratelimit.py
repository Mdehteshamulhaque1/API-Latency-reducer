from esone_api.config import get_settings


async def test_login_is_rate_limited_per_ip(client, monkeypatch):
    monkeypatch.setenv("ESONE_AUTH_RATE_LIMIT_PER_MINUTE", "3")
    get_settings.cache_clear()

    body = {"username": "nobody", "password": "wrong-pass-123"}
    for _ in range(3):
        assert (await client.post("/api/v1/auth/login", json=body)).status_code == 401

    blocked = await client.post("/api/v1/auth/login", json=body)
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
    assert blocked.json()["detail"].startswith("Too many attempts")

    # A different client IP (via the proxy header) is not affected.
    other = await client.post("/api/v1/auth/login", json=body, headers={"X-Forwarded-For": "203.0.113.9"})
    assert other.status_code == 401

    # Unrelated routes are never limited.
    assert (await client.get("/api/v1/health")).status_code == 200


async def test_rate_limit_can_be_disabled(client, monkeypatch):
    monkeypatch.setenv("ESONE_AUTH_RATE_LIMIT_PER_MINUTE", "0")
    get_settings.cache_clear()
    body = {"username": "nobody", "password": "wrong-pass-123"}
    for _ in range(15):
        assert (await client.post("/api/v1/auth/login", json=body)).status_code == 401
