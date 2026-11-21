"""
Rate limiting service using a token bucket algorithm backed by Redis.

How the token bucket works
--------------------------
Every identifier (an authenticated user, or a client IP for anonymous
traffic) owns a bucket that holds at most ``capacity`` tokens. The capacity
and refill period come from the caller's tier (``limits_for_role``):
anonymous, user, or privileged (operator and admin). Each request takes one
token. Tokens are refilled continuously at ``capacity / period``
tokens per second, so a client that stays quiet for a while builds up a
small burst allowance, while a client that hammers the API is slowed to the
average rate.

The bucket state lives in a single Redis key as a small JSON document
(``tokens`` and ``updated_at``). The read-modify-write is done inside a Lua
script, which Redis executes atomically, so two concurrent requests can never
both take the last token.

Failure policy
--------------
The limiter FAILS OPEN: if Redis is unreachable or the script errors, the
request is allowed. The API Optimizer prefers staying available over strict
enforcement; the decision is logged so an outage is visible.
"""
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.config import settings
from app.utils.redis_client import RedisClient

logger = logging.getLogger(__name__)

RATE_LIMIT_KEY_PREFIX = "rate_limit:"

TIER_ANONYMOUS = "anonymous"
TIER_USER = "user"
TIER_PRIVILEGED = "privileged"
PRIVILEGED_ROLES = {"admin", "operator"}


@dataclass(frozen=True)
class RateLimitTier:
    """Capacity and refill period for one class of caller."""

    name: str
    requests: int
    period: int
    applies_to: str

    @property
    def refill_per_second(self) -> float:
        return self.requests / self.period if self.period > 0 else float(self.requests)

    @property
    def policy(self) -> str:
        """IETF ``RateLimit-Policy`` value: ``<limit>;w=<window seconds>``."""
        return f"{self.requests};w={self.period}"


def tiers() -> list[RateLimitTier]:
    """Every tier, least to most generous, from settings."""
    return [
        RateLimitTier(
            TIER_ANONYMOUS,
            settings.rate_limit_anonymous_requests,
            settings.rate_limit_anonymous_period,
            "no token: keyed by client IP",
        ),
        RateLimitTier(
            TIER_USER,
            settings.rate_limit_user_requests,
            settings.rate_limit_user_period,
            "viewer and guest accounts: keyed by user id",
        ),
        RateLimitTier(
            TIER_PRIVILEGED,
            settings.rate_limit_privileged_requests,
            settings.rate_limit_privileged_period,
            "operator and admin accounts: keyed by user id",
        ),
    ]


def limits_for_role(role: Optional[str], authenticated: bool = True) -> RateLimitTier:
    """The tier a caller falls in: anonymous without a token, privileged for operator/admin, else user."""
    by_name = {tier.name: tier for tier in tiers()}
    if not authenticated:
        return by_name[TIER_ANONYMOUS]
    if role in PRIVILEGED_ROLES:
        return by_name[TIER_PRIVILEGED]
    return by_name[TIER_USER]


@dataclass(frozen=True)
class RateLimitDecision:
    """Outcome of one token-bucket check, used to build response headers."""

    allowed: bool
    limit: int
    remaining: int
    #: Seconds until the next token is available (meaningful when blocked).
    retry_after_seconds: int
    #: Seconds until the bucket is completely full again.
    reset_in_seconds: int
    #: True when Redis was unavailable and the request was let through.
    failed_open: bool = False
    #: Refill window in seconds, for the ``RateLimit-Policy`` header.
    period: int = 0
    tier: str = TIER_USER

    @property
    def policy(self) -> str:
        return f"{self.limit};w={self.period}"


class RateLimitService:
    """Token-bucket rate limiting keyed by user or client IP."""

    # Atomic token-bucket update.
    # Returns {allowed(0|1), tokens_after, seconds_until_next_token, seconds_until_full}
    _TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local ttl = tonumber(ARGV[4])

local state = redis.call('GET', key)
local tokens = capacity
local updated_at = now
if state then
  local decoded = cjson.decode(state)
  tokens = tonumber(decoded['tokens']) or capacity
  updated_at = tonumber(decoded['updated_at']) or now
end

local elapsed = math.max(0, now - updated_at)
tokens = math.min(capacity, tokens + elapsed * refill)

local allowed = 0
if tokens >= 1 then
  tokens = tokens - 1
  allowed = 1
end

redis.call('SET', key, cjson.encode({tokens = tokens, updated_at = now, limit = capacity, period = ttl}), 'EX', ttl)

local until_next = 0
if tokens < 1 and refill > 0 then
  until_next = (1 - tokens) / refill
end
local until_full = 0
if refill > 0 then
  until_full = (capacity - tokens) / refill
end
return {allowed, tostring(tokens), tostring(until_next), tostring(until_full)}
"""

    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        # Defaults when a caller does not pass a tier: the signed-in user tier.
        default = limits_for_role(None, authenticated=True)
        self.default_requests = default.requests
        self.default_period = default.period

    @staticmethod
    def bucket_key(identifier: str) -> str:
        return f"{RATE_LIMIT_KEY_PREFIX}{identifier}"

    async def check(
        self,
        identifier: str,
        requests: Optional[int] = None,
        period: Optional[int] = None,
        tier: str = TIER_USER,
    ) -> RateLimitDecision:
        """Take one token for ``identifier`` and report the bucket state."""
        requests = requests or self.default_requests
        period = period or self.default_period

        if not settings.rate_limit_enabled:
            return RateLimitDecision(
                allowed=True,
                limit=requests,
                remaining=requests,
                retry_after_seconds=0,
                reset_in_seconds=0,
                period=period,
                tier=tier,
            )

        now = datetime.now(timezone.utc).timestamp()
        refill_rate = requests / period if period > 0 else requests

        try:
            result = await self.redis.eval(
                self._TOKEN_BUCKET_LUA,
                keys=[self.bucket_key(identifier)],
                args=[requests, refill_rate, now, period],
            )
            allowed = int(result[0]) == 1
            tokens = float(result[1])
            until_next = float(result[2])
            until_full = float(result[3])
        except Exception as exc:
            # Fail open: availability beats strict enforcement when Redis is down.
            logger.error("Rate limit check failed open for %s: %s", identifier, exc)
            return RateLimitDecision(
                allowed=True,
                limit=requests,
                remaining=requests,
                retry_after_seconds=0,
                reset_in_seconds=0,
                failed_open=True,
                period=period,
                tier=tier,
            )

        if not allowed:
            logger.warning("Rate limit exceeded for %s (%s tier)", identifier, tier)

        return RateLimitDecision(
            allowed=allowed,
            limit=requests,
            remaining=max(0, int(math.floor(tokens))),
            retry_after_seconds=max(1, int(math.ceil(until_next))) if not allowed else 0,
            reset_in_seconds=int(math.ceil(until_full)),
            period=period,
            tier=tier,
        )

    async def is_allowed(
        self,
        identifier: str,
        requests: Optional[int] = None,
        period: Optional[int] = None,
    ) -> bool:
        """Boolean convenience wrapper around :meth:`check`."""
        decision = await self.check(identifier, requests=requests, period=period)
        return decision.allowed

    async def get_usage(
        self, identifier: str, requests: Optional[int] = None, period: Optional[int] = None
    ) -> dict:
        """Read the current bucket for an identifier without taking a token.

        ``requests`` and ``period`` describe the caller's tier and are used
        when the bucket does not exist yet.
        """
        rate_key = self.bucket_key(identifier)
        limit = requests or self.default_requests
        period = period or self.default_period
        try:
            state = await self.redis.get(rate_key) or {}
            if not isinstance(state, dict):
                state = {}
            limit = int(state.get("limit", limit))
            period = int(state.get("period", period))
            tokens = float(state.get("tokens", limit))
            updated_at = float(state.get("updated_at", 0.0))
            # Apply the refill that would happen on the next request, so the
            # dashboard shows the same number the limiter would use.
            refill_rate = limit / period if period > 0 else limit
            if updated_at:
                elapsed = max(0.0, datetime.now(timezone.utc).timestamp() - updated_at)
                tokens = min(float(limit), tokens + elapsed * refill_rate)
            remaining = max(0, int(math.floor(tokens)))
            reset_in = int(math.ceil((limit - tokens) / refill_rate)) if refill_rate > 0 else 0
            return {
                "identifier": identifier,
                "limit": limit,
                "period_seconds": period,
                "remaining": remaining,
                "used": max(0, limit - remaining),
                "reset_in_seconds": reset_in,
                "has_bucket": bool(state),
            }
        except Exception as exc:
            logger.error("Rate limit get usage error: %s", exc)
            return {
                "identifier": identifier,
                "limit": limit,
                "period_seconds": period,
                "remaining": limit,
                "used": 0,
                "reset_in_seconds": 0,
                "has_bucket": False,
                "error": "redis_unavailable",
            }

    async def reset_limit(self, identifier: str) -> bool:
        """Delete the bucket so the identifier starts full again."""
        try:
            result = await self.redis.delete(self.bucket_key(identifier))
            if result:
                logger.info("Reset rate limit for %s", identifier)
            return result
        except Exception as exc:
            logger.error("Rate limit reset error: %s", exc)
            return False
