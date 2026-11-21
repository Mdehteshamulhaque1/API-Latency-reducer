"""
Prometheus metrics for the LLM gateway, exposed at GET /metrics.

Every value here is recorded by ``ChatService`` at the moment it happens:
a cache hit, a successful provider call, a fallback, or a failure. Nothing
is estimated or emitted per HTTP request, so a counter only moves when a
real chat completion moved it.

Metric names and labels
-----------------------
chat_requests_total{served_model, cache_type, status}
    cache_type: "hit" | "miss"      status: "success" | "error"
chat_provider_latency_seconds{served_model}
    Time spent waiting on the provider, excluding cache work.
chat_request_latency_seconds{served_model}
    End-to-end gateway latency, including cache lookups and fallback.
chat_prompt_tokens_total{served_model} / chat_completion_tokens_total{served_model}
    Token counts exactly as reported by the provider.
chat_estimated_cost_usd_total{served_model}
    Estimated spend from PRICING_TABLE; an estimate, not a bill.
chat_fallback_total{status}
    status: "success" when the fallback model answered, "error" when it failed too.
chat_circuit_breaker_state{model}
    0 = closed, 1 = open, 2 = half-open.
"""

from __future__ import annotations

from prometheus_client import REGISTRY, Counter, Gauge, Histogram

_registry = REGISTRY

_LATENCY_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30)

chat_requests_total = Counter(
    "chat_requests_total",
    "Chat completion requests handled by the gateway.",
    ["served_model", "cache_type", "status"],
    registry=_registry,
)

chat_provider_latency_seconds = Histogram(
    "chat_provider_latency_seconds",
    "Latency of the upstream provider call in seconds.",
    ["served_model"],
    registry=_registry,
    buckets=_LATENCY_BUCKETS,
)

chat_request_latency_seconds = Histogram(
    "chat_request_latency_seconds",
    "End-to-end gateway latency in seconds.",
    ["served_model"],
    registry=_registry,
    buckets=_LATENCY_BUCKETS,
)

chat_prompt_tokens_total = Counter(
    "chat_prompt_tokens_total",
    "Prompt tokens reported by the provider.",
    ["served_model"],
    registry=_registry,
)

chat_completion_tokens_total = Counter(
    "chat_completion_tokens_total",
    "Completion tokens reported by the provider.",
    ["served_model"],
    registry=_registry,
)

chat_estimated_cost_usd_total = Counter(
    "chat_estimated_cost_usd_total",
    "Estimated spend in USD based on the configured pricing table.",
    ["served_model"],
    registry=_registry,
)

chat_fallback_total = Counter(
    "chat_fallback_total",
    "Fallback model attempts by outcome.",
    ["status"],
    registry=_registry,
)

chat_circuit_breaker_state = Gauge(
    "chat_circuit_breaker_state",
    "Circuit breaker state per primary model (0=closed, 1=open, 2=half_open).",
    ["model"],
    registry=_registry,
)

_BREAKER_STATE_VALUES = {"closed": 0, "open": 1, "half_open": 2}


def record_cache_hit(served_model: str, latency_seconds: float) -> None:
    """A response was served from the exact-match cache."""
    chat_requests_total.labels(served_model=served_model, cache_type="hit", status="success").inc()
    chat_request_latency_seconds.labels(served_model=served_model).observe(latency_seconds)


def record_success(
    served_model: str,
    *,
    latency_seconds: float,
    prompt_tokens: int,
    completion_tokens: int,
    estimated_cost_usd: float,
    fallback_used: bool,
) -> None:
    """A provider call succeeded (primary or fallback)."""
    chat_requests_total.labels(served_model=served_model, cache_type="miss", status="success").inc()
    chat_request_latency_seconds.labels(served_model=served_model).observe(latency_seconds)
    chat_prompt_tokens_total.labels(served_model=served_model).inc(max(prompt_tokens, 0))
    chat_completion_tokens_total.labels(served_model=served_model).inc(max(completion_tokens, 0))
    chat_estimated_cost_usd_total.labels(served_model=served_model).inc(max(estimated_cost_usd, 0.0))
    if fallback_used:
        chat_fallback_total.labels(status="success").inc()


def record_failure(model: str, *, latency_seconds: float, fallback_attempted: bool) -> None:
    """Every configured model path failed for this request."""
    chat_requests_total.labels(served_model=model, cache_type="miss", status="error").inc()
    chat_request_latency_seconds.labels(served_model=model).observe(latency_seconds)
    if fallback_attempted:
        chat_fallback_total.labels(status="error").inc()


def observe_provider_latency(served_model: str, latency_seconds: float) -> None:
    """Time spent inside one upstream call, including its retries."""
    chat_provider_latency_seconds.labels(served_model=served_model).observe(latency_seconds)


def set_circuit_breaker_state(model: str, state: str) -> None:
    """Mirror the in-process breaker state for ``model`` ("closed"/"open"/"half_open")."""
    chat_circuit_breaker_state.labels(model=model).set(_BREAKER_STATE_VALUES.get(state, 0))
