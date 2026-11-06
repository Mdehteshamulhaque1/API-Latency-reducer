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

from app.config import settings, compute_estimated_cost
from app.core.constants import CACHE_KEY_CHAT_PREFIX
from app.core.exceptions import ExternalServiceError
from app.schemas.chat import ChatRequest, ChatResponse, ChatUsage
from app.services.cache import CacheService
from app.services.circuit_breaker import CircuitBreaker, CircuitState, get_circuit_breaker
from app.utils.redis_client import redis_client

logger = logging.getLogger(__name__)

_MAX_RETRY_DELAY_SECONDS = 10.0


class _ProviderFailure(ExternalServiceError):
    """Internal provider error carrying fallback eligibility without exposing it."""

    def __init__(
        self,
        service_name: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
        *,
        fallback_eligible: bool = False,
    ) -> None:
        self.fallback_eligible = fallback_eligible
        super().__init__(service_name, message, details=details)


def _failure_summary(exc: ExternalServiceError | None) -> dict[str, Any]:
    """Return a small, safe failure summary for logs and error details."""
    if exc is None:
        return {"reason": "circuit_open"}
    details = exc.details or {}
    summary: dict[str, Any] = {}
    for key in ("status_code", "reason", "attempts"):
        if key in details:
            summary[key] = details[key]
    if not summary:
        summary["error"] = type(exc).__name__
    return summary


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
        breaker: CircuitBreaker | None = None,
    ):
        self._settings = settings_obj or settings
        self._transport = transport
        self._client = client
        self._cache = cache or CacheService(redis_client)
        self._cache_ttl = getattr(self._settings, "redis_cache_ttl", 3600)
        self._breaker = breaker

    async def create_chat_completion(
        self,
        request: ChatRequest,
        user_id: int | None = None,
        correlation_id: str | None = None,
    ) -> ChatResponse:
        """Create a chat completion, using cache, primary, then fallback."""
        if not self._settings.openai_api_key:
            raise ExternalServiceError(
                "OpenAI",
                "OpenAI API key is not configured",
                details={"reason": "missing_api_key"},
            )

        requested_model = request.model
        primary_model = (
            requested_model
            or getattr(self._settings, "openai_primary_model", None)
            or self._settings.openai_model
        )
        fallback_model = getattr(self._settings, "openai_fallback_model", None)
        if isinstance(fallback_model, str):
            fallback_model = fallback_model.strip() or None
        if fallback_model == primary_model:
            fallback_model = None

        messages = [message.model_dump() for message in request.messages]
        cache_enabled = request.temperature <= 0
        primary_cache_key = self._build_cache_key(
            primary_model,
            messages,
            request.temperature,
        )
        fallback_cache_key = (
            self._build_cache_key(fallback_model, messages, request.temperature)
            if fallback_model is not None
            else None
        )
        started_at = time.perf_counter()
        breaker = self._get_breaker(primary_model)

        if cache_enabled:
            cached_response = await self._get_cached_response(
                primary_cache_key,
                user_id,
                correlation_id,
            )
            if cached_response is not None:
                return self._cached_chat_response(
                    cached_response,
                    primary_cache_key,
                    started_at,
                    requested_model,
                    primary_model,
                    fallback_model,
                    user_id,
                    correlation_id,
                    fallback_used=False,
                    circuit_state=breaker.state.value,
                    cache_type="exact",
                    estimated_cost_usd=0.0,
                )

        allowed = breaker.allow_request()
        breaker_state = breaker.state
        if not allowed:
            if breaker_state is CircuitState.HALF_OPEN:
                logger.info(
                    "Primary model half-open probe already in flight; using fallback",
                    extra={
                        "requested_model": requested_model,
                        "primary_model": primary_model,
                        "fallback_model": fallback_model,
                        "circuit_state": breaker_state.value,
                        "user_id": user_id,
                        "correlation_id": correlation_id,
                    },
                )
            else:
                logger.info(
                    "Primary model circuit open; skipping primary",
                    extra={
                        "requested_model": requested_model,
                        "primary_model": primary_model,
                        "fallback_model": fallback_model,
                        "circuit_state": breaker_state.value,
                        "failure_count": breaker.failure_count,
                        "user_id": user_id,
                        "correlation_id": correlation_id,
                    },
                )
            return await self._fallback_or_raise(
                primary_model=primary_model,
                fallback_model=fallback_model,
                fallback_cache_key=fallback_cache_key,
                cache_enabled=cache_enabled,
                messages=messages,
                request=request,
                started_at=started_at,
                user_id=user_id,
                correlation_id=correlation_id,
                primary_error=None,
                requested_model=requested_model,
                breaker=breaker,
            )

        if breaker_state is CircuitState.HALF_OPEN:
            logger.info(
                "Primary model circuit half-open probe",
                extra={
                    "requested_model": requested_model,
                    "primary_model": primary_model,
                    "fallback_model": fallback_model,
                    "circuit_state": breaker_state.value,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                },
            )

        try:
            data, attempts = await self._call_model(
                primary_model,
                messages,
                request,
                user_id,
                correlation_id,
            )
            latency_ms = (time.perf_counter() - started_at) * 1000
            response = self._build_response(
                data,
                primary_model,
                latency_ms,
                fallback_used=False,
            )
        except ExternalServiceError as primary_error:
            if not self._is_fallback_eligible(primary_error):
                raise

            previous_state = breaker.state
            breaker.record_failure()
            new_state = breaker.state
            if new_state is CircuitState.OPEN and previous_state is not CircuitState.OPEN:
                logger.warning(
                    "Primary model circuit opened",
                    extra={
                        "requested_model": requested_model,
                        "primary_model": primary_model,
                        "fallback_model": fallback_model,
                        "circuit_state": new_state.value,
                        "failure_count": breaker.failure_count,
                        "failure_threshold": breaker.failure_threshold,
                        "cooldown_seconds": breaker.cooldown_seconds,
                        "user_id": user_id,
                        "correlation_id": correlation_id,
                    },
                )

            logger.warning(
                "Primary model failed; attempting fallback",
                extra={
                    "requested_model": requested_model,
                    "primary_model": primary_model,
                    "fallback_model": fallback_model,
                    "circuit_state": new_state.value,
                    **self._failure_extra(primary_error),
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                },
            )

            return await self._fallback_or_raise(
                primary_model=primary_model,
                fallback_model=fallback_model,
                fallback_cache_key=fallback_cache_key,
                cache_enabled=cache_enabled,
                messages=messages,
                request=request,
                started_at=started_at,
                user_id=user_id,
                correlation_id=correlation_id,
                primary_error=primary_error,
                requested_model=requested_model,
                breaker=breaker,
            )

        previous_state = breaker.state
        breaker.record_success()
        if previous_state is CircuitState.HALF_OPEN:
            logger.info(
                "Primary model circuit closed",
                extra={
                    "requested_model": requested_model,
                    "primary_model": primary_model,
                    "fallback_model": fallback_model,
                    "circuit_state": breaker.state.value,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                },
            )

        if cache_enabled:
            await self._store_cached_response(
                primary_cache_key,
                response,
                user_id,
                correlation_id,
            )

        # --- cost estimation ---
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        estimated_cost_usd = compute_estimated_cost(
            served_model=response.served_model or primary_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            pricing_table=settings.PRICING_TABLE,
            global_prompt_price=getattr(settings, "chat_prompt_price_per_million", 0.0),
            global_completion_price=getattr(settings, "chat_completion_price_per_million", 0.0),
        )
        cache_type = "miss"

        self._log_success(
            response,
            requested_model,
            primary_model,
            fallback_model,
            attempts,
            primary_cache_key if cache_enabled else None,
            user_id,
            correlation_id,
            fallback_used=False,
            circuit_state=breaker.state.value,
            estimated_cost_usd=estimated_cost_usd,
            cache_type=cache_type,
        )
        return response

    def _get_breaker(self, model: str) -> CircuitBreaker:
        """Return the injected or process-wide breaker for a primary model."""
        if self._breaker is not None:
            return self._breaker
        return get_circuit_breaker(
            f"openai:{model}",
            failure_threshold=getattr(self._settings, "llm_circuit_failure_threshold", 5),
            cooldown_seconds=getattr(self._settings, "llm_circuit_cooldown_seconds", 30.0),
            half_open_max_probes=getattr(
                self._settings,
                "llm_circuit_half_open_max_probes",
                1,
            ),
            half_open_success_threshold=getattr(
                self._settings,
                "llm_circuit_half_open_success_threshold",
                1,
            ),
        )

    def _build_payload(
        self,
        model: str,
        messages: list[dict[str, Any]],
        request: ChatRequest,
    ) -> dict[str, Any]:
        """Build an OpenAI chat-completions payload for one model."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        return payload

    async def _call_model(
        self,
        model: str,
        messages: list[dict[str, Any]],
        request: ChatRequest,
        user_id: int | None,
        correlation_id: str | None,
        max_retries: int | None = None,
    ) -> tuple[dict[str, Any], int]:
        """Call one model using the existing retry policy."""
        payload = self._build_payload(model, messages, request)
        url = f"{self._settings.openai_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        timeout = httpx.Timeout(self._settings.openai_timeout_seconds)

        if self._client is not None:
            return await self._request_with_retries(
                self._client,
                url,
                headers,
                payload,
                model,
                user_id,
                correlation_id,
                max_retries=max_retries,
            )

        async with httpx.AsyncClient(timeout=timeout, transport=self._transport) as client:
            return await self._request_with_retries(
                client,
                url,
                headers,
                payload,
                model,
                user_id,
                correlation_id,
                max_retries=max_retries,
            )

    async def _fallback_or_raise(
        self,
        *,
        primary_model: str,
        fallback_model: str | None,
        fallback_cache_key: str | None,
        cache_enabled: bool,
        messages: list[dict[str, Any]],
        request: ChatRequest,
        started_at: float,
        user_id: int | None,
        correlation_id: str | None,
        primary_error: ExternalServiceError | None,
        requested_model: str | None,
        breaker: CircuitBreaker,
    ) -> ChatResponse:
        """Use the fallback model, its cache, or raise a clean error."""
        if fallback_model is None:
            if primary_error is None:
                raise ExternalServiceError(
                    "OpenAI",
                    "Primary model circuit is open and no fallback model is configured",
                    details={
                        "reason": "circuit_open",
                        "primary_model": primary_model,
                    },
                )
            raise primary_error

        if cache_enabled and fallback_cache_key is not None:
            cached_response = await self._get_cached_response(
                fallback_cache_key,
                user_id,
                correlation_id,
            )
            if cached_response is not None:
                return self._cached_chat_response(
                    cached_response,
                    fallback_cache_key,
                    started_at,
                    requested_model,
                    primary_model,
                    fallback_model,
                    user_id,
                    correlation_id,
                    fallback_used=True,
                )

        try:
            data, attempts = await self._call_model(
                fallback_model,
                messages,
                request,
                user_id,
                correlation_id,
                max_retries=0,
            )
            latency_ms = (time.perf_counter() - started_at) * 1000
            response = self._build_response(
                data,
                fallback_model,
                latency_ms,
                fallback_used=True,
            )
        except ExternalServiceError as fallback_error:
            logger.error(
                "Fallback model failed",
                extra={
                    "requested_model": requested_model,
                    "primary_model": primary_model,
                    "fallback_model": fallback_model,
                    "served_model": fallback_model,
                    "fallback_used": True,
                    "circuit_state": "open" if primary_error is None else "closed",
                    **self._failure_extra(fallback_error),
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                },
            )
            all_models_error = self._all_models_failed_error(
                primary_model,
                fallback_model,
                primary_error,
                fallback_error,
            )
            logger.error(
                "All configured chat models failed",
                extra={
                    "requested_model": requested_model,
                    "primary_model": primary_model,
                    "fallback_model": fallback_model,
                    "served_model": None,
                    "fallback_used": True,
                    "user_id": user_id,
                    "correlation_id": correlation_id,
                },
            )
            raise all_models_error from fallback_error

        if cache_enabled:
            await self._store_cached_response(
                fallback_cache_key,
                response,
                user_id,
                correlation_id,
            )

        circuit_state = breaker.state.value
        self._log_success(
            response,
            requested_model,
            primary_model,
            fallback_model,
            attempts,
            fallback_cache_key if cache_enabled else None,
            user_id,
            correlation_id,
            fallback_used=True,
            circuit_state=circuit_state,
        )
        return response

    def _cached_chat_response(
        self,
        cached_response: ChatResponse,
        cache_key: str,
        started_at: float,
        requested_model: str | None,
        primary_model: str,
        fallback_model: str | None,
        user_id: int | None,
        correlation_id: str | None,
        *,
        fallback_used: bool,
        circuit_state: str,
        cache_type: str = "miss",
        estimated_cost_usd: float = 0.0,
    ) -> ChatResponse:
        """Return a cache hit with fresh latency and served-model metadata."""
        latency_ms = (time.perf_counter() - started_at) * 1000
        response = cached_response.model_copy(
            update={
                "cached": True,
                "latency_ms": round(latency_ms, 3),
                "served_model": cached_response.served_model or cached_response.model,
                "fallback_used": fallback_used,
            }
        )
        logger.info(
            "Chat completion cache hit",
            extra={
                "provider": "openai",
                "requested_model": requested_model,
                "primary_model": primary_model,
                "fallback_model": fallback_model,
                "model": response.model,
                "served_model": response.served_model,
                "fallback_used": fallback_used,
                "cache_type": cache_type,
                "estimated_cost_usd": estimated_cost_usd,
                "cache_key": cache_key,
                "latency_ms": round(response.latency_ms, 2),
                "user_id": user_id,
                "correlation_id": correlation_id,
                "circuit_state": circuit_state,
            },
        )
        return response

    def _log_success(
        self,
        response: ChatResponse,
        requested_model: str | None,
        primary_model: str,
        fallback_model: str | None,
        attempts: int,
        cache_key: str | None,
        user_id: int | None,
        correlation_id: str | None,
        *,
        fallback_used: bool,
        circuit_state: str,
        estimated_cost_usd: float = 0.0,
        cache_type: str = "miss",
    ) -> None:
        """Log one successful provider call with model attribution."""
        logger.info(
            "OpenAI chat completion succeeded",
            extra={
                "provider": "openai",
                "requested_model": requested_model,
                "primary_model": primary_model,
                "fallback_model": fallback_model,
                "model": response.model,
                "served_model": response.served_model or response.model,
                "fallback_used": fallback_used,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "latency_ms": round(response.latency_ms, 2),
                "attempts": attempts,
                "cached": False,
                "cache_key": cache_key,
                "user_id": user_id,
                "correlation_id": correlation_id,
                "circuit_state": circuit_state,
                "estimated_cost_usd": estimated_cost_usd,
                "cache_type": cache_type,
            },
        )

    @staticmethod
    def _is_fallback_eligible(exc: ExternalServiceError) -> bool:
        """Return whether a primary failure should trigger fallback."""
        return isinstance(exc, _ProviderFailure) and exc.fallback_eligible

    @staticmethod
    def _failure_extra(exc: ExternalServiceError) -> dict[str, Any]:
        """Return safe failure fields for structured logs."""
        return _failure_summary(exc)

    @staticmethod
    def _all_models_failed_error(
        primary_model: str,
        fallback_model: str,
        primary_error: ExternalServiceError | None,
        fallback_error: ExternalServiceError,
    ) -> ExternalServiceError:
        """Build a clean 503 error when both model paths fail."""
        return ExternalServiceError(
            "OpenAI",
            "All configured chat models failed",
            details={
                "primary_model": primary_model,
                "fallback_model": fallback_model,
                "primary_error": _failure_summary(primary_error),
                "fallback_error": _failure_summary(fallback_error),
            },
        )

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
        max_retries: int | None = None,
    ) -> tuple[dict[str, Any], int]:
        """POST to OpenAI, retrying transient failures within the configured limit."""
        retry_limit = (
            self._settings.openai_max_retries
            if max_retries is None
            else max(0, max_retries)
        )
        attempts_allowed = retry_limit + 1

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
                    raise _ProviderFailure(
                        "OpenAI",
                        "OpenAI request failed after retries",
                        details={"reason": reason, "attempts": attempts_allowed},
                        fallback_eligible=True,
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
                    raise _ProviderFailure(
                        "OpenAI",
                        "OpenAI returned an invalid response",
                        details={"reason": "invalid_json"},
                        fallback_eligible=False,
                    ) from exc

                if not isinstance(data, dict):
                    raise _ProviderFailure(
                        "OpenAI",
                        "OpenAI returned an invalid response",
                        details={"reason": "invalid_payload"},
                        fallback_eligible=False,
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
            raise _ProviderFailure(
                "OpenAI",
                "OpenAI request failed",
                details=details,
                fallback_eligible=retryable,
            )

        raise _ProviderFailure(
            "OpenAI",
            "OpenAI request failed",
            details={"reason": "retry_exhausted"},
            fallback_eligible=True,
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

    def _build_response(
        self,
        data: dict[str, Any],
        model: str,
        latency_ms: float,
        *,
        fallback_used: bool = False,
    ) -> ChatResponse:
        """Normalize an OpenAI response into the public response schema."""
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise _ProviderFailure(
                "OpenAI",
                "OpenAI returned an invalid response",
                details={"reason": "missing_choices"},
                fallback_eligible=False,
            )

        choice = choices[0]
        if not isinstance(choice, dict):
            raise _ProviderFailure(
                "OpenAI",
                "OpenAI returned an invalid response",
                details={"reason": "invalid_choice"},
                fallback_eligible=False,
            )

        message = choice.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise _ProviderFailure(
                "OpenAI",
                "OpenAI returned an invalid response",
                details={"reason": "missing_content"},
                fallback_eligible=False,
            )

        usage_payload = data.get("usage")
        if not isinstance(usage_payload, dict):
            usage_payload = {}

        prompt_tokens = _as_int(usage_payload.get("prompt_tokens"))
        completion_tokens = _as_int(usage_payload.get("completion_tokens"))
        total_tokens = _as_int(usage_payload.get("total_tokens"))
        if total_tokens == 0:
            total_tokens = prompt_tokens + completion_tokens

        served_model = str(data.get("model") or model)
        return ChatResponse(
            id=str(data.get("id", "")),
            model=served_model,
            served_model=served_model,
            fallback_used=fallback_used,
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
