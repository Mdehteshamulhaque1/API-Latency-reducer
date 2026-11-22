"""Real queries vs supporting traffic: GET /api/v1/analytics/queries."""
import asyncio
import uuid

import pytest

from app.services.query_breakdown import classify
from tests.test_answers import reset_rate_limits
from tests.test_view_as import _service


@pytest.mark.parametrize(
    ("direction", "method", "endpoint", "expected"),
    [
        ("inbound", "POST", "/api/v1/chat", "search"),
        ("inbound", "POST", "/api/v1/answers", "search"),
        ("inbound", "POST", "/proxy/esone/api/v1/chat", "search"),
        ("inbound", "POST", "/api/v1/chatbot", "chatbot"),
        ("inbound", "POST", "/proxy/esone/api/v1/chatbot", "chatbot"),
        ("inbound", "GET", "/api/v1/chat/history", "account"),
        ("inbound", "GET", "/api/v1/chat/stats", "account"),
        ("inbound", "GET", "/api/v1/users/me", "account"),
        ("inbound", "POST", "/api/v1/auth/login", "auth"),
        ("inbound", "POST", "/api/v1/auth/refresh", "auth"),
        ("inbound", "HEAD", "/", "health"),
        ("inbound", "GET", "/api/v1/health", "health"),
        ("inbound", "GET", "/api/v1/admin/users", "other"),
        ("outbound", "POST", "generativelanguage.googleapis.com/v1beta/openai/chat/completions", "ai_provider"),
        ("outbound", "POST", "api-latency-reducer-1.onrender.com/api/v1/answers", "gateway_calls"),
        ("outbound", "POST", "localhost:8001/api/v1/auth/login", "gateway_calls"),
        ("outbound", "GET", "example.com/feed", "outbound_other"),
    ],
)
def test_classify(direction, method, endpoint, expected):
    assert classify(direction, method, endpoint) == expected


def _row(endpoint, method="POST", direction="inbound", status=200, ms=100.0):
    row = {"service": "esone", "method": method, "endpoint": endpoint, "status_code": status,
           "response_time_ms": ms, "client_ip": "10.0.0.5", "direction": direction}
    if direction == "outbound":
        row["upstream_host"] = endpoint.split("/", 1)[0]
    return row


async def test_breakdown_separates_real_queries_and_adds_search_cost(client, admin_headers, operator_headers, monkeypatch):
    monkeypatch.setattr("app.api.v1.answers.get_answer_service", _service)
    # A person of our own: request logs persist across tests, so scope every row to them.
    ref = f"esone:qb{uuid.uuid4().hex[:8]}"
    batch = [
        _row("/api/v1/chat", ms=900.0),
        _row("/api/v1/chat", ms=100.0),
        _row("/api/v1/chatbot", ms=300.0),
        _row("/api/v1/chat/history", method="GET"),
        _row("/api/v1/auth/login"),
        _row("/api/v1/auth/login", status=401),
        _row("/", method="HEAD"),
        _row("generativelanguage.googleapis.com/v1beta/openai/chat/completions", direction="outbound"),
        _row("optimizer.test/api/v1/answers", direction="outbound"),
    ]
    batch = [row | {"end_user": ref} for row in batch]
    assert (await client.post("/api/v1/ingest/requests", json={"records": batch}, headers=operator_headers)).status_code == 202
    # The service account asks one question through the answers pipeline (as Esone does).
    await client.post("/api/v1/answers", json={"question": "What is the Python programming language?",
                                                "user_ref": ref}, headers=operator_headers)
    await asyncio.sleep(0.4)
    await reset_rate_limits()

    res = await client.get("/api/v1/analytics/queries", params={"as_user": ref}, headers=admin_headers)
    assert res.status_code == 200, res.text
    data = res.json()
    by_key = {c["key"]: c for c in data["categories"]}
    assert by_key["search"]["requests"] == 2 and by_key["search"]["avg_response_time_ms"] == 500.0
    assert by_key["chatbot"]["requests"] == 1
    assert by_key["auth"]["requests"] == 2 and by_key["auth"]["errors"] == 1
    assert by_key["account"]["requests"] == 1 and by_key["health"]["requests"] == 1
    assert by_key["ai_provider"]["requests"] == 1 and by_key["gateway_calls"]["requests"] == 1
    assert data["real_queries"] == 3 and data["supporting_requests"] == 4 and data["outbound_calls"] == 2
    assert data["total_requests"] == 9
    assert [c["group"] for c in data["categories"][:2]] == ["query", "query"]

    searches = data["searches"]
    assert searches["questions"] == 1 and searches["fresh_answers"] == 1 and searches["cache_hits"] == 0
    assert searches["billable_tokens"] == 30 and searches["cost_inr"] == 150.0 and searches["rate_per_token_inr"] == 5.0


async def test_breakdown_respects_view_as_and_roles(client, admin_headers, viewer_headers, operator_headers):
    batch = [_row("/api/v1/chat") | {"end_user": "esone:61"}, _row("/api/v1/chat") | {"end_user": "esone:62"}]
    await client.post("/api/v1/ingest/requests", json={"records": batch}, headers=operator_headers)
    await reset_rate_limits()
    one = (await client.get("/api/v1/analytics/queries", params={"as_user": "esone:61"}, headers=admin_headers)).json()
    assert one["real_queries"] == 1
    forbidden = await client.get("/api/v1/analytics/queries", params={"as_user": "esone:61"}, headers=viewer_headers)
    assert forbidden.status_code == 403
