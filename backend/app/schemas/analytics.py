"""
Pydantic schemas for analytics.
"""
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class APILogResponse(BaseModel):
    """Schema for API log response."""

    id: int
    user_id: Optional[int]
    method: str
    endpoint: str
    status_code: int
    response_time_ms: float
    cache_hit: bool
    client_ip: str
    correlation_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class AnalyticsResponse(BaseModel):
    """Schema for analytics data."""

    id: int
    total_requests: int
    total_errors: int
    cache_hits: int
    cache_misses: int
    avg_response_time_ms: float
    cache_hit_rate: float
    created_at: datetime

    class Config:
        from_attributes = True


class RecentRequest(BaseModel):
    """Snapshot of a recent API request."""

    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    cache_hit: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LatencyPoint(BaseModel):
    """Aggregated latency metric for a time bucket."""

    timestamp: str
    avg_response_time_ms: float
    request_count: int
    error_count: int


class OptimizationSuggestion(BaseModel):
    """Actionable recommendation generated from request patterns."""

    title: str
    severity: str = Field(pattern="^(low|medium|high)$")
    endpoint: Optional[str] = None
    reason: str
    action: str


class BenchmarkReport(BaseModel):
    """Simple before/after benchmark comparison."""

    baseline_avg_response_time_ms: float
    optimized_avg_response_time_ms: float
    improvement_percent: float
    sample_size: int
    before_window: str
    after_window: str


class AnalyticsSummary(BaseModel):
    """Schema for analytics summary."""

    total_requests: int
    total_errors: int
    cache_hit_rate: float
    avg_response_time_ms: float
    slowest_endpoint: Optional[str]
    slowest_response_time_ms: Optional[float]
    top_endpoints: List[dict]
    error_rate: float
    request_rate_per_minute: float = 0.0
    cache_miss_rate: float = 0.0
    recent_requests: List[RecentRequest] = Field(default_factory=list)
    latency_series: List[LatencyPoint] = Field(default_factory=list)
    slow_endpoints: List[dict] = Field(default_factory=list)
    optimization_suggestions: List[OptimizationSuggestion] = Field(default_factory=list)
    benchmark: Optional[BenchmarkReport] = None


class HealthCheckResponse(BaseModel):
    """Schema for health check response."""

    status: str
    version: str
    database: str
    redis: str
