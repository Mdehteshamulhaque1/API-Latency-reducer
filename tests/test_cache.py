"""
End-to-end cache behavior tests: hit/miss semantics, keying, TTL, and
invariants (only 200 GET responses are cached, and certain paths never are).
"""
import asyncio

from app.database.db import async_session_maker
from app.models import CacheRule


async def add_rule(**kwargs):
    """Insert a cache rule directly into the test DB (same event loop)."""
    defaults = {
        "endpoint_pattern": "/api/v1/demo/latency",
        "ttl": 60,
        "enabled": True,
        "cache_by_user": False,
        "cache_by_query_params": False,
        "cache_by_headers": False,
        "max_cache_size": 1000,
        "priority": 0,
        "description": "test rule",
    }
    defaults.update(kwargs)
    async with async_session_maker() as session:
        session.add(CacheRule(**defaults))
        await session.commit()


async def test_first_request_misses_then_hits(client):
    await add_rule()

    first = await client.get("/api/v1/demo/latency")
    assert first.status_code == 200
    assert first.headers.get("x-cache-hit") is None
    assert first.headers.get("x-cache-stored") == "true"

    second = await client.get("/api/v1/demo/latency")
    assert second.status_code == 200
    assert second.headers.get("x-cache-hit") == "true"
    assert second.json() == first.json()


async def test_query_params_create_distinct_cache_entries(client):
    await add_rule(cache_by_query_params=True)

    first = await client.get("/api/v1/demo/latency", params={"skip": "0"})
    assert first.headers.get("x-cache-hit") is None

    second = await client.get("/api/v1/demo/latency", params={"skip": "0"})
    assert second.headers.get("x-cache-hit") == "true"

    different = await client.get("/api/v1/demo/latency", params={"skip": "5"})
    assert different.headers.get("x-cache-hit") is None


async def test_disabled_rule_is_not_cached(client):
    await add_rule(enabled=False)

    first = await client.get("/api/v1/demo/latency")
    second = await client.get("/api/v1/demo/latency")
    assert first.headers.get("x-cache-hit") is None
    assert second.headers.get("x-cache-hit") is None


async def test_ttl_expiry_invalidates_cache(client):
    await add_rule(ttl=1)

    first = await client.get("/api/v1/demo/latency")
    assert first.headers.get("x-cache-stored") == "true"

    second = await client.get("/api/v1/demo/latency")
    assert second.headers.get("x-cache-hit") == "true"

    await asyncio.sleep(1.2)

    third = await client.get("/api/v1/demo/latency")
    assert third.headers.get("x-cache-hit") is None
    assert third.headers.get("x-cache-stored") == "true"


async def test_non_200_responses_are_not_cached(client, admin_headers):
    await add_rule(endpoint_pattern="/api/v1/rules", ttl=600)

    res = await client.get(
        "/api/v1/rules/999999", headers=admin_headers
    )
    assert res.status_code == 404
    assert res.headers.get("x-cache-stored") is None


async def test_non_get_methods_are_not_cached(client, admin_headers):
    await add_rule(endpoint_pattern="/api/v1/rules", ttl=600)

    payload = {
        "endpoint_pattern": "/api/v1/post-test-rule",
        "ttl": 300,
        "enabled": True,
        "max_cache_size": 1000,
        "priority": 1,
    }
    res = await client.post("/api/v1/rules", json=payload, headers=admin_headers)
    assert res.status_code == 200
    assert res.headers.get("x-cache-hit") is None
    assert res.headers.get("x-cache-stored") is None


async def test_excluded_paths_are_never_cached(client):
    for path in ("/api/v1/health", "/api/v1/ping"):
        first = await client.get(path)
        second = await client.get(path)
        assert first.headers.get("x-cache-hit") is None
        assert second.headers.get("x-cache-hit") is None


async def test_cached_response_preserves_content_type(client):
    await add_rule()

    await client.get("/api/v1/demo/latency")
    hit = await client.get("/api/v1/demo/latency")
    assert hit.headers.get("x-cache-hit") == "true"
    assert "application/json" in hit.headers.get("content-type", "")
