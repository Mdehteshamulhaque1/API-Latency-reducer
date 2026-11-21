"""
Revoked-token denylist backed by Redis.

JWTs are stateless: once issued they are valid until they expire, and the
server keeps no record of them. To support logout we give every token a
unique id (the ``jti`` claim) and, on logout, store that id in Redis until
the token would have expired anyway. Auth checks consult the list; a match
means the token was revoked.

Why a denylist and not an allowlist: only revoked tokens need storage, so
the list stays tiny and entries expire on their own.

Failure policy: FAIL OPEN. If Redis is unavailable the token is treated as
valid, keeping the API usable during a cache outage. The trade-off is that a
revoked token could still be accepted for its remaining lifetime (at most
ACCESS_TOKEN_EXPIRE_MINUTES for access tokens) while Redis is down.
"""
import logging
import time
from typing import Optional

from app.utils.redis_client import RedisClient, redis_client

logger = logging.getLogger(__name__)

DENYLIST_PREFIX = "auth:revoked:"


class TokenDenylist:
    """Store and query revoked JWT ids."""

    def __init__(self, client: Optional[RedisClient] = None):
        self.redis = client or redis_client

    @staticmethod
    def _key(jti: str) -> str:
        return f"{DENYLIST_PREFIX}{jti}"

    async def revoke(self, jti: str, expires_at: Optional[int]) -> bool:
        """Revoke a token id until ``expires_at`` (unix seconds)."""
        ttl = int(expires_at - time.time()) if expires_at else 0
        if ttl <= 0:
            # Already expired: nothing to remember.
            return True
        try:
            await self.redis.set(self._key(jti), "1", ttl=ttl)
            return True
        except Exception as exc:
            logger.error("Failed to revoke token %s: %s", jti[:8], exc)
            return False

    async def is_revoked(self, jti: Optional[str]) -> bool:
        """True when the id was revoked. Returns False if Redis is unavailable."""
        if not jti:
            return False
        try:
            if self.redis.client is None:
                return False
            return await self.redis.exists(self._key(jti))
        except Exception as exc:
            logger.warning("Denylist check failed open for %s: %s", jti[:8], exc)
            return False
