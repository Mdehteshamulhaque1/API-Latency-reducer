"""Request and response schemas."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from esone_api.models import Role

USERNAME_MIN, USERNAME_MAX = 3, 100
PASSWORD_MIN, PASSWORD_MAX = 8, 100


class UserCreate(BaseModel):
    username: str = Field(..., min_length=USERNAME_MIN, max_length=USERNAME_MAX)
    email: EmailStr
    password: str = Field(..., min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)

    @field_validator("username")
    @classmethod
    def _clean_username(cls, value: str) -> str:
        value = value.strip()
        if not value.replace("-", "").replace("_", "").replace(".", "").isalnum():
            raise ValueError("Username may contain letters, digits, '-', '_' and '.' only")
        return value


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefresh(BaseModel):
    refresh_token: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)


class AdminUserUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    limit: int
    offset: int


class HealthResponse(BaseModel):
    status: str
    database: str
    version: str


# ----- chat (mirrors the API Optimizer's app/schemas/answers.py) -----


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)


class AnswerSource(BaseModel):
    title: str
    url: str
    # Provider the page came from (wikipedia, duckduckgo, wikidata, web); older rows have none.
    source: str | None = None


class AnswerResponse(BaseModel):
    """The Optimizer's answer, passed through so the chat can show where it came from."""

    model_config = ConfigDict(extra="ignore")

    question: str
    answer: str
    answered_by: Literal["cache", "model", "crawler"]
    cached: bool
    similarity: float | None = None
    matched_question: str | None = None
    match_method: str | None = None
    sources: list[AnswerSource] = Field(default_factory=list)
    latency_ms: float = 0.0
    crawl_ms: float | None = None
    compose_method: str | None = None
    embedding_used: bool = False
    cache_lookup_ms: float = 0.0
    llm_ms: float = 0.0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    served_model: str | None = None
    cacheable: bool = True
    # Cost accounting from the Optimizer (estimates, never billing).
    cache_status: str = "miss"
    cache_id: str | None = None
    embedding_ms: float = 0.0
    embedding_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    llm_cost_usd: float = 0.0
    embedding_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    saved_cost_usd: float = 0.0
    waited_for_generation: bool = False
    # What this user is charged (INR): tokens of an answer not served from the cache.
    billable_tokens: int = 0
    cost_inr: float = 0.0


class ChatStatus(BaseModel):
    configured: bool


class ChatHistoryItem(BaseModel):
    """One request of the signed-in user: the question, the answer (or error) and how it was produced."""

    id: int
    created_at: datetime
    question: str
    answer: str
    # ok | error
    status: str = "ok"
    error_message: str | None = None
    answered_by: Literal["cache", "model", "crawler"]
    cached: bool
    # exact | semantic | miss | none
    cache_type: str = "miss"
    match_method: str | None = None
    similarity: float | None = None
    compose_method: str | None = None
    sources: list[AnswerSource] = Field(default_factory=list)
    sources_count: int = 0
    latency_ms: float = 0.0
    cache_lookup_ms: float = 0.0
    crawl_ms: float | None = None
    llm_ms: float = 0.0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    served_model: str | None = None
    correlation_id: str | None = None
    cache_status: str = "miss"
    embedding_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    llm_cost_usd: float = 0.0
    embedding_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    saved_cost_usd: float = 0.0
    billable_tokens: int = 0
    cost_inr: float = 0.0


class NameCount(BaseModel):
    name: str
    count: int


class ChatLatencyPoint(BaseModel):
    at: datetime
    latency_ms: float
    cached: bool


class ChatStats(BaseModel):
    """The signed-in user's own chat activity over a window."""

    hours: int
    total_queries: int
    answered: int
    errors: int
    cache_hits: int
    exact_hits: int
    semantic_hits: int
    misses: int
    cache_hit_rate: float
    avg_latency_ms: float
    avg_latency_cached_ms: float
    avg_latency_crawled_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    total_tokens: int
    estimated_cost_usd: float
    embedding_tokens: int = 0
    llm_cost_usd: float = 0.0
    embedding_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    saved_cost_usd: float = 0.0
    billable_tokens: int = 0
    cost_inr: float = 0.0
    bypassed: int = 0
    sources_used: int
    by_source: list[NameCount] = Field(default_factory=list)
    by_model: list[NameCount] = Field(default_factory=list)
    by_error: list[NameCount] = Field(default_factory=list)
    latency_series: list[ChatLatencyPoint] = Field(default_factory=list)
    recent: list[ChatHistoryItem] = Field(default_factory=list)
    recent_errors: list[ChatHistoryItem] = Field(default_factory=list)


class ChatHistory(BaseModel):
    items: list[ChatHistoryItem] = Field(default_factory=list)
    total: int = 0


class ChatHistoryCleared(BaseModel):
    deleted: int
