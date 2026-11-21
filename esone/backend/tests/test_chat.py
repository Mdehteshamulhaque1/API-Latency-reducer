"""The chat proxy signs in to the Optimizer once, forwards questions, and maps errors."""
import json

import httpx
import pytest

from esone_api import optimizer
from esone_api.config import get_settings
from tests.conftest import bearer, login, register

OPTIMIZER_ANSWER = {
    "question": "What is Python?",
    "answer": "Python is a high-level programming language. [1]",
    "answered_by": "crawler",
    "cached": False,
    "similarity": None,
    "matched_question": None,
    "match_method": None,
    "sources": [{"title": "Python (programming language)", "url": "https://en.wikipedia.org/wiki/Python"}],
    "latency_ms": 812.4,
    "crawl_ms": 640.0,
    "compose_method": "llm",
    "embedding_used": True,
}


class FakeOptimizer:
    """Plays the API Optimizer over httpx.MockTransport and records what it saw."""

    def __init__(self):
        self.logins = 0
        self.asks: list[dict] = []
        self.status = 200
        self.body: dict = OPTIMIZER_ANSWER
        self.reject_token = False

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/login":
            self.logins += 1
            body = json.loads(request.content)
            if body != {"username": "esone-bot", "password": "bot-pass-123"}:
                return httpx.Response(401, json={"detail": "Invalid credentials"})
            return httpx.Response(
                200, json={"access_token": f"tok-{self.logins}", "refresh_token": "r", "expires_in": 900}
            )
        if request.url.path == "/api/v1/answers":
            if self.reject_token and request.headers.get("authorization") == "Bearer tok-1":
                return httpx.Response(401, json={"detail": "Token expired"})
            self.asks.append(json.loads(request.content))
            return httpx.Response(self.status, json=self.body)
        return httpx.Response(404, json={"detail": "not found"})


@pytest.fixture
async def chat_client(client, monkeypatch):
    fake = FakeOptimizer()
    monkeypatch.setenv("ESONE_OPTIMIZER_URL", "http://optimizer.test")
    monkeypatch.setenv("ESONE_OPTIMIZER_USERNAME", "esone-bot")
    monkeypatch.setenv("ESONE_OPTIMIZER_PASSWORD", "bot-pass-123")
    get_settings.cache_clear()
    await optimizer.reset_optimizer()
    optimizer._transport_factory = lambda: httpx.MockTransport(fake.handler)
    yield client, fake
    optimizer._transport_factory = None
    await optimizer.reset_optimizer()


async def signed_in(client):
    await register(client)
    return bearer(await login(client))


async def test_chat_requires_login(chat_client):
    client, _ = chat_client
    assert (await client.post("/api/v1/chat", json={"question": "What is Python?"})).status_code == 401


async def test_chat_forwards_question_and_returns_answer_metadata(chat_client):
    client, fake = chat_client
    headers = await signed_in(client)
    res = await client.post("/api/v1/chat", json={"question": "What is Python?"}, headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["answer"].startswith("Python is")
    assert body["answered_by"] == "crawler" and body["cached"] is False
    assert body["sources"][0]["title"] == "Python (programming language)"
    assert body["compose_method"] == "llm"
    # The end-user reference lets the Optimizer keep a record per Esone user.
    assert fake.asks == [{"question": "What is Python?", "user_ref": "esone:2", "user_name": "alice",
                          "user_email": "alice@example.com"}]
    assert fake.logins == 1

    fake.body = {**OPTIMIZER_ANSWER, "answered_by": "cache", "cached": True, "similarity": 0.97, "match_method": "embedding"}
    again = await client.post("/api/v1/chat", json={"question": "What is Python?"}, headers=headers)
    assert again.json()["cached"] is True and again.json()["similarity"] == 0.97
    assert fake.logins == 1  # service token reused


async def test_chat_signs_in_again_when_service_token_is_rejected(chat_client):
    client, fake = chat_client
    headers = await signed_in(client)
    fake.reject_token = True
    res = await client.post("/api/v1/chat", json={"question": "What is Python?"}, headers=headers)
    assert res.status_code == 200
    assert fake.logins == 2


async def test_chat_maps_gateway_errors(chat_client):
    client, fake = chat_client
    headers = await signed_in(client)
    body = {"question": "What is Python?"}

    fake.status, fake.body = 400, {"detail": "Request blocked by guardrails"}
    res = await client.post("/api/v1/chat", json=body, headers=headers)
    assert res.status_code == 400 and res.json()["detail"] == "Request blocked by guardrails"

    fake.status, fake.body = 429, {"detail": "slow down"}
    assert (await client.post("/api/v1/chat", json=body, headers=headers)).status_code == 429

    fake.status, fake.body = 502, {"detail": "The crawler timed out"}
    res = await client.post("/api/v1/chat", json=body, headers=headers)
    assert res.status_code == 502 and "crawler" in res.json()["detail"]


async def test_chat_status_and_unconfigured_server(client, monkeypatch):
    # A developer's local .env may configure the Optimizer; this test needs it absent.
    monkeypatch.setenv("ESONE_OPTIMIZER_URL", "")
    get_settings.cache_clear()
    await optimizer.reset_optimizer()
    headers = await signed_in(client)
    assert (await client.get("/api/v1/chat/status", headers=headers)).json() == {"configured": False}
    res = await client.post("/api/v1/chat", json={"question": "What is Python?"}, headers=headers)
    assert res.status_code == 503


async def test_chat_validates_input(chat_client):
    client, _ = chat_client
    headers = await signed_in(client)
    assert (await client.post("/api/v1/chat", json={"question": "hi"}, headers=headers)).status_code == 422
    assert (await client.post("/api/v1/chat", json={}, headers=headers)).status_code == 422


async def test_chat_history_is_saved_per_user_and_can_be_cleared(chat_client):
    client, fake = chat_client
    headers = await signed_in(client)
    assert (await client.get("/api/v1/chat/history", headers=headers)).json() == {"items": [], "total": 0}

    await client.post("/api/v1/chat", json={"question": "What is Python?"}, headers=headers)
    fake.body = {**OPTIMIZER_ANSWER, "question": "Who made Python?", "answer": "Guido van Rossum. [1]",
                 "answered_by": "cache", "cached": True, "similarity": 0.93, "match_method": "embedding",
                 "sources": [{"title": "Guido", "url": "https://en.wikipedia.org/wiki/Guido", "source": "wikipedia"}]}
    await client.post("/api/v1/chat", json={"question": "Who made Python?"}, headers=headers)

    res = await client.get("/api/v1/chat/history", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["total"] == 2
    assert [item["question"] for item in body["items"]] == ["What is Python?", "Who made Python?"]  # oldest first
    first, second = body["items"]
    assert first["answer"].startswith("Python is") and first["cached"] is False and first["answered_by"] == "crawler"
    assert first["sources"][0]["title"] == "Python (programming language)" and first["sources"][0]["source"] is None
    assert second["cached"] is True and second["match_method"] == "embedding" and second["similarity"] == 0.93
    assert second["sources"][0]["source"] == "wikipedia"
    assert second["latency_ms"] == 812.4 and second["created_at"]

    # Another user has their own, empty, history.
    await register(client, username="bob", email="bob@example.com", password="bob-pass-1234")
    bob = bearer(await login(client, username="bob", password="bob-pass-1234"))
    assert (await client.get("/api/v1/chat/history", headers=bob)).json()["total"] == 0

    # Clearing forgets only the caller's rows.
    cleared = await client.delete("/api/v1/chat/history", headers=headers)
    assert cleared.status_code == 200 and cleared.json() == {"deleted": 2}
    assert (await client.get("/api/v1/chat/history", headers=headers)).json()["total"] == 0


async def test_chat_history_limit_and_auth(chat_client):
    client, fake = chat_client
    assert (await client.get("/api/v1/chat/history")).status_code == 401
    assert (await client.delete("/api/v1/chat/history")).status_code == 401
    headers = await signed_in(client)
    for i in range(3):
        # The stored question is the Optimizer's normalised (PII-masked) version, so the fake echoes it.
        fake.body = {**OPTIMIZER_ANSWER, "question": f"Question number {i}?"}
        await client.post("/api/v1/chat", json={"question": f"Question number {i}?"}, headers=headers)
    res = await client.get("/api/v1/chat/history", params={"limit": 2}, headers=headers)
    assert res.json()["total"] == 3
    assert [item["question"] for item in res.json()["items"]] == ["Question number 1?", "Question number 2?"]
    assert (await client.get("/api/v1/chat/history", params={"limit": 0}, headers=headers)).status_code == 422


async def test_my_activity_stats_are_per_user_and_include_errors(chat_client):
    client, fake = chat_client
    headers = await signed_in(client)
    assert (await client.get("/api/v1/chat/stats", headers=headers)).json()["total_queries"] == 0

    fake.body = {**OPTIMIZER_ANSWER, "question": "What is Python?", "total_tokens": 90, "estimated_cost_usd": 0.0002,
                 "served_model": "fake-model", "llm_ms": 300.0,
                 "sources": [{"title": "Py", "url": "https://en.wikipedia.org/wiki/Py", "source": "wikipedia"},
                             {"title": "DDG", "url": "https://duckduckgo.com/Py", "source": "duckduckgo"}]}
    await client.post("/api/v1/chat", json={"question": "What is Python?"}, headers=headers)
    fake.body = {**OPTIMIZER_ANSWER, "question": "what is python", "answered_by": "cache", "cached": True,
                 "match_method": "exact", "similarity": 1.0, "latency_ms": 40.0}
    await client.post("/api/v1/chat", json={"question": "what is python"}, headers=headers)
    fake.body = {**OPTIMIZER_ANSWER, "question": "tell me about python", "answered_by": "cache", "cached": True,
                 "match_method": "embedding", "similarity": 0.93, "latency_ms": 60.0}
    await client.post("/api/v1/chat", json={"question": "tell me about python"}, headers=headers)
    fake.status, fake.body = 502, {"detail": "The crawler timed out"}
    assert (await client.post("/api/v1/chat", json={"question": "Will this fail?"}, headers=headers)).status_code == 502
    fake.status, fake.body = 200, OPTIMIZER_ANSWER

    res = await client.get("/api/v1/chat/stats", headers=headers)
    assert res.status_code == 200, res.text
    st = res.json()
    assert st["total_queries"] == 4 and st["answered"] == 3 and st["errors"] == 1
    assert st["cache_hits"] == 2 and st["exact_hits"] == 1 and st["semantic_hits"] == 1 and st["misses"] == 1
    assert st["cache_hit_rate"] == round(2 / 3 * 100, 2)
    assert st["total_tokens"] == 90 and st["estimated_cost_usd"] == 0.0002
    assert st["by_model"] == [{"name": "fake-model", "count": 1}]
    assert {s["name"] for s in st["by_source"]} == {"wikipedia", "duckduckgo"} and st["sources_used"] == 2
    assert st["by_error"] == [{"name": "The crawler timed out", "count": 1}]
    assert st["p50_latency_ms"] <= st["p95_latency_ms"] <= st["p99_latency_ms"]
    assert len(st["latency_series"]) == 3 and [p["cached"] for p in st["latency_series"]] == [False, True, True]
    assert st["recent"][0]["status"] == "error" and st["recent"][0]["error_message"] == "The crawler timed out"
    assert st["recent"][1]["cache_type"] == "semantic" and st["recent"][2]["cache_type"] == "exact"
    assert st["recent_errors"][0]["question"] == "Will this fail?"

    # History shows only answered questions; the failed one is not a conversation turn.
    hist = (await client.get("/api/v1/chat/history", headers=headers)).json()
    assert hist["total"] == 3 and [i["question"] for i in hist["items"]] == ["What is Python?", "what is python", "tell me about python"]

    # Another user sees nothing of this.
    await register(client, username="carol", email="carol@example.com", password="carol-pass-1234")
    carol = bearer(await login(client, username="carol", password="carol-pass-1234"))
    assert (await client.get("/api/v1/chat/stats", headers=carol)).json()["total_queries"] == 0
    assert (await client.get("/api/v1/chat/stats")).status_code == 401



async def test_charges_are_stored_per_user(chat_client):
    client, fake = chat_client
    headers = await signed_in(client)
    fake.body = {**OPTIMIZER_ANSWER, "billable_tokens": 40, "cost_inr": 200.0}
    await client.post("/api/v1/chat", json={"question": "What is Python?"}, headers=headers)
    fake.body = {**OPTIMIZER_ANSWER, "question": "what is python", "answered_by": "cache", "cached": True,
                 "cache_status": "exact_hit", "billable_tokens": 0, "cost_inr": 0.0}
    await client.post("/api/v1/chat", json={"question": "what is python"}, headers=headers)
    st = (await client.get("/api/v1/chat/stats", headers=headers)).json()
    assert st["billable_tokens"] == 40 and st["cost_inr"] == 200.0
    hist = (await client.get("/api/v1/chat/history", headers=headers)).json()["items"]
    assert [i["cost_inr"] for i in hist] == [200.0, 0.0]

    await register(client, username="dave", email="dave@example.com", password="dave-pass-1234")
    dave = bearer(await login(client, username="dave", password="dave-pass-1234"))
    assert (await client.get("/api/v1/chat/stats", headers=dave)).json()["cost_inr"] == 0.0
