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
    assert blocked.headers["RateLimit-Limit"] == "3"
    assert blocked.headers["RateLimit-Remaining"] == "0"
    assert blocked.headers["RateLimit-Policy"] == "3;w=60"
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


async def test_default_login_limit_is_five_per_minute(client, monkeypatch):
    from esone_api.config import Settings

    # The code default (a developer's .env may override it locally).
    assert Settings.model_fields["auth_rate_limit_per_minute"].default == 5
    monkeypatch.setenv("ESONE_AUTH_RATE_LIMIT_PER_MINUTE", "5")
    get_settings.cache_clear()
    body = {"username": "nobody", "password": "wrong-pass-123"}
    for _ in range(5):
        assert (await client.post("/api/v1/auth/login", json=body)).status_code == 401
    assert (await client.post("/api/v1/auth/login", json=body)).status_code == 429
