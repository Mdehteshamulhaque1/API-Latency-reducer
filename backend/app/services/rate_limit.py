"""
Rate limiting service using a token bucket algorithm.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.config import settings
from app.utils.redis_client import RedisClient

logger = logging.getLogger(__name__)


class RateLimitService:
    """
    Implements token bucket rate limiting.
    Supports per-user, per-IP, and API key limiters.
    """

    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        self.default_requests = settings.rate_limit_default_requests
        self.default_period = settings.rate_limit_default_period

    async def is_allowed(
        self,
        identifier: str,
        requests: Optional[int] = None,
        period: Optional[int] = None,
    ) -> bool:
        """Check if a request is allowed based on the token bucket state."""
        if not settings.rate_limit_enabled:
            return True

        requests = requests or self.default_requests
        period = period or self.default_period
        rate_key = f"rate_limit:{identifier}"
        now = datetime.now(timezone.utc).timestamp()
        refill_rate = requests / period if period > 0 else requests

        try:
            state = await self.redis.get(rate_key) or {}
            tokens = float(state.get("tokens", requests))
            updated_at = float(state.get("updated_at", now))

            elapsed = max(0.0, now - updated_at)
            tokens = min(requests, tokens + (elapsed * refill_rate))

            if tokens < 1:
                await self.redis.set(
                    rate_key,
                    {"tokens": tokens, "updated_at": now, "limit": requests, "period": period},
                    ttl=period,
                )
                logger.warning("Rate limit exceeded for %s", identifier)
                return False

            tokens -= 1
            await self.redis.set(
                rate_key,
                {"tokens": tokens, "updated_at": now, "limit": requests, "period": period},
                ttl=period,
            )
            return True
        except Exception as e:
            logger.error("Rate limit check error: %s", str(e))
            return True

    async def get_usage(self, identifier: str) -> dict:
        """Get current token bucket usage for an identifier."""
        try:
            rate_key = f"rate_limit:{identifier}"
            state = await self.redis.get(rate_key) or {}
            tokens = float(state.get("tokens", self.default_requests))
            limit = int(state.get("limit", self.default_requests))
            period = int(state.get("period", self.default_period))
            remaining = max(0, int(tokens))

            return {
                "current_requests": max(0, limit - remaining),
                "limit": limit,
                "remaining": remaining,
                "reset_in_seconds": period,
            }
        except Exception as e:
            logger.error("Rate limit get usage error: %s", str(e))
            return {"error": str(e)}

    async def reset_limit(self, identifier: str) -> bool:
        """Reset rate limit for an identifier."""
        try:
            rate_key = f"rate_limit:{identifier}"
            result = await self.redis.delete(rate_key)
            if result:
                logger.info("Reset rate limit for %s", identifier)
            return result
        except Exception as e:
            logger.error("Rate limit reset error: %s", str(e))
            return False
