"""
POST /api/v1/ingest/requests: a monitored service (Esone) ships its request
log here, and the analytics endpoints can be scoped to that service.
"""
from sqlalchemy import delete

from app.database.db import async_session_maker
from app.models import APILog

ESONE_ROWS = [
    {
        "service": "esone",
        "direction": "inbound",
        "method": "post",
        "endpoint": "/api/v1/chat",
        "status_code": 200,
        "response_time_ms": 820.5,
        "client_ip": "203.0.113.9",
        "correlation_id": "corr-1",
        "request_size_bytes": 64,
        "response_size_bytes": 512,
        "cache_hit": True,
    },
    {
        "service": "esone",
        "direction": "outbound",
        "method": "POST",
        "endpoint": "localhost:8001/api/v1/answers",
        "upstream_host": "localhost:8001",
        "status_code": 200,
        "response_time_ms": 790.0,
        "client_ip": "esone-api",
        "correlation_id": "corr-1",
    },
    {
        "service": "esone",
        "direction": "inbound",
        "method": "GET",
        "endpoint": "/api/v1/users/me",
        "status_code": 401,
        "response_time_ms": 3.2,
        "client_ip": "203.0.113.9",
        "correlation_id": "corr-2",
    },
]


async def _clear_esone_rows():
    async with async_session_maker() as session:
        await session.execute(delete(APILog).where(APILog.service == "esone"))
        await session.commit()


async def test_ingest_requires_operator_or_admin(client, viewer_headers):
    res = await client.post("/api/v1/ingest/requests", json={"records": ESONE_ROWS[:1]}, headers=viewer_headers)
    assert res.status_code == 403


async def test_ingest_validates_records(client, operator_headers):
    bad = {**ESONE_ROWS[0], "direction": "sideways"}
    res = await client.post("/api/v1/ingest/requests", json={"records": [bad]}, headers=operator_headers)
    assert res.status_code == 422
    res = await client.post("/api/v1/ingest/requests", json={"records": []}, headers=operator_headers)
    assert res.status_code == 422


async def test_ingested_rows_are_scoped_by_service(client, operator_headers, viewer_headers):
    await _clear_esone_rows()
    res = await client.post("/api/v1/ingest/requests", json={"records": ESONE_ROWS}, headers=operator_headers)
    assert res.status_code == 202, res.text
    assert res.json() == {"accepted": 3}

    # Any dashboard user can analyse the monitored service's traffic.
    res = await client.get("/api/v1/analytics/summary?service=esone", headers=viewer_headers)
    assert res.status_code == 200
    summary = res.json()
    assert summary["total_requests"] == 3
    assert summary["total_errors"] == 1
    endpoints = {item["endpoint"] for item in summary["top_endpoints"]}
    assert endpoints == {"/api/v1/chat", "localhost:8001/api/v1/answers", "/api/v1/users/me"}
    recent = {(r["direction"], r["method"]) for r in summary["recent_requests"]}
    assert ("outbound", "POST") in recent and ("inbound", "POST") in recent  # method upper-cased

    # Direction narrows to what the service served or what it called.
    res = await client.get("/api/v1/analytics/summary?service=esone&direction=outbound", headers=viewer_headers)
    assert res.json()["total_requests"] == 1
    assert res.json()["recent_requests"][0]["upstream_host"] == "localhost:8001"

    # Raw log explorer honours the same scoping.
    res = await client.get("/api/v1/analytics/endpoints?service=esone&direction=inbound", headers=viewer_headers)
    assert res.status_code == 200
    assert {row["endpoint"] for row in res.json()} == {"/api/v1/chat", "/api/v1/users/me"}
    assert all(row["service"] == "esone" for row in res.json())

    # Without ``service`` the caller's own gateway requests are returned, as before.
    res = await client.get("/api/v1/analytics/endpoints?endpoint_pattern=/api/v1/chat", headers=viewer_headers)
    assert all(row["service"] == "api-optimizer" for row in res.json())

    # ``method`` narrows the substring match: GET /api/v1/chat/history is not a chat question.
    from app.utils.redis_client import redis_client

    for key in [key async for key in redis_client.scan_iter("rate_limit:*")]:
        await redis_client.delete(key)  # the 5-token test bucket is spent by now
    res = await client.get(
        "/api/v1/analytics/endpoints?service=esone&endpoint_pattern=/chat&method=post", headers=viewer_headers
    )
    assert res.status_code == 200, res.text
    assert [(row["method"], row["endpoint"]) for row in res.json()] == [("POST", "/api/v1/chat")]
    res = await client.get("/api/v1/analytics/endpoints?service=esone&method=GET", headers=viewer_headers)
    assert res.status_code == 200, res.text
    assert {row["endpoint"] for row in res.json()} == {"/api/v1/users/me"}
    assert (await client.get("/api/v1/analytics/endpoints?method=P0ST!", headers=viewer_headers)).status_code == 422

    # The service list shows the gateway itself first, then monitored services.
    res = await client.get("/api/v1/analytics/services", headers=viewer_headers)
    assert res.status_code == 200
    services = res.json()
    esone = next(item for item in services if item["service"] == "esone")
    assert esone["is_self"] is False
    assert esone["inbound"] == 2 and esone["outbound"] == 1 and esone["errors"] == 1
    assert services[0]["service"] == "api-optimizer" and services[0]["is_self"] is True

    await _clear_esone_rows()


async def test_service_scopes_other_dashboard_reads(client, operator_headers, viewer_headers, admin_headers):
    """Cache hits, 429s, LLM usage and guardrail events can all be read per service.

    Reads are spread over three accounts because the test rate limit is five
    requests per user.
    """
    await _clear_esone_rows()
    rows = ESONE_ROWS + [
        {
            "service": "esone",
            "direction": "inbound",
            "method": "POST",
            "endpoint": "/api/v1/auth/login",
            "status_code": 429,
            "response_time_ms": 0.4,
            "client_ip": "198.51.100.7",
            "correlation_id": "corr-3",
        }
    ]
    res = await client.post("/api/v1/ingest/requests", json={"records": rows}, headers=operator_headers)
    assert res.status_code == 202

    summary = (await client.get("/api/v1/analytics/summary?service=esone", headers=operator_headers)).json()
    assert summary["total_requests"] == 4
    assert summary["rate_limited_requests"] == 1
    assert round(summary["cache_hit_rate"], 2) == 25.0  # the cached chat answer

    events = (await client.get("/api/v1/rate-limits/events?service=esone", headers=operator_headers)).json()
    assert events["scope"] == "service"
    assert events["rate_limited_requests"] == 1
    assert events["events"][0]["endpoint"] == "/api/v1/auth/login"
    assert events["events"][0]["client_ip"] == "198.51.100.7"

    services = (await client.get("/api/v1/analytics/services", headers=operator_headers)).json()
    esone = next(item for item in services if item["service"] == "esone")
    assert esone["account_user_id"] is not None  # the operator that shipped the rows

    # LLM usage and guardrail events are attributed to the shipping account; a
    # viewer may read them through the service scope, and sees nothing for a
    # service that has never shipped rows.
    for path in ("/api/v1/ai-usage/summary", "/api/v1/guardrails/summary"):
        res = await client.get(f"{path}?service=esone", headers=viewer_headers)
        assert res.status_code == 200 and res.json()["scope"] == "service"
        res = await client.get(f"{path}?service=nobody", headers=viewer_headers)
        assert res.status_code == 200 and res.json()["scope"] == "service"
    res = await client.get("/api/v1/ai-usage/requests?service=nobody", headers=viewer_headers)
    assert res.json()["items"] == []

    # The assistant accepts the same scope for its troubleshooting evidence.
    res = await client.post(
        "/api/v1/assistant/troubleshoot",
        json={"status_code": 429, "hours": 24, "service": "esone"},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json()["evidence"]["rate_limits"]["rate_limited_requests"] == 1

    await _clear_esone_rows()
