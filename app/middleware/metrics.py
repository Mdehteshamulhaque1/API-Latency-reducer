"""
Metrics collection middleware.
Tracks API performance metrics.
"""
import logging
import time
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.database.db import async_session_maker
from app.services.analytics import AnalyticsService

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Collects metrics on API requests and responses.
    Logs response time, status code, and request details, and persists analytics.
    """

    async def dispatch(self, request: Request, call_next) -> Any:
        """Process request and collect metrics."""
        
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        cache_hit = getattr(request.state, "cache_hit", False)
        cache_key = getattr(request.state, "cache_key", None)

        # Log metrics
        logger.info(
            f"HTTP {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "response_time_ms": response_time * 1000,
                "correlation_id": getattr(request.state, "correlation_id", "N/A"),
                "cache_hit": cache_hit,
                "cache_key": cache_key,
            }
        )
        
        # Add response time header
        response.headers["X-Response-Time"] = str(response_time)
        if cache_hit:
            response.headers["X-Cache-Hit"] = "true"

        # Persist request analytics without blocking response delivery.
        await self._persist_request_metrics(request, response, response_time)
        
        return response

    async def _persist_request_metrics(self, request: Request, response, response_time: float) -> None:
        """Persist request metrics to APILog and Analytics tables."""
        try:
            async with async_session_maker() as session:
                analytics_service = AnalyticsService(session)
                user_id = getattr(request.state, "user_id", None)
                correlation_id = getattr(request.state, "correlation_id", "")
                client_ip = "unknown"
                if request.client is not None:
                    client_ip = request.client.host

                await analytics_service.log_request(
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
                    request_size_bytes=0,
                    response_size_bytes=0,
                    query_params=str(request.query_params) if request.query_params else None,
                )
        except Exception as exc:
            logger.error("Failed to persist request analytics: %s", exc)
