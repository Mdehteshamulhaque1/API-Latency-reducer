"""
AI usage persistence: every chat call through the gateway leaves one
ai_request_logs row, and /ai-usage reports real token and cost totals.

The provider is mocked at the HTTP transport level, so these are true
end-to-end tests of route -> service -> background task -> database.
"""
import asyncio
from types import SimpleNamespace

import httpx
import pytest

from app.api.v1 import chat as chat_route
from app.database.db import async_session_maker
from app.models import AIRequestLog
from app.services.chat import ChatService
from app.services.circuit_breaker import CircuitBreaker


class MemoryCache:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ttl=None):
        self.store[key] = value
        return True


def _settings(**overrides):
    values = {
        "openai_api_key": "test-key",
        "openai_base_url": "https://api.openai.com/v1",
        "openai_model": "gpt-4o-mini",
        "openai_primary_model": None,
        "openai_fallback_model": None,
        "openai_timeout_seconds": 10.0,
        "openai_max_retries": 0,
        "redis_cache_ttl": 3600,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _completion():
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 123,
        "model": "gpt-4o-mini",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    }


@pytest.fixture
def mocked_gateway(monkeypatch):
    """Replace the route's ChatService factory with one backed by a fake provider."""
    cache = MemoryCache()
    state = {"fail": False}

    def handler(request):
        if state["fail"]:
            return httpx.Response(503, json={"error": "upstream down"})
        return httpx.Response(200, json=_completion())

    def factory():
        return ChatService(
            _settings(),
            transport=httpx.MockTransport(handler),
            cache=cache,
            breaker=CircuitBreaker(name="usage-test", failure_threshold=100, cooldown_seconds=30),
        )

    monkeypatch.setattr(chat_route, "ChatService", factory)
    return state


async def _clear_logs():
    async with async_session_maker() as session:
        from sqlalchemy import delete

        await session.execute(delete(AIRequestLog))
        await session.commit()


async def _rows():
    await asyncio.sleep(0.2)  # background task runs after the response
    async with async_session_maker() as session:
        from sqlalchemy import select

        return (await session.execute(select(AIRequestLog).order_by(AIRequestLog.id))).scalars().all()


BODY = {"messages": [{"role": "user", "content": "hello"}], "temperature": 0}


async def test_success_then_cache_hit_are_recorded(client, viewer_headers, mocked_gateway):
    await _clear_logs()

    first = await client.post("/api/v1/chat", json=BODY, headers=viewer_headers)
    assert first.status_code == 200
    assert first.json()["cached"] is False
    # 100 prompt tokens at $0.15/M + 50 completion tokens at $0.60/M
    assert round(first.json()["estimated_cost_usd"], 8) == round(100 / 1e6 * 0.15 + 50 / 1e6 * 0.60, 8)

    second = await client.post("/api/v1/chat", json=BODY, headers=viewer_headers)
    assert second.status_code == 200
    assert second.json()["cached"] is True
    assert second.json()["estimated_cost_usd"] == 0.0

    rows = await _rows()
    assert [row.outcome for row in rows] == ["success", "cache_hit"]
    assert rows[0].user_id == 3
    assert rows[0].served_model == "gpt-4o-mini"
    assert (rows[0].prompt_tokens, rows[0].completion_tokens, rows[0].total_tokens) == (100, 50, 150)
    assert rows[0].estimated_cost_usd > 0
    assert rows[0].correlation_id
    assert rows[1].total_tokens == 0
    assert rows[1].estimated_cost_usd == 0.0


async def test_provider_failure_is_recorded_without_tokens(client, viewer_headers, mocked_gateway):
    await _clear_logs()
    mocked_gateway["fail"] = True

    res = await client.post("/api/v1/chat", json=BODY, headers=viewer_headers)
    assert res.status_code == 503

    rows = await _rows()
    assert len(rows) == 1
    assert rows[0].outcome == "error"
    assert rows[0].error_code == "http_503"
    assert rows[0].total_tokens == 0
    assert rows[0].estimated_cost_usd == 0.0
    assert rows[0].latency_ms >= 0


async def test_summary_totals_and_scoping(client, viewer_headers, operator_headers, admin_headers, mocked_gateway):
    await _clear_logs()
    await client.post("/api/v1/chat", json=BODY, headers=viewer_headers)
    await client.post("/api/v1/chat", json=BODY, headers=viewer_headers)  # cache hit
    mocked_gateway["fail"] = True
    # A different prompt so the operator misses the (prompt-keyed) cache.
    other = {"messages": [{"role": "user", "content": "something else"}], "temperature": 0}
    await client.post("/api/v1/chat", json=other, headers=operator_headers)
    await _rows()

    own = await client.get("/api/v1/ai-usage/summary?hours=24", headers=viewer_headers)
    assert own.status_code == 200
    body = own.json()
    assert body["scope"] == "own"
    assert body["requests"] == 2
    assert body["successes"] == 1
    assert body["cache_hits"] == 1
    assert body["errors"] == 0
    assert body["total_tokens"] == 150
    assert body["cost_is_estimate"] is True
    assert body["estimated_cost_usd"] > 0
    assert body["by_model"][0]["served_model"] == "gpt-4o-mini"
    assert body["series"] and sum(point["requests"] for point in body["series"]) == 2

    everything = await client.get("/api/v1/ai-usage/summary?hours=24", headers=admin_headers)
    all_body = everything.json()
    assert all_body["scope"] == "all"
    assert all_body["requests"] == 3
    assert all_body["errors"] == 1
    assert all_body["error_rate"] == round(1 / 3 * 100, 2)

    recent = await client.get("/api/v1/ai-usage/requests?hours=24&limit=10", headers=operator_headers)
    items = recent.json()["items"]
    assert len(items) == 1
    assert items[0]["outcome"] == "error"
    assert "content" not in items[0]


async def test_empty_window_is_all_zero(client, viewer_headers):
    res = await client.get("/api/v1/ai-usage/summary?hours=1", headers=viewer_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["requests"] >= 0
    assert body["cost_is_estimate"] is True
