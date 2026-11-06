"""
Unit tests for the OpenAI chat service and route registration.
"""
import json
import logging
from types import SimpleNamespace

import httpx
import pytest

from app.core.exceptions import ExternalServiceError
from app.schemas.chat import ChatRequest
from app.services.chat import ChatService


class NoopCache:
    """Cache stub that always misses and accepts writes without storing."""

    async def get(self, key):
        return None

    async def set(self, key, value, ttl=None):
        return True


def _settings(**overrides):
    values = {
        "openai_api_key": "test-key",
        "openai_base_url": "https://api.openai.com/v1",
        "openai_model": "gpt-4o-mini",
        "openai_timeout_seconds": 10.0,
        "openai_max_retries": 2,
        "redis_cache_ttl": 3600,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _request(temperature=0.0):
    return ChatRequest(
        messages=[{"role": "user", "content": "hello"}],
        temperature=temperature,
        max_tokens=16,
    )


def _completion(content="hi"):
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 123,
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 11, "completion_tokens": 4, "total_tokens": 15},
    }


async def test_chat_completion_success():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-key"
        assert str(request.url) == "https://api.openai.com/v1/chat/completions"
        payload = json.loads(request.content)
        assert payload == {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "hello"}],
            "temperature": 0.0,
            "max_tokens": 16,
        }
        return httpx.Response(200, json=_completion())

    service = ChatService(
        settings_obj=_settings(),
        transport=httpx.MockTransport(handler),
        cache=NoopCache(),
    )
    result = await service.create_chat_completion(_request(), user_id=7, correlation_id="corr-1")

    assert result.id == "chatcmpl-1"
    assert result.model == "gpt-4o-mini"
    assert result.content == "hi"
    assert result.finish_reason == "stop"
    assert result.usage.prompt_tokens == 11
    assert result.usage.completion_tokens == 4
    assert result.usage.total_tokens == 15
    assert result.latency_ms >= 0
    assert result.cached is False
    assert result.created == 123


async def test_chat_completion_retries_timeout(monkeypatch):
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(200, json=_completion(content="recovered"))

    monkeypatch.setattr(ChatService, "_retry_delay", lambda self, attempt, response=None: 0.0)
    service = ChatService(
        settings_obj=_settings(),
        transport=httpx.MockTransport(handler),
        cache=NoopCache(),
    )

    result = await service.create_chat_completion(_request())

    assert calls == 3
    assert result.content == "recovered"


async def test_chat_completion_retries_429(monkeypatch):
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json=_completion())

    monkeypatch.setattr(ChatService, "_retry_delay", lambda self, attempt, response=None: 0.0)
    service = ChatService(
        settings_obj=_settings(),
        transport=httpx.MockTransport(handler),
        cache=NoopCache(),
    )

    result = await service.create_chat_completion(_request())

    assert calls == 2
    assert result.content == "hi"


async def test_chat_completion_exhausts_retries(monkeypatch):
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500)

    monkeypatch.setattr(ChatService, "_retry_delay", lambda self, attempt, response=None: 0.0)
    service = ChatService(
        settings_obj=_settings(),
        transport=httpx.MockTransport(handler),
        cache=NoopCache(),
    )

    with pytest.raises(ExternalServiceError) as exc_info:
        await service.create_chat_completion(_request())

    assert calls == 3
    assert exc_info.value.status_code == 503
    assert exc_info.value.details["status_code"] == 500
    assert exc_info.value.details["attempts"] == 3


async def test_chat_completion_does_not_retry_4xx(monkeypatch):
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400)

    monkeypatch.setattr(ChatService, "_retry_delay", lambda self, attempt, response=None: 0.0)
    service = ChatService(
        settings_obj=_settings(),
        transport=httpx.MockTransport(handler),
        cache=NoopCache(),
    )

    with pytest.raises(ExternalServiceError) as exc_info:
        await service.create_chat_completion(_request())

    assert calls == 1
    assert exc_info.value.details["status_code"] == 400


async def test_chat_completion_requires_api_key():
    async def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("OpenAI must not be called without an API key")

    service = ChatService(
        settings_obj=_settings(openai_api_key=None),
        transport=httpx.MockTransport(handler),
        cache=NoopCache(),
    )

    with pytest.raises(ExternalServiceError) as exc_info:
        await service.create_chat_completion(_request())

    assert exc_info.value.status_code == 503
    assert exc_info.value.details["reason"] == "missing_api_key"


async def test_chat_completion_rejects_malformed_response():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    service = ChatService(
        settings_obj=_settings(),
        transport=httpx.MockTransport(handler),
        cache=NoopCache(),
    )

    with pytest.raises(ExternalServiceError) as exc_info:
        await service.create_chat_completion(_request())

    assert exc_info.value.details["reason"] == "missing_choices"


async def test_chat_completion_logs_usage_and_latency(caplog):
    caplog.set_level(logging.INFO, logger="app.services.chat")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_completion())

    service = ChatService(
        settings_obj=_settings(),
        transport=httpx.MockTransport(handler),
        cache=NoopCache(),
    )

    await service.create_chat_completion(_request(), user_id=7, correlation_id="corr-1")

    record = next(
        item for item in caplog.records if item.message == "OpenAI chat completion succeeded"
    )
    assert record.prompt_tokens == 11
    assert record.completion_tokens == 4
    assert record.total_tokens == 15
    assert record.latency_ms >= 0
    assert record.user_id == 7
    assert record.correlation_id == "corr-1"
    assert "hello" not in caplog.text


def test_chat_routes_are_registered():
    from app.main import app

    schema = app.openapi()
    assert "/api/v1/chat" in schema["paths"]
    assert "post" in schema["paths"]["/api/v1/chat"]

    def collect_paths(routes, prefix=""):
        paths = set()
        for route in routes:
            path = getattr(route, "path", None)
            if path:
                paths.add(prefix + path)
            context = getattr(route, "include_context", None)
            original = getattr(route, "original_router", None)
            if context is not None and original is not None:
                nested_prefix = prefix + getattr(context, "prefix", "")
                paths.update(collect_paths(original.routes, nested_prefix))
        return paths

    assert "/v1/chat" in collect_paths(app.routes)
