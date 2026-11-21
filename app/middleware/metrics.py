"""
Metrics collection middleware.

Outermost application middleware (only CORS sits outside it), so the
measured duration covers auth, rate limiting, caching, and the handler.

For every request it:
1. measures wall-clock duration,
2. writes one structured log line (no bodies, no headers, no secrets),
3. adds ``X-Response-Time`` and, on cache hits, ``X-Cache-Hit`` headers,
4. schedules a background task that persists an ``APILog`` row and updates
   the hourly ``Analytics`` roll-up AFTER the response has been sent, so
   database writes never add to the latency the client sees.

LLM gateway metrics for Prometheus are NOT emitted here; ``ChatService``
records them with real values (see ``app/metrics.py``).
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import Request
from starlette.background import BackgroundTask, BackgroundTasks
from starlette.middleware.base import BaseHTTPMiddleware

from app.database.db import async_session_maker
from app.services.analytics import AnalyticsService

logger = logging.getLogger(__name__)

# Synthetic load-test endpoints are not persisted to analytics: logging
# them would skew the dashboard with artificial traffic and throttle the
# benchmark with database writes on the request hot path.
ANALYTICS_EXCLUDED_PREFIXES = ("/api/v1/demo",)


def _content_length(headers) -> int:
    """Parse a Content-Length header, treating missing or invalid values as 0."""
    raw = headers.get("content-length")
    if raw is None:
        return 0
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 0


class MetricsMiddleware(BaseHTTPMiddleware):
    """Measure, log, and persist request metrics."""

    async def dispatch(self, request: Request, call_next) -> Any:
        start_time = time.perf_counter()

        response = await call_next(request)

        response_time = time.perf_counter() - start_time
        cache_hit = getattr(request.state, "cache_hit", False)
        cache_key = getattr(request.state, "cache_key", None)

        logger.info(
            f"HTTP {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "response_time_ms": round(response_time * 1000, 3),
                "correlation_id": getattr(request.state, "correlation_id", "N/A"),
                "cache_hit": cache_hit,
                "cache_key": cache_key,
                "rate_limited": getattr(request.state, "rate_limited", False),
            },
        )

        response.headers["X-Response-Time"] = f"{response_time:.6f}"
        if cache_hit:
            response.headers["X-Cache-Hit"] = "true"

        if request.url.path.startswith(ANALYTICS_EXCLUDED_PREFIXES):
            return response

        # Persist request analytics without blocking response delivery.
        # Preserve any background task the route handler already scheduled.
        existing = response.background
        if existing is None:
            response.background = BackgroundTask(
                self._persist_request_metrics, request, response, response_time
            )
        elif isinstance(existing, BackgroundTasks):
            existing.add_task(self._persist_request_metrics, request, response, response_time)
        else:
            async def _combined():
                await existing()
                await self._persist_request_metrics(request, response, response_time)

            response.background = BackgroundTask(_combined)

        return response

    async def _persist_request_metrics(self, request: Request, response, response_time: float) -> None:
        """Persist request metrics to the APILog and Analytics tables."""
        try:
            async with async_session_maker() as session:
                analytics_service = AnalyticsService(session)
                user_id = getattr(request.state, "user_id", None)
                correlation_id = getattr(request.state, "correlation_id", "")
                client_ip = request.client.host if request.client is not None else "unknown"

                service = getattr(request.state, "service", None)  # set by the reverse proxy
                await analytics_service.log_request(
                    **({"service": service} if service else {}),
                    method=request.method,
                    endpoint=request.url.path,
                    path=str(request.url),
                    status_code=response.status_code,
                    response_time_ms=response_time * 1000,
                    client_ip=client_ip,
                    correlation_id=correlation_id,
                    user_id=int(user_id) if user_id is not None else None,
                    cache_hit=getattr(request.state, "cache_hit", False),
                    cache_key=getattr(request.state, "cache_key", None),
                    request_size_bytes=_content_length(request.headers),
                    response_size_bytes=_content_length(response.headers),
                    query_params=str(request.query_params) if request.query_params else None,
                )
        except Exception as exc:
            logger.error("Failed to persist request analytics: %s", exc)
