"""
Database models for the application.

Only tables that the application actually reads or writes live here:

- users          -> authentication and role-based access control
- cache_rules    -> which endpoints the CacheMiddleware may cache, and how
- api_logs       -> one row per HTTP request, written by MetricsMiddleware for
                    this service and by POST /ingest/requests for monitored
                    services (e.g. Esone); every analytics number is
                    aggregated from here. ``service`` names the application
                    the row belongs to, ``direction`` is "inbound" (a request
                    it served) or "outbound" (a call it made to another host).
- ai_request_logs -> one row per LLM call: tokens, latency, estimated cost, outcome
- end_users      -> people using a monitored service (e.g. Esone), by reference
- answer_logs    -> one row per answered question (POST /api/v1/answers): the
                    question, its answer, cache or crawler, sources, latency
- guardrail_events -> what the AI guardrails caught (never the text itself)
- documents / document_chunks -> knowledge-base files and their retrievable pieces

Schema changes are managed with Alembic (see alembic/versions/).
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import BaseModel
from app.core.constants import DIRECTION_INBOUND, SELF_SERVICE, UserRole


class User(BaseModel):
    """User model for authentication and authorization."""
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.VIEWER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index("idx_user_email", "email"),
        Index("idx_user_active", "is_active"),
    )

    def to_dict(self):
        """Convert to dictionary, excluding password."""
        data = super().to_dict()
        data.pop("hashed_password", None)
        return data


class CacheRule(BaseModel):
    """Cache rules configuration for different endpoints."""
    __tablename__ = "cache_rules"

    endpoint_pattern: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    ttl: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)  # seconds
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Conditional caching: which request attributes become part of the cache key
    cache_by_user: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cache_by_query_params: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cache_by_headers: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Largest response body (in KB) that will be stored for this rule
    max_cache_size: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_cache_rule_endpoint", "endpoint_pattern"),
        Index("idx_cache_rule_enabled", "enabled"),
    )


class APILog(BaseModel):
    """Detailed logs for each API request."""
    __tablename__ = "api_logs"

    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    # Which application the request belongs to and whether it served the
    # request ("inbound") or made it ("outbound"). Rows written by this
    # service's own middleware use SELF_SERVICE / inbound.
    service: Mapped[str] = mapped_column(
        String(50), nullable=False, default=SELF_SERVICE, server_default=SELF_SERVICE, index=True
    )
    direction: Mapped[str] = mapped_column(
        String(10), nullable=False, default=DIRECTION_INBOUND, server_default=DIRECTION_INBOUND
    )
    # Host that an outbound call was made to (None for inbound rows).
    upstream_host: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Person a monitored service made the request for ("esone:7"); None when
    # nobody was signed in, and for this gateway's own rows.
    end_user: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    method: Mapped[str] = mapped_column(String(10), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)

    # Response details
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    response_time_ms: Mapped[float] = mapped_column(Float, nullable=False)

    # Cache details
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cache_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Request details
    client_ip: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    correlation_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    request_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    response_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    query_params: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_api_log_user", "user_id"),
        Index("idx_api_log_endpoint", "endpoint"),
        Index("idx_api_log_status", "status_code"),
        Index("idx_api_log_created", "created_at"),
        Index("idx_api_log_correlation", "correlation_id"),
        Index("idx_api_log_service_created", "service", "created_at"),
        Index("idx_api_log_end_user_created", "end_user", "created_at"),
    )


class AIRequestLog(BaseModel):
    """One row per LLM call made through the gateway.

    Token counts come straight from the provider's ``usage`` block and are
    zero when the provider omits them. ``estimated_cost_usd`` is derived from
    the configured pricing table and is an estimate, never a bill. No prompt
    or completion text is stored here.
    """
    __tablename__ = "ai_request_logs"

    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    # Which feature made the call: "chat" (gateway), later "assistant", "rag".
    feature: Mapped[str] = mapped_column(String(30), nullable=False, default="chat")
    provider: Mapped[str] = mapped_column(String(30), nullable=False, default="openai")
    requested_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    served_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # "success" | "cache_hit" | "error"
    outcome: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Short machine-readable reason on errors (e.g. "timeout", "circuit_open").
    error_code: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)

    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    __table_args__ = (
        Index("idx_ai_log_created", "created_at"),
        Index("idx_ai_log_user_created", "user_id", "created_at"),
    )


class AnswerLog(BaseModel):
    """One asked question (POST /api/v1/answers) and the answer it received.

    Unlike ``ai_request_logs`` this table does hold the question and answer
    text: the dashboard shows what was asked, what was answered, and whether
    the semantic cache or the crawler produced it. ``question_hash`` groups
    re-asked questions for the most-asked ranking; ``sources`` is a JSON list
    of ``{title, url, source}``.
    """
    __tablename__ = "answer_logs"

    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    # End user of a monitored service (e.g. "esone:42"): the service's own
    # users get separate records while sharing the gateway account above.
    end_user: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    # ok | error | blocked
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="ok", server_default="ok")
    error_code: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    # exact_hit | semantic_hit | miss | bypassed (Redis unavailable, no lookup possible)
    cache_status: Mapped[str] = mapped_column(String(12), nullable=False, default="miss", server_default="miss")

    question: Mapped[str] = mapped_column(Text, nullable=False)
    question_hash: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    # "cache" | "crawler"
    answered_by: Mapped[str] = mapped_column(String(10), nullable=False)
    # False when nothing was found and the fixed "could not find" reply was returned.
    found: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    # exact | embedding | lexical (cache hits only)
    match_method: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    similarity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # llm | extract (crawler answers only)
    compose_method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    # Provider of the first source: wikipedia | duckduckgo | wikidata | web
    primary_source: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    sources: Mapped[str] = mapped_column(Text, nullable=False, default="[]", server_default="[]")
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    # Redis key of the shared cache entry that served (hit) or stored (miss) the answer.
    cache_key: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    cache_lookup_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    crawl_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    llm_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    embedding_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    # Tokens of THIS request: prompt/completion only when a model generated, embedding when the question was embedded.
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    embedding_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    # Costs of THIS request (estimates from the pricing tables). A cache hit has llm_cost 0.
    llm_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    embedding_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    total_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    # Kept equal to total_cost_usd for older readers.
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    # On a hit: the entry's original generation cost minus this request's embedding cost (estimate).
    saved_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    billable_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    cost_inr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    served_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    waited_for_generation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")

    __table_args__ = (
        Index("idx_answer_log_created", "created_at"),
        Index("idx_answer_log_user_created", "user_id", "created_at"),
        Index("idx_answer_log_hash_created", "question_hash", "created_at"),
        Index("idx_answer_log_end_user_created", "end_user", "created_at"),
        Index("idx_answer_log_cache_status_created", "cache_status", "created_at"),
    )


class EndUser(BaseModel):
    """A person using a monitored service, known by the reference that service sends.

    ``ref`` is opaque (for example ``esone:7``). The display name and email are
    what the service passed with the person's questions, so the admin user
    directory can show who a reference belongs to.
    """
    __tablename__ = "end_users"

    ref: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    service: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class GuardrailEvent(BaseModel):
    """Security audit trail for the AI features.

    Records that a guardrail fired and why, never the text it fired on.
    """
    __tablename__ = "guardrail_events"

    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    # injection_detected | injection_blocked | pii_masked | output_invalid |
    # low_grounding | retrieval_failed | ai_request_failed | document_flagged |
    # upload_rejected
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    # low | medium | high
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="low")
    # chat | assistant | rag | documents
    feature: Mapped[str] = mapped_column(String(30), nullable=False, default="chat")
    # Short, non-sensitive explanation: rule names, counts, reason codes.
    detail: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index("idx_guardrail_created", "created_at"),
        Index("idx_guardrail_category_created", "category", "created_at"),
    )


class Document(BaseModel):
    """An uploaded knowledge-base file (PDF, TXT, or Markdown)."""
    __tablename__ = "documents"

    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    # SHA-256 of the raw upload; duplicate uploads are rejected by this.
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    # pending | ready | failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    character_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Set when the injection scanner found instruction-like text inside the file.
    flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    flag_detail: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)


class DocumentChunk(BaseModel):
    """One retrievable slice of a document. The vector lives in ChromaDB."""
    __tablename__ = "document_chunks"

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    character_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Id of the embedding in the vector store ("<document_id>:<position>").
    vector_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    __table_args__ = (
        Index("idx_chunk_document_position", "document_id", "position"),
    )
