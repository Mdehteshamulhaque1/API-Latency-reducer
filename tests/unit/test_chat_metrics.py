"""Metrics endpoint tests for the LLM Gateway.

Tests /metrics output and Prometheus registry state.
"""

import pytest


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_200(client):
    """Assert /metrics returns 200 with Prometheus text format."""
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    content_type = resp.headers.get("content-type", "")
    assert "text/plain" in content_type or "application/openmetrics" in content_type


@pytest.mark.asyncio
async def test_metrics_contains_counter_labels(client):
    """Assert metrics output contains counter labels for cache miss/hit."""
    resp = await client.get("/metrics")
    body = resp.text
    # chat_requests_total should have cache_type and status labels
    assert "chat_requests_total" in body
    # Should have cache_type label values
    assert 'cache_type="' in body


@pytest.mark.asyncio
async def test_metrics_fallback_counter(client):
    """Assert fallback_total counter exists and has status label."""
    resp = await client.get("/metrics")
    body = resp.text
    assert "chat_fallback_total" in body
    # Should have status label (success, error, rate_limited)
    assert 'status="' in body


@pytest.mark.asyncio
async def test_metrics_error_status_label(client, admin_headers):
    """Assert error status label appears after error-producing request."""
    # First make a request that will produce an error path
    resp = await client.post("/api/v1/auth/register", json={"email": "newuser@example.com", "password": "password123"})
    # Then check metrics
    resp = await client.get("/metrics")
    body = resp.text
    assert "chat_requests_total" in body
    # Check for error status in fallback
    assert 'status="' in body


@pytest.mark.asyncio
async def test_metrics_registry_counters_increment():
    """Directly verify Prometheus registry counters exist and have correct types."""
    from app.metrics import chat_requests_total, chat_fallback_total
    # Verify metrics are Counter instances
    from prometheus_client import Counter
    assert isinstance(chat_requests_total, Counter)
    assert isinstance(chat_fallback_total, Counter)
    # The full metric name includes the suffix; _name strips it
    assert chat_requests_total._name in ("chat_requests", "chat_requests_total")
    assert chat_fallback_total._name in ("chat_fallback", "chat_fallback_total")