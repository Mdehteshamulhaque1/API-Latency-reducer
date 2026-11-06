"""
Prometheus metrics for the LLM Gateway.

Exposes GET /metrics with a single registry containing:
- chat_requests_total{served_model,cache_type,status}
- chat_provider_latency_seconds{served_model} histogram
- chat_request_latency_seconds{served_model} histogram
- chat_prompt_tokens_total{served_model}
- chat_completion_tokens_total{served_model}
- chat_estimated_cost_usd_total
- chat_fallback_total{status}
- chat_circuit_breaker_state{state}
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge, REGISTRY

# ---------------------------------------------------------------------------
# Global registry – single registry shared across the process.
# ---------------------------------------------------------------------------
_registry = REGISTRY

# ---------------------------------------------------------------------------
# chat_requests_total – total number of chat completion requests by model,
# cache type and status (miss/hit/fallback/error).
# ---------------------------------------------------------------------------
chat_requests_total = Counter(
    "chat_requests_total",
    "Total number of chat completion requests.",
    ["served_model", "cache_type", "status"],
    registry=_registry,
)

# ---------------------------------------------------------------------------
# chat_provider_latency_seconds – latency (in seconds) of the provider call,
# per served model. Histogram with explicit buckets.
# ---------------------------------------------------------------------------
chat_provider_latency_seconds = Histogram(
    "chat_provider_latency_seconds",
    "Latency of the provider call in seconds.",
    ["served_model"],
    registry=_registry,
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 30),
)

# ---------------------------------------------------------------------------
# chat_request_latency_seconds – total request latency (including cache,
# provider, fallback) in seconds per served model.
# ---------------------------------------------------------------------------
chat_request_latency_seconds = Histogram(
    "chat_request_latency_seconds",
    "Total request latency in seconds.",
    ["served_model"],
    registry=_registry,
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 30),
)

# ---------------------------------------------------------------------------
# chat_prompt_tokens_total – total prompt tokens served per model.
# ---------------------------------------------------------------------------
chat_prompt_tokens_total = Counter(
    "chat_prompt_tokens_total",
    "Total prompt tokens served.",
    ["served_model"],
    registry=_registry,
)

# ---------------------------------------------------------------------------
# chat_completion_tokens_total – total completion tokens served per model.
# ---------------------------------------------------------------------------
chat_completion_tokens_total = Counter(
    "chat_completion_tokens_total",
    "Total completion tokens served.",
    ["served_model"],
    registry=_registry,
)

# ---------------------------------------------------------------------------
# chat_estimated_cost_usd_total – total estimated cost in USD.
# ---------------------------------------------------------------------------
chat_estimated_cost_usd_total = Counter(
    "chat_estimated_cost_usd_total",
    "Total estimated cost in USD.",
    registry=_registry,
)

# ---------------------------------------------------------------------------
# chat_fallback_total – number of fallback attempts by status.
# ---------------------------------------------------------------------------
chat_fallback_total = Counter(
    "chat_fallback_total",
    "Number of fallback attempts.",
    ["status"],
    registry=_registry,
)

# ---------------------------------------------------------------------------
# chat_circuit_breaker_state – current circuit breaker state per model.
# ---------------------------------------------------------------------------
chat_circuit_breaker_state = Gauge(
    "chat_circuit_breaker_state",
    "Current circuit breaker state (0=CLOSED, 1=OPEN, 2=HALF_OPEN).",
    ["state"],
    registry=_registry,
)


# ---------------------------------------------------------------------------
# Helper: increment chat_requests_total
# ---------------------------------------------------------------------------
def inc_requests(served_model: str, cache_type: str, status: str) -> None:
    chat_requests_total.labels(served_model=served_model, cache_type=cache_type, status=status).inc()


# ---------------------------------------------------------------------------
# Helper: observe provider latency
# ---------------------------------------------------------------------------
def observe_provider_latency(served_model: str, latency_seconds: float) -> None:
    chat_provider_latency_seconds.labels(served_model=served_model).observe(latency_seconds)


# ---------------------------------------------------------------------------
# Helper: observe total request latency
# ---------------------------------------------------------------------------
def observe_request_latency(served_model: str, latency_seconds: float) -> None:
    chat_request_latency_seconds.labels(served_model=served_model).observe(latency_seconds)


# ---------------------------------------------------------------------------
# Helper: increment prompt tokens
# ---------------------------------------------------------------------------
def inc_prompt_tokens(served_model: str, count: int) -> None:
    chat_prompt_tokens_total.labels(served_model=served_model).inc(count)


# ---------------------------------------------------------------------------
# Helper: increment completion tokens
# ---------------------------------------------------------------------------
def inc_completion_tokens(served_model: str, count: int) -> None:
    chat_completion_tokens_total.labels(served_model=served_model).inc(count)


# ---------------------------------------------------------------------------
# Helper: increment estimated cost
# ---------------------------------------------------------------------------
def inc_estimated_cost_usd(total_cost: float) -> None:
    chat_estimated_cost_usd_total.inc(total_cost)


# ---------------------------------------------------------------------------
# Helper: increment fallback counter
# ---------------------------------------------------------------------------
def inc_fallback(status: str = "success") -> None:
    chat_fallback_total.labels(status=status).inc()


# ---------------------------------------------------------------------------
# Helper: set circuit breaker state gauge
# ---------------------------------------------------------------------------
def set_circuit_breaker_state(state: str, model: str | None = None) -> None:
    """Set the circuit breaker state gauge.

    state: "CLOSED", "OPEN", or "HALF_OPEN"
    """
    # Map state string to numeric value for the gauge
    state_map = {"CLOSED": "0", "OPEN": "1", "HALF_OPEN": "2"}
    numeric = state_map.get(state, "0")
    # If a model is specified, we currently just set the global state gauge;
    # per-model gauges would require additional labelling.
    chat_circuit_breaker_state.labels(state=numeric).set(1 if model is None else 0)
    # When a model is provided, we still set the gauge to 1 for that state;
    # the model information is conveyed via the metric description, not labels.
    if model is not None:
        chat_circuit_breaker_state.labels(state=numeric).set(1)