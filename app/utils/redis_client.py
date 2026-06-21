"""
Redis client wrapper for caching and session management.
"""
import json
import logging
from typing import Any, Optional

import redis.asyncio as redis
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Async Redis client wrapper.
    Handles connection, serialization, and error handling.
    """

    def __init__(self):
        self.client: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis."""
        try:
            self.client = await redis.from_url(
                settings.redis_url,
                encoding="utf8",
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            # Test connection
            await self.client.ping()
            logger.info("Connected to Redis")
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.client:
            await self.client.close()
            logger.info("Disconnected from Redis")

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        Automatically deserializes JSON values.
        """
        if not self.client:
            raise RedisError("Redis client not initialized")
        
        try:
            value = await self.client.get(key)
            if value is None:
                return None
            
            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except RedisError as e:
            logger.error(f"Redis GET error for key {key}: {str(e)}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache.
        Automatically serializes complex objects to JSON.
        """
        if not self.client:
            raise RedisError("Redis client not initialized")
        
        try:
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value)
            else:
                serialized_value = value
            
            # Use provided TTL or default
            ttl = ttl or settings.redis_cache_ttl
            
            await self.client.setex(key, ttl, serialized_value)
            return True
        except RedisError as e:
            logger.error(f"Redis SET error for key {key}: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.client:
            raise RedisError("Redis client not initialized")
        
        try:
            result = await self.client.delete(key)
            return result > 0
        except RedisError as e:
            logger.error(f"Redis DELETE error for key {key}: {str(e)}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.client:
            raise RedisError("Redis client not initialized")
        
        try:
            result = await self.client.exists(key)
            return result > 0
        except RedisError as e:
            logger.error(f"Redis EXISTS error for key {key}: {str(e)}")
            return False

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter value."""
        if not self.client:
            raise RedisError("Redis client not initialized")
        
        try:
            result = await self.client.incrby(key, amount)
            # Set TTL if it's a new key
            if result == amount:
                await self.client.expire(key, settings.rate_limit_default_period)
            return result
        except RedisError as e:
            logger.error(f"Redis INCREMENT error for key {key}: {str(e)}")
            return 0

    async def get_ttl(self, key: str) -> int:
        """Get TTL for key in seconds."""
        if not self.client:
            raise RedisError("Redis client not initialized")
        
        try:
            ttl = await self.client.ttl(key)
            return ttl
        except RedisError as e:
            logger.error(f"Redis TTL error for key {key}: {str(e)}")
            return -1

    async def flush_all(self):
        """Flush all data from Redis (use with caution)."""
        if not self.client:
            raise RedisError("Redis client not initialized")
        
        try:
            await self.client.flushall()
            logger.warning("Redis flushed all data")
        except RedisError as e:
            logger.error(f"Redis FLUSH error: {str(e)}")

    async def keys(self, pattern: str = "*"):
        """Get all keys matching pattern."""
        if not self.client:
            raise RedisError("Redis client not initialized")
        
        try:
            return await self.client.keys(pattern)
        except RedisError as e:
            logger.error(f"Redis KEYS error: {str(e)}")
            return []


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """Dependency to get Redis client."""
    return redis_client
