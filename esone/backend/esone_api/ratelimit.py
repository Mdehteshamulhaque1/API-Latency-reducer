"""Small in-memory rate limiter for the credential endpoints.

Per client IP, sliding one-minute window. Good enough for a single Render
instance; swap for a shared store if the API ever runs on several instances.
"""
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from esone_api.config import get_settings

LIMITED_PATHS = {"/api/v1/auth/login", "/api/v1/auth/register"}
WINDOW_SECONDS = 60


class SlidingWindow:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def reset(self) -> None:
        self._hits.clear()

    def check(self, key: str, limit: int) -> int:
        """Record a hit. Return 0 if allowed, else seconds until the window frees up."""
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] >= WINDOW_SECONDS:
            hits.popleft()
        if len(hits) >= limit:
            return max(1, int(WINDOW_SECONDS - (now - hits[0])) + 1)
        hits.append(now)
        # Drop idle keys so the map cannot grow without bound.
        if len(self._hits) > 10_000:
            for k in [k for k, v in self._hits.items() if not v or now - v[-1] >= WINDOW_SECONDS]:
                del self._hits[k]
        return 0


limiter = SlidingWindow()


def client_ip(request: Request) -> str:
    """Honour X-Forwarded-For only when told the app sits behind a trusted proxy."""
    if get_settings().trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if request.method == "POST" and request.url.path in LIMITED_PATHS:
            limit = get_settings().auth_rate_limit_per_minute
            if limit > 0:
                wait = limiter.check(f"{request.url.path}:{client_ip(request)}", limit)
                if wait:
                    return JSONResponse(
                        status_code=429,
                        content={"detail": f"Too many attempts. Try again in {wait} seconds"},
                        headers={"Retry-After": str(wait)},
                    )
        return await call_next(request)
