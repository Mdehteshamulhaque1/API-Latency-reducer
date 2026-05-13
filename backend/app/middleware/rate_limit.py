"""
Rate limiting middleware.
Implements token bucket algorithm for rate limiting.
"""
import hashlib
import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.services.rate_limit import RateLimitService
from app.utils.redis_client import redis_client

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using token bucket algorithm.
    Tracks requests per IP, user, and API key.
    """

    EXCLUDED_PATHS = {
        "/api/v1/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    async def dispatch(self, request: Request, call_next):
        """Process request and check rate limits."""
        if any(request.url.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return await call_next(request)

        identifier = self._get_identifier(request)

        try:
            rate_limit_service = RateLimitService(redis_client)
            is_allowed = await rate_limit_service.is_allowed(identifier)

            if not is_allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded",
                        "error_code": "RATE_LIMIT_EXCEEDED",
                    },
                    headers={"Retry-After": str(rate_limit_service.default_period)},
                )
        except Exception as e:
            logger.error("Rate limit check error: %s", str(e))

        return await call_next(request)

    @staticmethod
    def _get_identifier(request: Request) -> str:
        """Derive the rate-limit key from API key, user, or client IP."""
        api_key = request.headers.get("X-API-Key")
        if api_key:
            digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:24]
            return f"api-key:{digest}"

        if hasattr(request.state, "user_id") and request.state.user_id:
            return f"user:{request.state.user_id}"

        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_host = forwarded_for.split(",")[0].strip()
        else:
            client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"
