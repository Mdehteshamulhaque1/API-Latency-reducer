"""
Caching service: key generation, reads/writes with TTL, invalidation, stats.

Key layout in Redis
-------------------
``rule:<endpoint_pattern>:<path>[:user:<id>][:params:<md5>][:headers:<md5>]``
    One entry per cached HTTP response, written by CacheMiddleware.
``chat:<sha256>``
    Exact-match LLM responses, written by ChatService.
``cache:stats:hits`` / ``cache:stats:misses``
    Process-wide counters, incremented on every cache lookup.

Invalidation strategy
---------------------
* Time based: every entry carries a TTL from its cache rule, so stale data
  expires on its own. This is the primary mechanism.
* Explicit: ``invalidate_route`` deletes every entry for one rule pattern
  (after a deploy, or when an operator knows the upstream data changed), and
  ``invalidate_all`` clears every response entry. Both use SCAN so they never
  block Redis the way KEYS or FLUSHALL would, and they never touch rate-limit
  buckets or the token denylist that share the same Redis database.
"""
import hashlib
import json
import logging
from typing import Any, Dict, Optional

from app.core.constants import CACHE_KEY_CHAT_PREFIX, CACHE_KEY_RULE_PREFIX, CACHE_TTL_DEFAULT
from app.utils.redis_client import RedisClient

logger = logging.getLogger(__name__)

CACHE_HITS_KEY = "cache:stats:hits"
CACHE_MISSES_KEY = "cache:stats:misses"


class CacheService:
    """
    Manages response caching with TTL, conditional keys, and statistics.
    """

    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client

    def _generate_cache_key(
        self,
        endpoint: str,
        cache_by_user: bool = False,
        cache_by_params: bool = False,
        cache_by_headers: bool = False,
        user_id: Optional[int] = None,
        query_params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> str:
        """Generate cache key based on endpoint and conditional parameters."""
        key_parts = [endpoint]

        if cache_by_user and user_id:
            key_parts.append(f"user:{user_id}")

        if cache_by_params and query_params:
            params_hash = hashlib.md5(
                json.dumps(query_params, sort_keys=True).encode()
            ).hexdigest()
            key_parts.append(f"params:{params_hash}")

        if cache_by_headers and headers:
            headers_hash = hashlib.md5(
                json.dumps(headers, sort_keys=True).encode()
            ).hexdigest()
            key_parts.append(f"headers:{headers_hash}")

        return ":".join(key_parts)

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve cached value and track hit statistics."""
        try:
            value = await self.redis.get(key)
            if value is not None:
                await self.record_hit()
                logger.debug("Cache hit for key: %s", key)
            else:
                await self.record_miss()
            return value
        except Exception as e:
            logger.error("Cache get error: %s", str(e))
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Store value in cache."""
        try:
            # Redis rejects non-positive TTLs; clamp them to the default rather
            # than letting a misconfigured rule break caching.
            ttl = ttl if ttl is not None and ttl > 0 else CACHE_TTL_DEFAULT
            await self.redis.set(key, value, ttl=ttl)
            logger.debug("Cached value for key: %s with TTL: %ss", key, ttl)
            return True
        except Exception as e:
            logger.error("Cache set error: %s", str(e))
            return False

    async def record_hit(self) -> None:
        """Record a cache hit."""
        try:
            await self.redis.increment(CACHE_HITS_KEY, 1)
        except Exception as e:
            logger.debug("Unable to record cache hit: %s", e)

    async def record_miss(self) -> None:
        """Record a cache miss."""
        try:
            await self.redis.increment(CACHE_MISSES_KEY, 1)
        except Exception as e:
            logger.debug("Unable to record cache miss: %s", e)

    async def delete(self, key: str) -> bool:
        """Delete cached value."""
        try:
            result = await self.redis.delete(key)
            if result:
                logger.debug("Deleted cache for key: %s", key)
            return result
        except Exception as e:
            logger.error("Cache delete error: %s", str(e))
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all cache keys matching a pattern.

        Uses SCAN instead of KEYS so invalidation never blocks Redis on large
        key sets.
        """
        try:
            deleted_count = 0
            async for key in self.redis.scan_iter(pattern, count=200):
                if await self.redis.delete(key):
                    deleted_count += 1

            logger.info("Invalidated %s cache keys matching pattern: %s", deleted_count, pattern)
            return deleted_count
        except Exception as e:
            logger.error("Cache invalidation error: %s", str(e))
            return 0

    async def invalidate_route(self, endpoint_pattern: str) -> int:
        """Invalidate every cached response produced by one cache rule."""
        return await self.invalidate_pattern(f"{CACHE_KEY_RULE_PREFIX}{endpoint_pattern}:*")

    async def invalidate_all(self) -> int:
        """Invalidate every cached HTTP response (rule entries only).

        Rate-limit buckets, the LLM cache, and the token denylist are left
        intact; this is deliberately NOT a FLUSHALL.
        """
        return await self.invalidate_pattern(f"{CACHE_KEY_RULE_PREFIX}*")

    async def invalidate_chat(self) -> int:
        """Invalidate every exact-match LLM response."""
        return await self.invalidate_pattern(f"{CACHE_KEY_CHAT_PREFIX}*")

    async def _count_keys(self, pattern: str) -> int:
        count = 0
        async for _ in self.redis.scan_iter(pattern, count=500):
            count += 1
        return count

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Cache counters plus live key counts, gathered with SCAN."""
        try:
            hits_raw = await self.redis.get(CACHE_HITS_KEY)
            misses_raw = await self.redis.get(CACHE_MISSES_KEY)
            hit_count = int(hits_raw or 0)
            miss_count = int(misses_raw or 0)
            lookups = hit_count + miss_count

            response_entries = await self._count_keys(f"{CACHE_KEY_RULE_PREFIX}*")
            chat_entries = await self._count_keys(f"{CACHE_KEY_CHAT_PREFIX}*")

            return {
                "available": True,
                "cache_hits": hit_count,
                "cache_misses": miss_count,
                "lookups": lookups,
                "cache_hit_rate": round((hit_count / lookups) * 100, 2) if lookups else 0.0,
                "response_entries": response_entries,
                "chat_entries": chat_entries,
            }
        except Exception as e:
            logger.error("Cache stats error: %s", str(e))
            return {
                "available": False,
                "cache_hits": 0,
                "cache_misses": 0,
                "lookups": 0,
                "cache_hit_rate": 0.0,
                "response_entries": 0,
                "chat_entries": 0,
            }
