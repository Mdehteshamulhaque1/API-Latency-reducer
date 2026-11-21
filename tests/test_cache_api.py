"""
Cache management API: stats, invalidation, role gating, and the per-rule
size budget enforced by the middleware.
"""
from app.database.db import async_session_maker
from app.models import CacheRule
from app.utils.redis_client import redis_client


async def add_rule(**kwargs):
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


async def test_stats_report_hits_misses_and_entries(client, admin_headers):
    await add_rule()
    await client.get("/api/v1/demo/latency")  # miss, stored
    await client.get("/api/v1/demo/latency")  # hit

    res = await client.get("/api/v1/cache/stats", headers=admin_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["available"] is True
    assert body["cache_hits"] >= 1
    assert body["cache_misses"] >= 1
    assert body["lookups"] == body["cache_hits"] + body["cache_misses"]
    assert body["response_entries"] >= 1
    assert body["total_rules"] == 1
    assert body["enabled_rules"] == 1
    assert body["default_ttl_seconds"] > 0


async def test_stats_require_authentication(client):
    res = await client.get("/api/v1/cache/stats")
    assert res.status_code == 401


async def test_invalidate_rule_forces_next_request_to_miss(client, operator_headers):
    await add_rule()
    await client.get("/api/v1/demo/latency")
    hit = await client.get("/api/v1/demo/latency")
    assert hit.headers.get("x-cache-hit") == "true"

    res = await client.post(
        "/api/v1/cache/invalidate",
        json={"endpoint_pattern": "/api/v1/demo/latency"},
        headers=operator_headers,
    )
    assert res.status_code == 200
    assert res.json()["deleted"] >= 1
    assert res.json()["scope"] == "rule:/api/v1/demo/latency"

    after = await client.get("/api/v1/demo/latency")
    assert after.headers.get("x-cache-hit") is None
    assert after.headers.get("x-cache-stored") == "true"


async def test_invalidate_all_leaves_rate_limit_buckets_alone(client, admin_headers):
    await add_rule()
    await client.get("/api/v1/demo/latency")
    # Create a rate-limit bucket for the anonymous IP by calling a limited route.
    await client.get("/api/v1/ping")
    assert await redis_client.exists("rate_limit:ip:127.0.0.1")

    res = await client.post("/api/v1/cache/invalidate", json={}, headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["scope"] == "all-responses"
    assert res.json()["deleted"] >= 1

    # The IP bucket survives (a FLUSHALL would have wiped it) and no response
    # entries remain.
    assert await redis_client.exists("rate_limit:ip:127.0.0.1")
    entries = [key async for key in redis_client.scan_iter("rule:*")]
    assert entries == []


async def test_viewer_cannot_invalidate(client, viewer_headers):
    res = await client.post("/api/v1/cache/invalidate", json={}, headers=viewer_headers)
    assert res.status_code == 403


async def test_response_larger_than_rule_budget_is_not_cached(client, admin_headers):
    # 120 rules with 1,000-character descriptions make GET /api/v1/rules
    # return well over 100 KB; a 100 KB budget on that route must skip the
    # store and say why.
    for index in range(120):
        await add_rule(
            endpoint_pattern=f"/api/v1/padding/{index}",
            description="x" * 1000,
        )
    await add_rule(endpoint_pattern="/api/v1/rules", max_cache_size=100, priority=10)

    res = await client.get("/api/v1/rules", headers=admin_headers)
    assert res.status_code == 200
    assert len(res.content) > 100 * 1024
    assert res.headers.get("x-cache-skipped") == "too-large"
    assert res.headers.get("x-cache-stored") is None

    again = await client.get("/api/v1/rules", headers=admin_headers)
    assert again.headers.get("x-cache-hit") is None
