"""Database models."""
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from esone_api.database import Base


class Role(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default=Role.VIEWER.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    """One row per issued refresh token, keyed by the token's jti claim."""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="refresh_tokens")


class ChatMessage(Base):
    """One request a user made in the chat: the question, the answer the
    Optimizer gave (or the error), and how it was produced.

    This is the user's private query log. Stored per user so the chat page
    can show earlier questions and the "My activity" page can report their
    own cache outcomes, latency, sources, cost and errors. ``sources`` is
    the Optimizer's source list as JSON.
    """

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    # ok | error
    status: Mapped[str] = mapped_column(String(10), default="ok", server_default="ok")
    error_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # "cache" | "crawler" | "none"
    answered_by: Mapped[str] = mapped_column(String(10), default="crawler")
    cached: Mapped[bool] = mapped_column(Boolean, default=False)
    # exact | semantic | miss | none
    cache_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    match_method: Mapped[str | None] = mapped_column(String(12), nullable=True)
    similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    compose_method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    sources: Mapped[str] = mapped_column(Text, default="[]")
    sources_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    cache_lookup_ms: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    crawl_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    llm_ms: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    served_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # exact_hit | semantic_hit | miss | bypassed | none
    cache_status: Mapped[str] = mapped_column(String(12), default="miss", server_default="miss")
    embedding_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    llm_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    embedding_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    saved_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    # INR charged to this user for this answer (0 for cache hits).
    billable_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    cost_inr: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    user: Mapped[User] = relationship(back_populates="chat_messages")
