"""Admin "view as user": every dashboard read scoped to one user, refused for everyone else."""
import asyncio

import httpx

from app.ai.answers.crawler import Crawler
from app.ai.answers.semantic_cache import SemanticCache
from app.services.answers import AnswerService
from tests.ai_fakes import FakeEmbeddingClient
from tests.test_answers import FakeKnowledge, FakeWikipedia, reset_rate_limits

SCOPED_READS = [
    "/api/v1/analytics/summary",
    "/api/v1/analytics/endpoints",
    "/api/v1/analytics/slow-endpoints",
    "/api/v1/analytics/benchmark",
    "/api/v1/analytics/suggestions",
    "/api/v1/rate-limits/me",
    "/api/v1/rate-limits/events",
    "/api/v1/ai-usage/summary",
    "/api/v1/ai-usage/requests",
    "/api/v1/guardrails/summary",
    "/api/v1/guardrails/events",
    "/api/v1/answers/recent",
    "/api/v1/answers/stats",
    "/api/v1/answers/top",
    "/api/v1/answers/cache",
    "/api/v1/answers/costs",
    "/api/v1/answers/users",
    "/api/v1/pricing/users",
]


async def _read(client, path, params, headers):
    """One read with a fresh bucket: the test rate limit is a few requests."""
    await reset_rate_limits()
    return (await client.get(path, params=params, headers=headers)).json()


def _service():
    wiki = FakeWikipedia()
    return AnswerService(
        cache=SemanticCache(threshold=0.5),
        crawler=Crawler(transport=httpx.MockTransport(wiki.handler), max_results=2),
        embedding_factory=FakeEmbeddingClient,
        knowledge_fn=FakeKnowledge("Python is a programming language."),
        model_first=True,
    )


async def test_only_admins_may_view_as_another_user(client, viewer_headers, operator_headers):
    for path in SCOPED_READS:
        for headers in (viewer_headers, operator_headers):
            await reset_rate_limits()
            res = await client.get(path, params={"as_user": "account:1"}, headers=headers)
            assert res.status_code == 403, (path, res.status_code, res.text[:120])


async def test_every_read_accepts_as_user_for_admins(client, admin_headers):
    for path in SCOPED_READS:
        await reset_rate_limits()
        res = await client.get(path, params={"as_user": "account:3"}, headers=admin_headers)
        assert res.status_code == 200, (path, res.text[:200])


async def test_account_view_shows_only_that_users_rows(client, admin_headers, viewer_headers, operator_headers, monkeypatch):
    monkeypatch.setattr("app.api.v1.answers.get_answer_service", _service)
    for _ in range(3):
        await client.get("/api/v1/rate-limits/config", headers=viewer_headers)
    await client.get("/api/v1/rate-limits/config", headers=operator_headers)
    await client.post("/api/v1/answers", json={"question": "What is the Python programming language?"}, headers=viewer_headers)
    await asyncio.sleep(0.4)  # request logs and answer rows are written in background tasks
    await reset_rate_limits()

    as_viewer = {"as_user": "account:3"}
    summary = await _read(client, "/api/v1/analytics/summary", as_viewer, admin_headers)
    logs = await _read(client, "/api/v1/analytics/endpoints", {**as_viewer, "limit": 100}, admin_headers)
    assert logs and {row["user_id"] for row in logs} == {3}
    assert summary["total_requests"] >= 4  # api_logs persist across tests; every row counted is still user 3

    # as_user wins over service: still the viewer's own gateway rows, not a service's.
    with_service = await _read(client, "/api/v1/analytics/summary", {**as_viewer, "service": "esone"}, admin_headers)
    assert with_service["total_requests"] == summary["total_requests"]

    me = await _read(client, "/api/v1/rate-limits/me", as_viewer, admin_headers)
    assert me["identifier"] == "user:3" and me["tier"] == "user"
    events = await _read(client, "/api/v1/rate-limits/events", as_viewer, admin_headers)
    assert events["scope"] == "user"

    stats = await _read(client, "/api/v1/answers/stats", as_viewer, admin_headers)
    assert stats["scope"] == "user" and stats["questions"] == 1
    recent = await _read(client, "/api/v1/answers/recent", {**as_viewer, "hours": 24}, admin_headers)
    assert [item["user_id"] for item in recent["items"]] == [3]
    billing = await _read(client, "/api/v1/pricing/users", as_viewer, admin_headers)
    assert {item["user_id"] for item in billing["items"]} == {3} and billing["total_billable_tokens"] == 30

    # The operator is invisible in the viewer's scope.
    as_operator = await _read(client, "/api/v1/answers/stats", {"as_user": "account:2"}, admin_headers)
    assert as_operator["questions"] == 0
    for path in ("/api/v1/ai-usage/summary", "/api/v1/guardrails/summary"):
        assert (await _read(client, path, as_viewer, admin_headers))["scope"] == "user"


async def test_end_user_view_has_searches_but_never_everyones_traffic(client, admin_headers, operator_headers, monkeypatch):
    monkeypatch.setattr("app.api.v1.answers.get_answer_service", _service)
    await client.post(
        "/api/v1/answers",
        json={"question": "What is the Python programming language?", "user_ref": "esone:7", "user_name": "priya"},
        headers=operator_headers,
    )
    await client.get("/api/v1/rate-limits/config", headers=operator_headers)
    await asyncio.sleep(0.4)
    await reset_rate_limits()

    as_priya = {"as_user": "esone:7"}
    stats = await _read(client, "/api/v1/answers/stats", as_priya, admin_headers)
    assert stats["questions"] == 1 and stats["end_user"] == "esone:7"
    costs = await _read(client, "/api/v1/answers/costs", as_priya, admin_headers)
    assert costs["llm_calls_made"] == 1
    billing = await _read(client, "/api/v1/pricing/users", as_priya, admin_headers)
    assert billing["scope"] == "user" and [item["end_user"] for item in billing["items"]] == ["esone:7"]

    # Per-person HTTP traffic does not exist for an end user: empty, not everyone's.
    summary = await _read(client, "/api/v1/analytics/summary", as_priya, admin_headers)
    assert summary["total_requests"] == 0
    ai = await _read(client, "/api/v1/ai-usage/summary", as_priya, admin_headers)
    assert ai["requests"] == 0


def _row(end_user, endpoint, status=200):
    return {
        "service": "esone",
        "method": "POST",
        "endpoint": endpoint,
        "status_code": status,
        "response_time_ms": 120.0,
        "client_ip": "10.0.0.9",
        "end_user": end_user,
    }


async def test_tagged_rows_give_an_end_user_their_own_api_activity(client, admin_headers, operator_headers):
    batch = [
        _row("esone:41", "/api/v1/chat"),
        _row("esone:41", "/api/v1/chat", status=429),
        _row("esone:42", "/api/v1/chat"),
        _row(None, "/api/v1/health"),
    ]
    res = await client.post("/api/v1/ingest/requests", json={"records": batch}, headers=operator_headers)
    assert res.status_code == 202, res.text

    as_41 = {"as_user": "esone:41"}
    summary = await _read(client, "/api/v1/analytics/summary", as_41, admin_headers)
    assert summary["total_requests"] == 2 and summary["rate_limited_requests"] == 1
    logs = await _read(client, "/api/v1/analytics/endpoints", as_41, admin_headers)
    assert len(logs) == 2 and {row["end_user"] for row in logs} == {"esone:41"}
    events = await _read(client, "/api/v1/rate-limits/events", as_41, admin_headers)
    assert events["total_requests"] == 2 and events["rate_limited_requests"] == 1

    detail = await _read(client, "/api/v1/users/detail", {"key": "esone:41"}, admin_headers)
    assert detail["traffic"]["total_requests"] == 2
    listing = await _read(client, "/api/v1/users", {"kind": "end_user"}, admin_headers)
    counts = {item["key"]: item["api_requests"] for item in listing["items"]}
    assert counts["esone:41"] == 2 and counts["esone:42"] == 1

    # A malformed reference is rejected rather than stored.
    bad = await client.post(
        "/api/v1/ingest/requests", json={"records": [_row("<script>", "/x")]}, headers=operator_headers
    )
    assert bad.status_code == 422
