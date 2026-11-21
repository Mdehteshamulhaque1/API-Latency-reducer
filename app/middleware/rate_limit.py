"""
Rate limiting middleware.

Runs after AuthMiddleware (so ``request.state.user_id`` is available) and
before CacheMiddleware (so cached responses still count against the limit).

Identifier strategy
-------------------
* Authenticated request  -> ``user:<id>``   (one bucket per account)
* Anonymous request      -> ``ip:<addr>``   (one bucket per client address)

Tiers (``app.services.rate_limit.limits_for_role``)
---------------------------------------------------
* anonymous   -> ``RATE_LIMIT_ANONYMOUS_*``  (60 per minute by default)
* user        -> ``RATE_LIMIT_USER_*``       (300 per minute: viewer, guest)
* privileged  -> ``RATE_LIMIT_PRIVILEGED_*`` (1000 per minute: operator, admin)

Headers the client cannot influence are the only inputs. In particular an
``X-API-Key`` header is ignored: the application has no API-key records, so
honouring it would let anyone escape the IP bucket by sending a random value.
``X-Forwarded-For`` is only trusted when the direct peer is a configured
reverse proxy (``TRUSTED_PROXIES``).

Responses
---------
Every rate-limited route receives the IETF draft headers ``RateLimit-Limit``,
``RateLimit-Remaining``, ``RateLimit-Reset`` and ``RateLimit-Policy``
(``<limit>;w=<window>``) plus the older ``X-RateLimit-*`` trio for existing
clients. When the bucket is empty the request is rejected with HTTP 429 and a
``Retry-After`` header holding the number of seconds until the next token is
available.

Failure policy: fail open (see ``RateLimitService``).
"""
import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.services.rate_limit import RateLimitDecision, RateLimitService, limits_for_role
from app.utils.redis_client import redis_client

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token-bucket rate limiting per user or client IP."""

    EXCLUDED_PATHS = {
        "/api/v1/health",
        "/api/v1/demo/latency",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    async def dispatch(self, request: Request, call_next):
        """Take a token for the caller, or reject with 429."""
        if any(request.url.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return await call_next(request)

        identifier = self.get_identifier(request)
        tier = limits_for_role(
            getattr(request.state, "user_role", None),
            authenticated=identifier.startswith("user:"),
        )
        decision = await RateLimitService(redis_client).check(
            identifier, requests=tier.requests, period=tier.period, tier=tier.name
        )
        request.state.rate_limit_identifier = identifier
        request.state.rate_limit_tier = tier.name
        request.state.rate_limited = not decision.allowed

        if not decision.allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                },
                headers={"Retry-After": str(decision.retry_after_seconds)},
            )
            self._apply_headers(response, decision)
            return response

        response = await call_next(request)
        self._apply_headers(response, decision)
        return response

    @staticmethod
    def _apply_headers(response, decision: RateLimitDecision) -> None:
        # IETF draft-ietf-httpapi-ratelimit-headers names, plus the X- trio.
        response.headers["RateLimit-Limit"] = str(decision.limit)
        response.headers["RateLimit-Remaining"] = str(decision.remaining)
        response.headers["RateLimit-Reset"] = str(decision.reset_in_seconds)
        response.headers["RateLimit-Policy"] = decision.policy
        response.headers["X-RateLimit-Limit"] = str(decision.limit)
        response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
        response.headers["X-RateLimit-Reset"] = str(decision.reset_in_seconds)

    @staticmethod
    def get_identifier(request: Request) -> str:
        """Derive the rate-limit key from the authenticated user or client IP."""
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        client_host = request.client.host if request.client else "unknown"

        # Only trust X-Forwarded-For when the request arrives directly from a
        # configured reverse proxy; otherwise a client could spoof the header
        # and evade rate limiting.
        if request.client and request.client.host in settings.trusted_proxies:
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                client_host = forwarded_for.split(",")[0].strip()

        return f"ip:{client_host}"
