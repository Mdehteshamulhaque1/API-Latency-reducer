"""
Prometheus metrics for the LLM gateway.

Counters only move when ChatService handles a real completion, so each test
drives the service with a mocked provider and then reads the registry.
"""
import json
from types import SimpleNamespace

import httpx
import pytest
from prometheus_client import REGISTRY

from app.core.exceptions import ExternalServiceError
from app.schemas.chat import ChatRequest
from app.services.chat import ChatService
from app.services.circuit_breaker import CircuitBreaker


class NoopCache:
    async def get(self, key):
        return None

    async def set(self, key, value, ttl=None):
        return True


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


def _request(temperature=0.0):
    return ChatRequest(messages=[{"role": "user", "content": "hello"}], temperature=temperature)


def _completion(model="gpt-4o-mini"):
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 123,
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 4, "total_tokens": 15},
    }


def _sample(name, **labels):
    value = REGISTRY.get_sample_value(name, labels)
    return value or 0.0


def _ok_transport(model="gpt-4o-mini"):
    return httpx.MockTransport(lambda request: httpx.Response(200, json=_completion(model)))


def _breaker():
    return CircuitBreaker(name="test", failure_threshold=3, cooldown_seconds=30)


async def test_success_increments_counters_tokens_and_cost():
    labels = {"served_model": "gpt-4o-mini", "cache_type": "miss", "status": "success"}
    before = _sample("chat_requests_total", **labels)
    prompt_before = _sample("chat_prompt_tokens_total", served_model="gpt-4o-mini")
    cost_before = _sample("chat_estimated_cost_usd_total", served_model="gpt-4o-mini")

    service = ChatService(_settings(), transport=_ok_transport(), cache=NoopCache(), breaker=_breaker())
    await service.create_chat_completion(_request())

    assert _sample("chat_requests_total", **labels) == before + 1
    assert _sample("chat_prompt_tokens_total", served_model="gpt-4o-mini") == prompt_before + 11
    assert _sample("chat_completion_tokens_total", served_model="gpt-4o-mini") >= 4
    # 11 prompt tokens at $0.15/M + 4 completion tokens at $0.60/M
    assert round(_sample("chat_estimated_cost_usd_total", served_model="gpt-4o-mini") - cost_before, 9) == round(
        11 / 1_000_000 * 0.15 + 4 / 1_000_000 * 0.60, 9
    )
    assert _sample("chat_provider_latency_seconds_count", served_model="gpt-4o-mini") >= 1
    assert _sample("chat_request_latency_seconds_count", served_model="gpt-4o-mini") >= 1


async def test_cache_hit_counts_as_hit_not_miss():
    hit = {"served_model": "gpt-4o-mini", "cache_type": "hit", "status": "success"}
    miss = {"served_model": "gpt-4o-mini", "cache_type": "miss", "status": "success"}
    hit_before = _sample("chat_requests_total", **hit)
    miss_before = _sample("chat_requests_total", **miss)

    service = ChatService(_settings(), transport=_ok_transport(), cache=MemoryCache(), breaker=_breaker())
    await service.create_chat_completion(_request())
    response = await service.create_chat_completion(_request())

    assert response.cached is True
    assert _sample("chat_requests_total", **miss) == miss_before + 1
    assert _sample("chat_requests_total", **hit) == hit_before + 1


async def test_failure_without_fallback_records_error():
    labels = {"served_model": "gpt-4o-mini", "cache_type": "miss", "status": "error"}
    before = _sample("chat_requests_total", **labels)
    fallback_errors_before = _sample("chat_fallback_total", status="error")

    transport = httpx.MockTransport(lambda request: httpx.Response(503, json={"error": "down"}))
    service = ChatService(_settings(), transport=transport, cache=NoopCache(), breaker=_breaker())
    with pytest.raises(ExternalServiceError):
        await service.create_chat_completion(_request())

    assert _sample("chat_requests_total", **labels) == before + 1
    assert _sample("chat_fallback_total", status="error") == fallback_errors_before


async def test_fallback_success_is_counted():
    before = _sample("chat_fallback_total", status="success")

    def handler(request):
        body = json.loads(request.content)
        if body["model"] == "gpt-4o-mini":
            return httpx.Response(503, json={"error": "primary down"})
        return httpx.Response(200, json=_completion("gpt-4o"))

    service = ChatService(
        _settings(openai_fallback_model="gpt-4o"),
        transport=httpx.MockTransport(handler),
        cache=NoopCache(),
        breaker=_breaker(),
    )
    response = await service.create_chat_completion(_request())
    assert response.fallback_used is True
    assert _sample("chat_fallback_total", status="success") == before + 1
    assert _sample("chat_requests_total", served_model="gpt-4o", cache_type="miss", status="success") >= 1


async def test_breaker_gauge_tracks_state():
    def handler(request):
        return httpx.Response(503, json={"error": "down"})

    breaker = CircuitBreaker(name="gauge", failure_threshold=2, cooldown_seconds=30)
    service = ChatService(
        _settings(openai_fallback_model="gpt-4o"),
        transport=httpx.MockTransport(handler),
        cache=NoopCache(),
        breaker=breaker,
    )
    for _ in range(2):
        with pytest.raises(ExternalServiceError):
            await service.create_chat_completion(_request())

    assert _sample("chat_circuit_breaker_state", model="gpt-4o-mini") == 1.0  # open


async def test_metrics_endpoint_exposes_gateway_series(client):
    service = ChatService(_settings(), transport=_ok_transport(), cache=NoopCache(), breaker=_breaker())
    await service.create_chat_completion(_request())

    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")
    body = resp.text
    assert 'chat_requests_total{cache_type="miss",served_model="gpt-4o-mini",status="success"}' in body
    assert "chat_provider_latency_seconds_bucket" in body
    assert "chat_estimated_cost_usd_total" in body
