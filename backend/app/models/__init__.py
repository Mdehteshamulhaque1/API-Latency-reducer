"""
Database models for the application.
"""
from typing import Optional

from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    Enum,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import BaseModel
from app.core.constants import UserRole


class User(BaseModel):
    """User model for authentication and authorization."""
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.VIEWER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    api_quota: Mapped[int] = mapped_column(Integer, default=10000, nullable=False)  # Requests per month
    
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
    
    # Conditional caching
    cache_by_user: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cache_by_query_params: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cache_by_headers: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Cache invalidation
    max_cache_size: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)  # KB
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
    )


class RateLimitCounter(BaseModel):
    """Rate limit counters for users and IPs."""
    __tablename__ = "rate_limit_counters"

    identifier: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    identifier_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # 'user' or 'ip'
    
    request_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    limit: Mapped[int] = mapped_column(Integer, nullable=False)
    window_start: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_duration: Mapped[int] = mapped_column(Integer, nullable=False)  # seconds
    
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    __table_args__ = (
        Index("idx_rate_limit_identifier", "identifier"),
        Index("idx_rate_limit_type", "identifier_type"),
    )


class Analytics(BaseModel):
    """Aggregated analytics data for dashboards."""
    __tablename__ = "analytics"

    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    
    period: Mapped[str] = mapped_column(String(50), nullable=False)  # 'hourly', 'daily', 'weekly'
    
    total_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cache_hits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cache_misses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    avg_response_time_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    min_response_time_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_response_time_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    total_bytes_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_bytes_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    __table_args__ = (
        Index("idx_analytics_user", "user_id"),
        Index("idx_analytics_period", "period"),
        Index("idx_analytics_created", "created_at"),
    )
