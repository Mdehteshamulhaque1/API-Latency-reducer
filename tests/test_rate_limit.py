"""
End-to-end token-bucket rate limiter tests: enforcement, identifier isolation,
headers, fail-open behavior, and exempt paths.

conftest sets every tier to 5 requests per 3600 s, so every bucket holds
5 tokens and refills far too slowly to matter here.
"""
from app.config import settings
from app.services.rate_limit import limits_for_role
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


async def test_rate_limit_headers_count_down(client):
    first = await client.get("/api/v1/ping")
    assert first.headers["X-RateLimit-Limit"] == "5"
    assert first.headers["X-RateLimit-Remaining"] == "4"
    assert int(first.headers["X-RateLimit-Reset"]) >= 0
    # IETF draft names carry the same values, plus the policy "<limit>;w=<window>".
    assert first.headers["RateLimit-Limit"] == "5"
    assert first.headers["RateLimit-Remaining"] == "4"
    assert first.headers["RateLimit-Reset"] == first.headers["X-RateLimit-Reset"]
    assert first.headers["RateLimit-Policy"] == "5;w=3600"

    second = await client.get("/api/v1/ping")
    assert second.headers["X-RateLimit-Remaining"] == "3"
    assert second.headers["RateLimit-Remaining"] == "3"


def test_tiers_follow_role(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_anonymous_requests", 60)
    monkeypatch.setattr(settings, "rate_limit_anonymous_period", 60)
    monkeypatch.setattr(settings, "rate_limit_user_requests", 300)
    monkeypatch.setattr(settings, "rate_limit_user_period", 60)
    monkeypatch.setattr(settings, "rate_limit_privileged_requests", 1000)
    monkeypatch.setattr(settings, "rate_limit_privileged_period", 60)

    anonymous = limits_for_role(None, authenticated=False)
    viewer = limits_for_role("viewer")
    guest = limits_for_role("guest")
    operator = limits_for_role("operator")
    admin = limits_for_role("admin")
    assert (anonymous.name, anonymous.requests, anonymous.period) == ("anonymous", 60, 60)
    assert (viewer.name, viewer.requests) == ("user", 300) and guest.requests == 300
    assert (operator.name, operator.requests) == ("privileged", 1000) and admin.requests == 1000
    assert anonymous.policy == "60;w=60" and admin.refill_per_second == 1000 / 60


async def test_tier_applies_per_caller(client, admin_headers, monkeypatch):
    """A privileged account gets its own, larger bucket while anonymous callers keep theirs."""
    monkeypatch.setattr(settings, "rate_limit_privileged_requests", 8)
    first = await client.get("/api/v1/analytics/summary", headers=admin_headers)
    assert first.status_code == 200
    assert first.headers["RateLimit-Limit"] == "8"
    assert first.headers["RateLimit-Policy"] == "8;w=3600"
    anonymous = await client.get("/api/v1/ping")
    assert anonymous.headers["RateLimit-Limit"] == "5"


async def test_retry_after_reflects_next_token_not_full_period(client):
    for _ in range(5):
        await client.get("/api/v1/ping")

    res = await client.get("/api/v1/ping")
    assert res.status_code == 429
    retry_after = int(res.headers["Retry-After"])
    # Refill is 5 tokens / 3600 s, so the next token arrives in ~720 s,
    # well under the full period the old implementation reported.
    assert 1 <= retry_after <= 720
    assert res.headers["X-RateLimit-Remaining"] == "0"


async def test_authenticated_user_has_separate_bucket(client, admin_headers):
    for _ in range(5):
        res = await client.get("/api/v1/analytics/summary", headers=admin_headers)
        assert res.status_code == 200

    res = await client.get("/api/v1/analytics/summary", headers=admin_headers)
    assert res.status_code == 429


async def test_api_key_header_cannot_bypass_ip_bucket(client):
    """A spoofable header must not create a fresh bucket."""
    for _ in range(5):
        await client.get("/api/v1/ping")

    res = await client.get("/api/v1/ping", headers={"X-API-Key": "made-up-key"})
    assert res.status_code == 429


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
