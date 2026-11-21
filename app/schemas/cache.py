"""
Pydantic schemas for the cache management API.
"""
from typing import Optional

from pydantic import BaseModel, Field


class CacheStats(BaseModel):
    """Live cache statistics read from Redis."""

    available: bool = Field(description="False when Redis could not be reached")
    cache_hits: int
    cache_misses: int
    lookups: int
    cache_hit_rate: float = Field(description="Percentage of lookups served from cache")
    response_entries: int = Field(description="Cached HTTP responses currently stored")
    chat_entries: int = Field(description="Cached LLM responses currently stored")
    default_ttl_seconds: int
    enabled_rules: int
    total_rules: int


class CacheInvalidateRequest(BaseModel):
    """Which cached responses to drop."""

    endpoint_pattern: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Invalidate entries of one cache rule. Omit to invalidate all responses.",
    )
    include_chat: bool = Field(
        default=False,
        description="Also drop exact-match LLM responses",
    )


class CacheInvalidateResponse(BaseModel):
    scope: str
    deleted: int
