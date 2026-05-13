"""
Pydantic schemas for cache rules.
"""
from typing import Optional
from pydantic import BaseModel, Field


class CacheRuleBase(BaseModel):
    """Base cache rule schema."""
    endpoint_pattern: str = Field(..., min_length=1, max_length=255)
    ttl: int = Field(default=3600, ge=0)
    enabled: bool = True
    cache_by_user: bool = False
    cache_by_query_params: bool = False
    cache_by_headers: bool = False
    max_cache_size: int = Field(default=1000, ge=100)
    priority: int = Field(default=0, ge=0)
    description: Optional[str] = None


class CacheRuleCreate(CacheRuleBase):
    """Schema for creating cache rule."""
    pass


class CacheRuleUpdate(BaseModel):
    """Schema for updating cache rule."""
    ttl: Optional[int] = None
    enabled: Optional[bool] = None
    cache_by_user: Optional[bool] = None
    cache_by_query_params: Optional[bool] = None
    cache_by_headers: Optional[bool] = None
    max_cache_size: Optional[int] = None
    priority: Optional[int] = None
    description: Optional[str] = None


class CacheRuleResponse(CacheRuleBase):
    """Schema for cache rule response."""
    id: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
