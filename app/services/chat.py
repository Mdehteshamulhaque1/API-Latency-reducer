"""
OpenAI chat completion service with retries, exact-match caching, and usage tracking.
"""
import asyncio
import hashlib
import json
import logging
import time
from typing import Any

import httpx

from app.config import settings
from app.core.constants import CACHE_KEY_CHAT_PREFIX
from app.core.exceptions import ExternalServiceError
from app.schemas.chat import ChatRequest, ChatResponse, ChatUsage
from app.services.cache import CacheService
from app.utils.redis_client import redis_client

logger = logging.getLogger(__name__)

_MAX_RETRY_DELAY_SECONDS = 10.0


def _as_int(value: Any) -> int:
    """Return an integer value or zero when the provider omits it."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return 0


def _as_optional_int(value: Any) -> int | None:
    """Return an integer value or None when the provider omits it."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


class ChatService:
    """Call the OpenAI Chat Completions API with bounded retries and exact-match caching."""

    def __init__(
        self,
        settings_obj: Any | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        client: httpx.AsyncClient | None = None,
        cache: CacheService | None = None,
    ):
        self._settings = settings_obj or settings
        self._transport = transport
        self._client = client
        self._cache = cache or CacheService(redis_client)
        self._cache_ttl = getattr(self._settings, "redis_cache_ttl", 3600)

    async def create_chat_completion(
        self,
        request: ChatRequest,
        user_id: int | None = None,
        correlation_id: str | None = None,
    ) -> ChatResponse:
        """Create a chat completion, using exact-match cache when eligible."""
        if not self._settings.openai_api_key:
            raise ExternalServiceError(
                "OpenAI",
                "OpenAI API key is not configured",
                details={"reason": "missing_api_key"},
            )

        model = request.model or self._settings.openai_model
        messages = [message.model_dump() for message in request.messages]
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        cache_enabled = request.temperature <= 0
        cache_key = self._build_cache_key(model, messages, request.temperature)
        started_at = time.perf_counter()

        if cache_enabled:
            cached_response = await self._get_cached_response(
                cache_key,
                user_id,
                correlation_id,
            )
            if cached_response is not None:
                latency_ms = (time.perf_counter() - started_at) * 1000
                response = cached_response.model_copy(
                    update={"cached": True, "latency_ms": round(latency_ms, 3)}
                )
                logger.info(
                    "Chat completion cache hit",
                    extra={
                        "provider": "openai",
                        "model": response.model,
                        "cache_key": cache_key,
                        "latency_ms": round(response.latency_ms, 2),
                        "user_id": user_id,
                        "correlation_id": correlation_id,
                    },
                )
                return response

        url = f"{self._settings.openai_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        timeout = httpx.Timeout(self._settings.openai_timeout_seconds)

        if self._client is not None:
            data, attempts = await self._request_with_retries(
                self._client,
                url,
                headers,
                payload,
                model,
                user_id,
                correlation_id,
            )
        else:
            async with httpx.AsyncClient(timeout=timeout, transport=self._transport) as client:
                data, attempts = await self._request_with_retries(
                    client,
                    url,
                    headers,
                    payload,
                    model,
                    user_id,
                    correlation_id,
                )

        latency_ms = (time.perf_counter() - started_at) * 1000
        response = self._build_response(data, model, latency_ms)
        if cache_enabled:
            await self._store_cached_response(cache_key, response, user_id, correlation_id)

        logger.info(
            "OpenAI chat completion succeeded",
            extra={
                "provider": "openai",
                "model": response.model,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "latency_ms": round(response.latency_ms, 2),
                "attempts": attempts,
                "cached": False,
                "cache_key": cache_key if cache_enabled else None,
                "user_id": user_id,
                "correlation_id": correlation_id,
            },
        )
        return response

    def _build_cache_key(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float,
    ) -> str:
        """Build a stable exact-match cache key from model, messages, and temperature."""
        canonical = json.dumps(
            {"model": model, "messages": messages, "temperature": temperature},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"{CACHE_KEY_CHAT_PREFIX}{digest}"

    async def _get_cached_response(
        self,
        cache_key: str,
        user_id: int | None,
        correlation_id: str | None,
    ) -> ChatResponse | None:
        """Read a cached response, treating Redis or payload failures as misses."""
        try:
            cached_data = await self._cache.get(cache_key)
        except Exception as exc:
            logger.warning(
                "Chat cache read failed; bypassing cache",
                extra={
                    "cache_key": cache_key,
                    "reason": type(exc).__name__,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                },
            )
            return None

        if cached_data is None:
            return None

        try:
            return ChatResponse.model_validate(cached_data)
        except Exception as exc:
            logger.warning(
                "Ignoring invalid chat cache entry",
                extra={
                    "cache_key": cache_key,
                    "reason": type(exc).__name__,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                },
            )
            return None

    async def _store_cached_response(
        self,
        cache_key: str,
        response: ChatResponse,
        user_id: int | None,
        correlation_id: str | None,
    ) -> None:
        """Write a successful response to cache without failing the request."""
        try:
            stored = await self._cache.set(
                cache_key,
                response.model_dump(mode="json", exclude={"cached", "latency_ms"}),
                ttl=self._cache_ttl,
            )
        except Exception as exc:
            logger.warning(
                "Chat cache write failed; returning provider response",
                extra={
                    "cache_key": cache_key,
                    "reason": type(exc).__name__,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                },
            )
            return

        if not stored:
            logger.warning(
                "Chat cache write was not stored",
                extra={
                    "cache_key": cache_key,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                },
            )

    async def _request_with_retries(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        model: str,
        user_id: int | None,
        correlation_id: str | None,
    ) -> tuple[dict[str, Any], int]:
        """POST to OpenAI, retrying transient failures within the configured limit."""
        attempts_allowed = self._settings.openai_max_retries + 1

        for attempt in range(attempts_allowed):
            try:
                response = await client.post(url, headers=headers, json=payload)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                reason = type(exc).__name__
                if attempt >= attempts_allowed - 1:
                    logger.error(
                        "OpenAI chat completion failed",
                        extra={
                            "provider": "openai",
                            "model": model,
                            "reason": reason,
                            "attempts": attempts_allowed,
                            "user_id": user_id,
                            "correlation_id": correlation_id,
                        },
                    )
                    raise ExternalServiceError(
                        "OpenAI",
                        "OpenAI request failed after retries",
                        details={"reason": reason, "attempts": attempts_allowed},
                    ) from exc

                delay = self._retry_delay(attempt)
                logger.warning(
                    "Retrying OpenAI request",
                    extra={
                        "provider": "openai",
                        "model": model,
                        "reason": reason,
                        "attempt": attempt + 1,
                        "max_attempts": attempts_allowed,
                        "delay_seconds": delay,
                        "user_id": user_id,
                        "correlation_id": correlation_id,
                    },
                )
                await asyncio.sleep(delay)
                continue

            if response.status_code == 200:
                try:
                    data = response.json()
                except ValueError as exc:
                    raise ExternalServiceError(
                        "OpenAI",
                        "OpenAI returned an invalid response",
                        details={"reason": "invalid_json"},
                    ) from exc

                if not isinstance(data, dict):
                    raise ExternalServiceError(
                        "OpenAI",
                        "OpenAI returned an invalid response",
                        details={"reason": "invalid_payload"},
                    )
                return data, attempt + 1

            retryable = response.status_code == 429 or 500 <= response.status_code < 600
            if retryable and attempt < attempts_allowed - 1:
                delay = self._retry_delay(attempt, response)
                logger.warning(
                    "Retrying OpenAI request",
                    extra={
                        "provider": "openai",
                        "model": model,
                        "status_code": response.status_code,
                        "attempt": attempt + 1,
                        "max_attempts": attempts_allowed,
                        "delay_seconds": delay,
                        "user_id": user_id,
                        "correlation_id": correlation_id,
                    },
                )
                await asyncio.sleep(delay)
                continue

            details: dict[str, Any] = {"status_code": response.status_code}
            if retryable:
                details["attempts"] = attempts_allowed
            logger.error(
                "OpenAI chat completion failed",
                extra={
                    "provider": "openai",
                    "model": model,
                    "status_code": response.status_code,
                    "attempts": attempt + 1,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                },
            )
            raise ExternalServiceError(
                "OpenAI",
                "OpenAI request failed",
                details=details,
            )

        raise ExternalServiceError(
            "OpenAI",
            "OpenAI request failed",
            details={"reason": "retry_exhausted"},
        )

    def _retry_delay(self, attempt: int, response: httpx.Response | None = None) -> float:
        """Return a bounded delay, honoring Retry-After when provided."""
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return min(max(float(retry_after), 0.0), _MAX_RETRY_DELAY_SECONDS)
                except ValueError:
                    pass
        return min(0.5 * (2**attempt), _MAX_RETRY_DELAY_SECONDS)

    def _build_response(self, data: dict[str, Any], model: str, latency_ms: float) -> ChatResponse:
        """Normalize an OpenAI response into the public response schema."""
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ExternalServiceError(
                "OpenAI",
                "OpenAI returned an invalid response",
                details={"reason": "missing_choices"},
            )

        choice = choices[0]
        if not isinstance(choice, dict):
            raise ExternalServiceError(
                "OpenAI",
                "OpenAI returned an invalid response",
                details={"reason": "invalid_choice"},
            )

        message = choice.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise ExternalServiceError(
                "OpenAI",
                "OpenAI returned an invalid response",
                details={"reason": "missing_content"},
            )

        usage_payload = data.get("usage")
        if not isinstance(usage_payload, dict):
            usage_payload = {}

        prompt_tokens = _as_int(usage_payload.get("prompt_tokens"))
        completion_tokens = _as_int(usage_payload.get("completion_tokens"))
        total_tokens = _as_int(usage_payload.get("total_tokens"))
        if total_tokens == 0:
            total_tokens = prompt_tokens + completion_tokens

        return ChatResponse(
            id=str(data.get("id", "")),
            model=str(data.get("model") or model),
            content=content,
            finish_reason=choice.get("finish_reason"),
            usage=ChatUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
            latency_ms=round(latency_ms, 3),
            created=_as_optional_int(data.get("created")),
        )
