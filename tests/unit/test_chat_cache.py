"""
Unit tests for exact-match Redis caching in the chat service.
"""
import httpx
import pytest
from redis.exceptions import RedisError

from app.core.exceptions import ExternalServiceError
from app.schemas.chat import ChatRequest
from app.services.cache import CacheService
from app.services.chat import ChatService


class FakeRedis:
    """Minimal async Redis stand-in with failure injection."""

    def __init__(self):
        self.data = {}
        self.ttls = {}
        self.get_calls = 0
        self.set_calls = 0
        self.fail_get = False
        self.fail_set = False

    async def get(self, key):
        self.get_calls += 1
        if self.fail_get:
            raise RedisError("get failed")
        return self.data.get(key)

    async def set(self, key, value, ttl=None):
        self.set_calls += 1
        if self.fail_set:
            raise RedisError("set failed")
        self.data[key] = value
        self.ttls[key] = ttl
        return True

    async def increment(self, key, amount=1):
        return amount


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
    return type("Settings", (), values)()


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


def _service(fake_redis, handler, **settings_overrides):
    return ChatService(
        settings_obj=_settings(**settings_overrides),
        transport=httpx.MockTransport(handler),
        cache=CacheService(fake_redis),
    )


async def test_cache_miss_then_hit_avoids_openai():
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=_completion("cached answer"))

    fake_redis = FakeRedis()
    service = _service(fake_redis, handler)

    first = await service.create_chat_completion(_request())
    second = await service.create_chat_completion(_request())

    assert calls == 1
    assert first.cached is False
    assert second.cached is True
    assert second.content == "cached answer"
    assert second.usage.total_tokens == 15
    assert second.latency_ms >= 0
    assert fake_redis.get_calls == 2
    assert fake_redis.set_calls == 1
    assert len(fake_redis.data) == 1
    assert next(iter(fake_redis.data)).startswith("chat:")


@pytest.mark.parametrize(
    "configured_ttl,expected_ttl",
    [(None, 3600), (120, 120)],
)
async def test_cache_ttl_is_configurable(configured_ttl, expected_ttl):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_completion())

    fake_redis = FakeRedis()
    overrides = {} if configured_ttl is None else {"redis_cache_ttl": configured_ttl}
    service = _service(fake_redis, handler, **overrides)

    await service.create_chat_completion(_request())

    key = next(iter(fake_redis.ttls))
    assert fake_redis.ttls[key] == expected_ttl


async def test_temperature_above_zero_bypasses_cache():
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=_completion())

    fake_redis = FakeRedis()
    service = _service(fake_redis, handler)

    first = await service.create_chat_completion(_request(temperature=0.7))
    second = await service.create_chat_completion(_request(temperature=0.7))

    assert calls == 2
    assert fake_redis.get_calls == 0
    assert fake_redis.set_calls == 0
    assert fake_redis.data == {}
    assert first.cached is False
    assert second.cached is False


@pytest.mark.parametrize(
    "fail_get,fail_set",
    [(True, False), (False, True), (True, True)],
)
async def test_redis_failures_fall_back_to_openai(fail_get, fail_set):
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=_completion("from provider"))

    fake_redis = FakeRedis()
    fake_redis.fail_get = fail_get
    fake_redis.fail_set = fail_set
    service = _service(fake_redis, handler)

    result = await service.create_chat_completion(_request())

    assert calls == 1
    assert result.cached is False
    assert result.content == "from provider"


def test_cache_key_includes_model_messages_and_temperature():
    fake_redis = FakeRedis()
    service = _service(fake_redis, lambda request: httpx.Response(200, json=_completion()))
    messages = [{"role": "user", "content": "hello"}]

    key = service._build_cache_key("gpt-4o-mini", messages, 0.0)

    assert key.startswith("chat:")
    assert key == service._build_cache_key("gpt-4o-mini", messages, 0.0)
    assert key == service._build_cache_key(
        "gpt-4o-mini",
        [{"content": "hello", "role": "user"}],
        0.0,
    )
    assert key != service._build_cache_key("gpt-4o", messages, 0.0)
    assert key != service._build_cache_key(
        "gpt-4o-mini",
        [{"role": "user", "content": "goodbye"}],
        0.0,
    )
    assert key != service._build_cache_key("gpt-4o-mini", messages, 1.0)


async def test_invalid_cached_payload_falls_back_to_openai():
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=_completion("fresh"))

    fake_redis = FakeRedis()
    service = _service(fake_redis, handler)
    messages = [{"role": "user", "content": "hello"}]
    fake_redis.data[service._build_cache_key("gpt-4o-mini", messages, 0.0)] = {"bad": "data"}

    result = await service.create_chat_completion(_request())

    assert calls == 1
    assert result.cached is False
    assert result.content == "fresh"


async def test_error_response_is_not_cached():
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400)

    fake_redis = FakeRedis()
    service = _service(fake_redis, handler)

    with pytest.raises(ExternalServiceError):
        await service.create_chat_completion(_request())

    assert calls == 1
    assert fake_redis.set_calls == 0
    assert fake_redis.data == {}
