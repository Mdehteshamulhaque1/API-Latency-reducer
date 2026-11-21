"""
Pydantic schemas for the performance assistant, cache recommendations,
and the troubleshooting assistant.
"""
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.schemas.documents import SourceChunk


class AssistantAskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    hours: int = Field(default=24, gt=0, le=720)
    include_docs: bool = Field(default=True, description="Also search uploaded documentation")
    service: Optional[str] = Field(
        default=None, pattern=r"^[a-z0-9][a-z0-9-]{0,49}$",
        description="Answer about a monitored service's traffic (e.g. 'esone') instead of this gateway's",
    )


class AssistantAskResponse(BaseModel):
    question: str
    answer: Optional[str] = Field(description="Model narrative; None when the model was unavailable")
    llm_available: bool
    llm_error: Optional[str]
    tools_used: List[str]
    facts: Dict[str, Dict] = Field(description="Measured values the answer was built from, keyed by tool")
    sources: List[SourceChunk]
    grounding_score: float
    model: Optional[str]
    cached: bool
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float
    latency_ms: float
    guardrail_notes: List[str]


class SuggestedQuestions(BaseModel):
    questions: List[str]


class RecommendationItem(BaseModel):
    endpoint: str
    kind: str = Field(description="cache | tune | do_not_cache | keep")
    title: str
    reason: str
    suggested_ttl_seconds: Optional[Tuple[int, int]]
    evidence: Dict
    advisory: bool = True


class RecommendationResponse(BaseModel):
    hours: int
    analysed_endpoints: int
    recommendations: List[RecommendationItem]
    explanation: Optional[str]
    llm_available: bool
    note: str


class TroubleshootRequest(BaseModel):
    status_code: Optional[int] = Field(default=None, ge=400, le=599)
    endpoint: Optional[str] = Field(default=None, max_length=200)
    symptom: Optional[str] = Field(default=None, max_length=500)
    hours: int = Field(default=24, gt=0, le=720)
    service: Optional[str] = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{0,49}$")


class KnownCause(BaseModel):
    cause: str
    check: str


class TroubleshootResponse(BaseModel):
    status_code: Optional[int]
    endpoint: Optional[str]
    symptom: Optional[str]
    hours: int
    evidence: Dict[str, Dict]
    known_causes: List[KnownCause]
    sources: List[SourceChunk]
    explanation: Optional[str]
    llm_available: bool
    model: Optional[str]
    estimated_cost_usd: float
