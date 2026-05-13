"""
Metrics collection middleware.
Tracks API performance metrics.
"""
import logging
import time
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Collects metrics on API requests and responses.
    Logs response time, status code, and request details.
    """

    async def dispatch(self, request: Request, call_next) -> any:
        """Process request and collect metrics."""
        
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Log metrics
        logger.info(
            f"HTTP {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "response_time_ms": response_time * 1000,
                "correlation_id": getattr(request.state, "correlation_id", "N/A"),
            }
        )
        
        # Add response time header
        response.headers["X-Response-Time"] = str(response_time)
        
        return response
