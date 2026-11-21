"""
Pydantic schemas for AI usage, token, and cost monitoring.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AIModelUsage(BaseModel):
    """Usage rolled up per served model."""

    served_model: str
    requests: int
    successes: int
    cache_hits: int
    errors: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    avg_latency_ms: float
    estimated_cost_usd: float


class AIUsagePoint(BaseModel):
    """Usage per time bucket."""

    timestamp: str
    requests: int
    errors: int
    total_tokens: int
    estimated_cost_usd: float


class AIRequestLogItem(BaseModel):
    """One recorded LLM call (no prompt text is stored)."""

    id: int
    created_at: datetime
    user_id: Optional[int]
    correlation_id: Optional[str]
    feature: str
    provider: str
    requested_model: Optional[str]
    served_model: Optional[str]
    outcome: str
    fallback_used: bool
    error_code: Optional[str]
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    estimated_cost_usd: float


class AIUsageSummary(BaseModel):
    """Totals over a window. Costs are estimates derived from PRICING_TABLE."""

    hours: int
    scope: str = Field(description="'all' for admins, otherwise 'own'")
    requests: int
    successes: int
    cache_hits: int
    errors: int
    fallbacks: int
    error_rate: float
    cache_hit_rate: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    avg_latency_ms: float
    estimated_cost_usd: float
    cost_is_estimate: bool = True
    pricing_source: str = "PRICING_TABLE (USD per 1M tokens)"
    by_model: List[AIModelUsage] = Field(default_factory=list)
    series: List[AIUsagePoint] = Field(default_factory=list)


class AIRequestLogPage(BaseModel):
    hours: int
    scope: str
    items: List[AIRequestLogItem]
