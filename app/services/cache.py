"""
Caching service for intelligent cache management.
"""
import hashlib
import json
import logging
from typing import Any, Dict, Iterable, Optional

from app.core.constants import CACHE_KEY_RULE_PREFIX, CACHE_TTL_DEFAULT
from app.utils.redis_client import RedisClient

logger = logging.getLogger(__name__)

CACHE_HITS_KEY = "cache:stats:hits"
CACHE_MISSES_KEY = "cache:stats:misses"


class CacheService:
    """
    Manages intelligent caching with TTL, conditional caching, and statistics.
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
            ttl = ttl or CACHE_TTL_DEFAULT
            await self.redis.set(key, value, ttl=ttl)
            logger.debug("Cached value for key: %s with TTL: %ss", key, ttl)
            return True
        except Exception as e:
            logger.error("Cache set error: %s", str(e))
            return False

    async def warm_cache(self, entries: Iterable[dict[str, Any]]) -> int:
        """Warm a collection of cache entries in the background."""
        warmed = 0
        for entry in entries:
            if await self.set(
                entry["key"],
                entry["value"],
                ttl=entry.get("ttl"),
            ):
                warmed += 1
        return warmed

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
        """Invalidate all cache keys matching a pattern."""
        try:
            keys = await self.redis.keys(pattern)
            if not keys:
                return 0

            deleted_count = 0
            for key in keys:
                if await self.redis.delete(key):
                    deleted_count += 1

            logger.info("Invalidated %s cache keys matching pattern: %s", deleted_count, pattern)
            return deleted_count
        except Exception as e:
            logger.error("Cache invalidation error: %s", str(e))
            return 0

    async def invalidate_route(self, endpoint_pattern: str) -> int:
        """Invalidate route-wise cache entries using the shared prefix."""
        return await self.invalidate_pattern(f"{CACHE_KEY_RULE_PREFIX}{endpoint_pattern}*")

    async def clear_cache(self) -> bool:
        """Clear all cache (use with caution)."""
        try:
            await self.redis.flush_all()
            logger.warning("All cache cleared")
            return True
        except Exception as e:
            logger.error("Cache clear error: %s", str(e))
            return False

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            keys = await self.redis.keys("*")
            hits = await self.redis.get(CACHE_HITS_KEY) or 0
            misses = await self.redis.get(CACHE_MISSES_KEY) or 0
            hit_count = int(hits)
            miss_count = int(misses)
            request_count = hit_count + miss_count

            return {
                "total_cached_keys": len(keys) if keys else 0,
                "cache_size_estimated": len(str(keys)),
                "cache_hits": hit_count,
                "cache_misses": miss_count,
                "cache_hit_rate": round((hit_count / request_count) * 100, 2) if request_count else 0.0,
            }
        except Exception as e:
            logger.error("Cache stats error: %s", str(e))
            return {"error": str(e)}
