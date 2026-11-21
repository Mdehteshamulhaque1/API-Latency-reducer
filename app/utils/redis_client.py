"""
Async Redis client wrapper: connection, JSON serialisation, error handling.

Every method logs and returns a neutral value on Redis errors so callers
can fail open; only ``eval`` re-raises, because the rate limiter needs to
know the difference between "blocked" and "could not check".
"""
import json
import logging
from typing import Any, Optional

import redis.asyncio as redis
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self):
        self.client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        try:
            self.client = redis.from_url(
                settings.redis_url,
                encoding="utf8",
                decode_responses=True,
                socket_connect_timeout=settings.redis_connect_timeout,
                socket_timeout=settings.redis_socket_timeout,
            )
            await self.client.ping()
            logger.info("Connected to Redis")
        except RedisError as exc:
            logger.error("Failed to connect to Redis: %s", exc)
            raise

    async def disconnect(self) -> None:
        if self.client:
            await self.client.aclose()
            logger.info("Disconnected from Redis")

    def _require(self) -> redis.Redis:
        if not self.client:
            raise RedisError("Redis client not initialized")
        return self.client

    async def get(self, key: str) -> Optional[Any]:
        """Get a value, decoding JSON when possible."""
        try:
            value = await self._require().get(key)
        except RedisError as exc:
            logger.error("Redis GET error for key %s: %s", key, exc)
            return None
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value with a TTL, serialising dicts and lists as JSON."""
        try:
            payload = json.dumps(value) if isinstance(value, (dict, list)) else value
            await self._require().setex(key, ttl or settings.redis_cache_ttl, payload)
            return True
        except RedisError as exc:
            logger.error("Redis SET error for key %s: %s", key, exc)
            return False

    async def delete(self, key: str) -> bool:
        try:
            return await self._require().delete(key) > 0
        except RedisError as exc:
            logger.error("Redis DELETE error for key %s: %s", key, exc)
            return False

    async def exists(self, key: str) -> bool:
        try:
            return await self._require().exists(key) > 0
        except RedisError as exc:
            logger.error("Redis EXISTS error for key %s: %s", key, exc)
            return False

    async def increment(self, key: str, amount: int = 1) -> int:
        try:
            return await self._require().incrby(key, amount)
        except RedisError as exc:
            logger.error("Redis INCREMENT error for key %s: %s", key, exc)
            return 0

    async def ping(self) -> bool:
        """True when Redis answers; False when it is down or not connected."""
        try:
            return bool(await self._require().ping())
        except RedisError:
            return False

    async def set_if_absent(self, key: str, value: Any, ttl: int) -> bool:
        """SET NX EX: True when this call created the key (a lock), False when it already existed or Redis failed."""
        try:
            payload = json.dumps(value) if isinstance(value, (dict, list)) else value
            return bool(await self._require().set(key, payload, nx=True, ex=ttl))
        except RedisError as exc:
            logger.error("Redis SET NX error for key %s: %s", key, exc)
            return False

    async def memory_usage(self, key: str) -> int:
        """Bytes Redis reports for a key (0 when unsupported or unavailable)."""
        try:
            value = await self._require().memory_usage(key)
            return int(value or 0)
        except RedisError:
            return 0

    async def ttl(self, key: str) -> int:
        """Seconds to live (-1 no expiry, -2 missing), or -2 when Redis is unavailable."""
        try:
            return int(await self._require().ttl(key))
        except RedisError:
            return -2

    async def push_capped(self, key: str, value: Any, max_len: int, ttl: int) -> bool:
        """Prepend ``value`` to a list, keep only the newest ``max_len`` items, refresh the TTL."""
        try:
            payload = json.dumps(value) if isinstance(value, (dict, list)) else value
            async with self._require().pipeline(transaction=True) as pipe:
                pipe.lpush(key, payload)
                pipe.ltrim(key, 0, max_len - 1)
                pipe.expire(key, ttl)
                await pipe.execute()
            return True
        except RedisError as exc:
            logger.error("Redis LPUSH error for key %s: %s", key, exc)
            return False

    async def list_range(self, key: str, start: int = 0, end: int = -1) -> list:
        """Items of a list (newest first for ``push_capped`` lists), JSON-decoded when possible."""
        try:
            raw = await self._require().lrange(key, start, end)
        except RedisError as exc:
            logger.error("Redis LRANGE error for key %s: %s", key, exc)
            return []
        items = []
        for value in raw:
            try:
                items.append(json.loads(value))
            except (json.JSONDecodeError, TypeError):
                items.append(value)
        return items

    async def scan_iter(self, pattern: str = "*", count: int = 100):
        """Iterate keys matching a pattern without blocking the server (SCAN, not KEYS)."""
        try:
            async for key in self._require().scan_iter(match=pattern, count=count):
                yield key
        except RedisError as exc:
            logger.error("Redis SCAN error for pattern %s: %s", pattern, exc)

    async def eval(self, script: str, keys: list, args: list):
        """Execute a Lua script atomically. Raises on failure."""
        return await self._require().eval(script, len(keys), *(keys + args))


# Global Redis client instance
redis_client = RedisClient()
