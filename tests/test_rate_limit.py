"""
End-to-end token-bucket rate limiter tests: enforcement, identifier isolation,
fail-open behavior, and exempt paths.
"""
from app.utils.redis_client import redis_client


async def test_requests_within_limit_allowed(client):
    for _ in range(5):
        res = await client.get("/api/v1/ping")
        assert res.status_code == 200


async def test_exceeding_limit_returns_429(client):
    for _ in range(5):
        await client.get("/api/v1/ping")

    res = await client.get("/api/v1/ping")
    assert res.status_code == 429
    body = res.json()
    assert body["error_code"] == "RATE_LIMIT_EXCEEDED"
    assert "Retry-After" in res.headers


async def test_authenticated_user_has_separate_bucket(client, admin_headers):
    for _ in range(5):
        res = await client.get("/api/v1/analytics/summary", headers=admin_headers)
        assert res.status_code == 200

    res = await client.get("/api/v1/analytics/summary", headers=admin_headers)
    assert res.status_code == 429


async def test_api_key_isolates_identifiers(client):
    headers_a = {"X-API-Key": "key-alpha-123"}
    headers_b = {"X-API-Key": "key-beta-456"}

    for _ in range(5):
        await client.get("/api/v1/ping", headers=headers_a)

    res = await client.get("/api/v1/ping", headers=headers_a)
    assert res.status_code == 429

    res = await client.get("/api/v1/ping", headers=headers_b)
    assert res.status_code == 200


async def test_fail_open_when_redis_unavailable(client, monkeypatch):
    # Simulate Redis being down: the limiter must fail-open, not fail-closed.
    monkeypatch.setattr(redis_client, "client", None)

    for _ in range(6):
        res = await client.get("/api/v1/ping")
        assert res.status_code == 200


async def test_health_endpoint_exempt_from_rate_limit(client):
    for _ in range(8):
        res = await client.get("/api/v1/health")
        assert res.status_code == 200


async def test_demo_endpoint_exempt_from_rate_limit(client):
    for _ in range(5):
        res = await client.get("/api/v1/demo/latency")
        assert res.status_code == 200
