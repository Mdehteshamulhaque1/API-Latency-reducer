"""
Pydantic schemas for analytics.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RecentRequest(BaseModel):
    """Snapshot of a recent API request."""

    model_config = ConfigDict(from_attributes=True)

    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    cache_hit: bool
    created_at: datetime
    service: str = "api-optimizer"
    direction: str = "inbound"
    upstream_host: Optional[str] = None


class MonitoredService(BaseModel):
    """One application whose requests are in ``api_logs`` for the window."""

    service: str
    is_self: bool
    requests: int
    inbound: int
    outbound: int
    errors: int
    avg_response_time_ms: float
    last_seen: Optional[datetime] = None
    # Gateway user account the service ships its rows with; its LLM calls
    # and guardrail events are attributed to this account.
    account_user_id: Optional[int] = None


class LatencyPoint(BaseModel):
    """Aggregated latency metric for a time bucket."""

    timestamp: str
    avg_response_time_ms: float
    request_count: int
    error_count: int


class LatencyDistributionPoint(LatencyPoint):
    """Latency percentiles for a time bucket."""

    p95_response_time_ms: float
    p99_response_time_ms: float


class SlowEndpointRankingItem(BaseModel):
    """Top slow endpoint ranking entry."""

    endpoint: str
    count: int
    avg_time: float
    p95_time: float
    p99_time: float
    errors: int
    cache_hit_rate: float
    error_rate: float


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
    """Everything the dashboard needs for one window. All values are measured
    from request rows; ``total_errors`` counts status >= 400 (including 429),
    ``rate_limited_requests`` counts status == 429 only."""

    total_requests: int
    total_errors: int
    rate_limited_requests: int = 0
    cache_hit_rate: float
    cache_miss_rate: float = 0.0
    avg_response_time_ms: float
    slowest_endpoint: Optional[str]
    slowest_response_time_ms: Optional[float]
    top_endpoints: List[dict]
    error_rate: float
    request_rate_per_minute: float = 0.0
    recent_requests: List[RecentRequest] = Field(default_factory=list)
    latency_series: List[LatencyPoint] = Field(default_factory=list)
    latency_distribution: List[LatencyDistributionPoint] = Field(default_factory=list)
    slow_endpoint_ranking: List[SlowEndpointRankingItem] = Field(default_factory=list)
    overall_p50_response_time_ms: float = 0.0
    overall_p95_response_time_ms: float = 0.0
    overall_p99_response_time_ms: float = 0.0
    slow_endpoints: List[dict] = Field(default_factory=list)
    optimization_suggestions: List[OptimizationSuggestion] = Field(default_factory=list)
    benchmark: Optional[BenchmarkReport] = None


class HealthCheckResponse(BaseModel):
    """Schema for health check response."""

    status: str
    version: str
    database: str
    redis: str
