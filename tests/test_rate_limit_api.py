"""
Rate-limit API: configuration, the caller's own bucket, and 429 events.

Requests must hit a PROTECTED route for the user bucket to apply:
/api/v1/ping is public, so a token sent there is ignored and the IP bucket
is charged instead.
"""
import asyncio

PROTECTED = "/api/v1/rate-limits/config"


async def _drain_bucket(client, headers):
    """Use up the 5-token user bucket, producing one 429 row in the request log."""
    for _ in range(5):
        res = await client.get(PROTECTED, headers=headers)
        assert res.status_code == 200
    res = await client.get(PROTECTED, headers=headers)
    assert res.status_code == 429
    # Analytics rows are written in a background task after the response.
    await asyncio.sleep(0.3)


async def test_config_describes_token_bucket(client, viewer_headers):
    res = await client.get("/api/v1/rate-limits/config", headers=viewer_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["enabled"] is True
    assert body["algorithm"] == "token_bucket"
    assert body["your_tier"] == "user"
    assert body["capacity"] == 5
    assert body["period_seconds"] == 3600
    assert body["failure_policy"] == "fail-open"
    assert "/api/v1/health" in body["excluded_paths"]
    assert [tier["name"] for tier in body["tiers"]] == ["anonymous", "user", "privileged"]
    assert all(tier["capacity"] == 5 and tier["policy"] == "5;w=3600" for tier in body["tiers"])
    assert "RateLimit-Policy" in body["headers"] and "X-RateLimit-Limit" in body["headers"]


async def test_me_reflects_tokens_used(client, viewer_headers):
    await client.get(PROTECTED, headers=viewer_headers)
    await client.get(PROTECTED, headers=viewer_headers)

    res = await client.get("/api/v1/rate-limits/me", headers=viewer_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["identifier"] == "user:3"
    assert body["tier"] == "user"
    assert body["limit"] == 5
    assert body["has_bucket"] is True
    # Two config calls plus the /me call itself consumed three tokens.
    assert body["used"] == 3
    assert body["remaining"] == 2
    assert body["reset_in_seconds"] > 0


async def test_events_scoped_to_own_user_for_non_admins(client, viewer_headers, operator_headers):
    await _drain_bucket(client, viewer_headers)

    res = await client.get("/api/v1/rate-limits/events", headers=operator_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["scope"] == "own"
    # The viewer's 429 must not leak into the operator's view.
    assert all(event["user_id"] == 2 for event in body["events"])


async def test_events_visible_to_admin_across_users(client, viewer_headers, admin_headers):
    await _drain_bucket(client, viewer_headers)

    res = await client.get("/api/v1/rate-limits/events", headers=admin_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["scope"] == "all"
    assert body["rate_limited_requests"] >= 1
    viewer_events = [event for event in body["events"] if event["user_id"] == 3]
    assert viewer_events
    assert viewer_events[0]["endpoint"] == PROTECTED
    assert viewer_events[0]["correlation_id"]
    assert 0 < body["rate_limited_percent"] <= 100
