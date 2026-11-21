"""
Schemas for the question-answering endpoints (/api/v1/answers).

POST /answers            -> AnswerResponse
GET  /answers/recent     -> AnswerLogPage     (asked questions with their answers, paginated)
GET  /answers/top        -> TopQuestionsPage  (most asked questions in the window)
GET  /answers/stats      -> AnswerStats       (hit rate, latency, sources, cost)
GET  /answers/cache      -> CacheOverview     (what is in the shared cache right now)
GET  /answers/costs      -> CostAnalytics     (LLM vs embedding vs saved, tokens, calls avoided)
GET  /answers/users      -> UserQueryStatsPage (per end user / account aggregates)
"""
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

#: Opaque end-user reference a monitored service passes with a question
#: (for example ``esone:42``), so each of its users gets their own records
#: while the answer cache stays shared.
END_USER_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9:_.@-]{0,99}$"

CacheStatus = Literal["exact_hit", "semantic_hit", "miss", "bypassed"]
COST_NOTE = "Costs are estimates from the configured pricing tables, not provider billing."


class AnswerRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    user_ref: Optional[str] = Field(default=None, pattern=END_USER_PATTERN, description="End-user reference")
    #: Who the reference belongs to, shown in the admin user directory.
    user_name: Optional[str] = Field(default=None, max_length=100)
    user_email: Optional[str] = Field(default=None, max_length=255)


class AnswerSource(BaseModel):
    title: str
    url: str
    #: Provider the page came from: wikipedia | duckduckgo | wikidata | web
    source: Optional[str] = None


class AnswerResponse(BaseModel):
    question: str
    answer: str
    #: "cache" when a stored question matched, "model" when the model answered from its own
    #: knowledge, "crawler" when pages were read and the answer composed from them.
    answered_by: Literal["cache", "model", "crawler"]
    cached: bool
    #: exact_hit | semantic_hit | miss | bypassed (Redis unavailable: no lookup was possible)
    cache_status: CacheStatus = "miss"
    cache_id: Optional[str] = None
    #: Similarity to the matched stored question (1.0 for an exact match); None on a miss.
    similarity: Optional[float] = None
    matched_question: Optional[str] = None
    #: "exact", "embedding" or "lexical" on a cache hit.
    match_method: Optional[str] = None
    sources: List[AnswerSource] = Field(default_factory=list)
    latency_ms: float = Field(default=0.0, ge=0)
    crawl_ms: Optional[float] = None
    #: "knowledge" when the model answered by itself, "llm" when it wrote from the pages,
    #: "extract" when the best page's intro was used.
    compose_method: Optional[str] = None
    embedding_used: bool = False
    cache_lookup_ms: float = 0.0
    embedding_ms: float = 0.0
    embedding_tokens: int = 0
    #: True when the embedding provider reports no usage and the count is estimated from text length.
    embedding_tokens_estimated: bool = False
    llm_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    served_model: Optional[str] = None
    llm_cost_usd: float = 0.0
    embedding_cost_usd: float = 0.0
    #: Actual cost of this request (LLM + embedding), an estimate.
    total_cost_usd: float = 0.0
    #: Same as total_cost_usd, kept for older readers.
    estimated_cost_usd: float = 0.0
    #: On a cache hit: original generation cost minus this request's embedding cost (estimate).
    saved_cost_usd: float = 0.0
    billable_tokens: int = 0
    cost_inr: float = 0.0
    waited_for_generation: bool = False
    #: False when the question carried personal data: answered, but kept out of the shared cache.
    cacheable: bool = True


class AnswerLogItem(BaseModel):
    """One asked question and the answer it received (one row per caller, even on shared cache hits)."""

    id: int
    created_at: datetime
    user_id: Optional[int] = None
    end_user: Optional[str] = None
    correlation_id: Optional[str] = None
    question: str
    answer: str
    #: ok | error | blocked
    status: str = "ok"
    error_code: Optional[str] = None
    answered_by: str
    #: False when no source had anything: the fixed "could not find" reply was returned.
    found: bool = True
    cache_status: str = "miss"
    match_method: Optional[str] = None
    similarity: Optional[float] = None
    compose_method: Optional[str] = None
    #: Provider of the first source used (None for cache hits and not-found answers).
    primary_source: Optional[str] = None
    sources: List[AnswerSource] = Field(default_factory=list)
    cache_key: Optional[str] = None
    latency_ms: float = 0.0
    cache_lookup_ms: float = 0.0
    embedding_ms: float = 0.0
    crawl_ms: Optional[float] = None
    llm_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    embedding_tokens: int = 0
    total_tokens: int = 0
    llm_cost_usd: float = 0.0
    embedding_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    estimated_cost_usd: float = 0.0
    saved_cost_usd: float = 0.0
    billable_tokens: int = 0
    cost_inr: float = 0.0
    served_model: Optional[str] = None
    waited_for_generation: bool = False


class AnswerLogPage(BaseModel):
    hours: int
    scope: str = Field(description="'all' for admins, 'own' for other roles, 'service' for a monitored service")
    end_user: Optional[str] = None
    cache_status: Optional[str] = None
    #: Where the rows came from: the Redis list of the last hour, or the database.
    served_from: Literal["redis", "database"]
    offset: int = 0
    limit: int = 50
    total: int = 0
    items: List[AnswerLogItem] = Field(default_factory=list)


class TopQuestion(BaseModel):
    question: str
    question_hash: str
    asked: int
    cache_hits: int
    avg_latency_ms: float
    last_asked: datetime
    last_answer: str


class TopQuestionsPage(BaseModel):
    hours: int
    scope: str
    end_user: Optional[str] = None
    items: List[TopQuestion] = Field(default_factory=list)


class SourceCount(BaseModel):
    name: str
    count: int


class AnswerStats(BaseModel):
    """Totals over the window, aggregated from answer_logs."""

    hours: int
    scope: str
    end_user: Optional[str] = None
    questions: int
    unique_questions: int
    end_users: int = 0
    cache_hits: int
    exact_hits: int = 0
    semantic_hits: int = 0
    crawled: int
    not_found: int
    errors: int = 0
    blocked: int = 0
    bypassed: int = 0
    cache_hit_rate: float
    avg_latency_ms: float
    avg_latency_cached_ms: float
    avg_latency_crawled_ms: float
    avg_cache_lookup_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    embedding_tokens: int = 0
    llm_cost_usd: float = 0.0
    embedding_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    estimated_cost_usd: float = 0.0
    saved_cost_usd: float = 0.0
    cost_note: str = COST_NOTE
    cache_ttl_seconds: int
    recent_window_seconds: int
    by_source: List[SourceCount] = Field(default_factory=list)
    by_match: List[SourceCount] = Field(default_factory=list)
    by_model: List[SourceCount] = Field(default_factory=list)


class CacheOverview(BaseModel):
    """What the shared answer cache holds right now, plus how it performed in the window."""

    hours: int
    scope: str
    redis_available: bool
    active_entries: int
    stored_total: int = Field(description="Entries ever written (counter); expired is estimated as stored - active")
    expired_estimate: int
    bytes_used: int
    entries_scanned: int
    total_entry_hits: int
    oldest_entry_at: Optional[datetime] = None
    ttl_seconds: int
    volatile_ttl_seconds: int
    similarity_threshold: float
    expiry_policy: str = "sliding: every hit rewrites the entry with a fresh TTL"
    exact_hits: int
    semantic_hits: int
    misses: int
    bypassed: int
    cache_hit_rate: float
    avg_cache_lookup_ms: float
    avg_latency_hit_ms: float
    avg_latency_miss_ms: float


class CostAnalytics(BaseModel):
    """LLM versus embedding spend and what the cache saved, over the window."""

    hours: int
    scope: str
    end_user: Optional[str] = None
    currency: str
    pricing_effective_date: str
    cost_note: str = COST_NOTE
    llm_cost_usd: float
    embedding_cost_usd: float
    total_cost_usd: float
    saved_cost_usd: float
    prompt_tokens: int
    completion_tokens: int
    embedding_tokens: int
    total_tokens: int
    llm_calls_made: int
    llm_calls_avoided: int
    requests: int
    hits: int
    misses: int
    avg_cost_per_hit_usd: float
    avg_cost_per_miss_usd: float
    avg_latency_hit_ms: float
    avg_latency_miss_ms: float
    by_model: List[SourceCount] = Field(default_factory=list)


class UserQueryStats(BaseModel):
    """One caller's totals: an end user of a monitored service, or a gateway account."""

    user: str = Field(description="end-user reference (e.g. esone:42) or 'account:<id>'")
    user_id: Optional[int] = None
    end_user: Optional[str] = None
    queries: int
    exact_hits: int
    semantic_hits: int
    misses: int
    bypassed: int
    errors: int
    llm_calls: int
    total_tokens: int
    embedding_tokens: int
    total_cost_usd: float
    saved_cost_usd: float
    avg_latency_ms: float
    last_seen: datetime


class UserQueryStatsPage(BaseModel):
    hours: int
    scope: str
    offset: int
    limit: int
    total: int
    cost_note: str = COST_NOTE
    items: List[UserQueryStats] = Field(default_factory=list)
