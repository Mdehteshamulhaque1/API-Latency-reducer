"""
Pydantic schemas for the guardrails audit API.
"""
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class GuardrailSummary(BaseModel):
    hours: int
    scope: str = Field(description="'all' for admins, otherwise 'own'")
    total_events: int
    blocked_requests: int
    high_severity: int
    by_category: Dict[str, int]
    by_feature: Dict[str, int]
    injection_blocking_enabled: bool
    pii_masking_enabled: bool
    note: str = (
        "Detection is heuristic: it records what the rules caught and cannot "
        "guarantee that every injection or every piece of PII was found."
    )


class GuardrailEventItem(BaseModel):
    id: int
    created_at: datetime
    user_id: Optional[int]
    correlation_id: Optional[str]
    category: str
    severity: str
    feature: str
    detail: str
    blocked: bool


class GuardrailEventPage(BaseModel):
    hours: int
    scope: str
    items: List[GuardrailEventItem]


class GuardrailCheckRequest(BaseModel):
    """Dry-run the input screen on a piece of text (nothing is sent to a model)."""

    text: str = Field(..., min_length=1, max_length=32000)


class GuardrailCheckResponse(BaseModel):
    injection_severity: str
    injection_rules: List[str]
    would_block: bool
    pii_counts: Dict[str, int]
    masked_text: str
