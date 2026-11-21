"""
Pydantic schemas for the rate-limit API.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RateLimitTierInfo(BaseModel):
    """One class of caller and its bucket."""

    name: str = Field(description="anonymous | user | privileged")
    applies_to: str
    capacity: int
    period_seconds: int
    refill_per_second: float
    policy: str = Field(description="RateLimit-Policy value: <limit>;w=<window seconds>")


class RateLimitConfig(BaseModel):
    """Effective limiter configuration, read from settings.

    ``capacity`` and ``period_seconds`` describe the caller's own tier;
    ``tiers`` lists every tier.
    """

    enabled: bool
    algorithm: str = "token_bucket"
    your_tier: str
    capacity: int = Field(description="Bucket size for the caller's tier: max requests in a burst")
    period_seconds: int = Field(description="Seconds to refill an empty bucket")
    refill_per_second: float
    tiers: List[RateLimitTierInfo]
    identifier_strategy: str = "user id when authenticated, otherwise client IP; tier by role"
    failure_policy: str = "fail-open"
    headers: List[str] = Field(
        default=[
            "RateLimit-Limit",
            "RateLimit-Remaining",
            "RateLimit-Reset",
            "RateLimit-Policy",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "Retry-After (on 429)",
        ]
    )
    excluded_paths: List[str]


class RateLimitUsage(BaseModel):
    """Current bucket state for one identifier."""

    identifier: str
    tier: str = "user"
    limit: int
    period_seconds: int
    remaining: int
    used: int
    reset_in_seconds: int
    has_bucket: bool = Field(description="False when the identifier has not made a request yet")
    error: Optional[str] = None


class RateLimitEvent(BaseModel):
    """One rejected (HTTP 429) request from the request log."""

    id: int
    created_at: datetime
    method: str
    endpoint: str
    client_ip: str
    user_id: Optional[int]
    correlation_id: str


class RateLimitEventSummary(BaseModel):
    """Rejected requests over a window."""

    hours: int
    total_requests: int
    rate_limited_requests: int
    rate_limited_percent: float
    scope: str = Field(description="'all' for admins, otherwise 'own'")
    events: List[RateLimitEvent]
