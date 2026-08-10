"""
Application configuration management.
Supports environment-based configuration with validation.
"""
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # App Configuration
    app_name: str = Field(default="API Optimizer", validation_alias="APP_NAME")
    app_version: str = Field(default="1.0.0", validation_alias="APP_VERSION")
    debug: bool = Field(default=False, validation_alias="DEBUG")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    # Server
    server_host: str = Field(default="0.0.0.0", validation_alias="SERVER_HOST")
    server_port: int = Field(default=8000, validation_alias="SERVER_PORT")
    api_v1_prefix: str = Field(default="/api/v1", validation_alias="API_V1_PREFIX")

    # Database
    database_url: str = Field(validation_alias="DATABASE_URL")
    database_echo: bool = Field(default=False, validation_alias="DATABASE_ECHO")
    database_pool_size: int = Field(default=5, validation_alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=2, validation_alias="DATABASE_MAX_OVERFLOW")
    database_pool_recycle: int = Field(default=3600, validation_alias="DATABASE_POOL_RECYCLE")

    # Redis
    redis_url: str = Field(validation_alias="REDIS_URL")
    redis_cache_ttl: int = Field(default=3600, validation_alias="REDIS_CACHE_TTL")

    # JWT
    secret_key: str = Field(validation_alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", validation_alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, validation_alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # Demo endpoints (e.g. /api/v1/demo/latency) are deliberately
    # unauthenticated and unthrottled, so they must be off by default in
    # production and enabled only for demos / load testing.
    demo_endpoint_enabled: bool = Field(default=False, validation_alias="DEMO_ENDPOINT_ENABLED")

    # Proxy IPs allowed to set the X-Forwarded-For header (rate limiting).
    # Leave empty in production unless the app sits behind a reverse proxy
    # whose addresses are listed here.
    trusted_proxies: List[str] = Field(default=[], validation_alias="TRUSTED_PROXIES")

    # Celery (optional: the app boots without a broker; tasks are only
    # scheduled when a celery worker is actually started)
    celery_broker_url: Optional[str] = Field(default=None, validation_alias="CELERY_BROKER_URL")
    celery_result_backend: Optional[str] = Field(default=None, validation_alias="CELERY_RESULT_BACKEND")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, validation_alias="RATE_LIMIT_ENABLED")
    rate_limit_default_requests: int = Field(default=100, validation_alias="RATE_LIMIT_DEFAULT_REQUESTS")
    rate_limit_default_period: int = Field(default=3600, validation_alias="RATE_LIMIT_DEFAULT_PERIOD")

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        validation_alias="CORS_ORIGINS",
    )

    # Admin User
    admin_email: str = Field(validation_alias="ADMIN_EMAIL")
    admin_password: str = Field(validation_alias="ADMIN_PASSWORD")

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v):
        """Ensure secret key is long and not a well-known placeholder."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        normalized = v.strip().lower().replace(" ", "")
        if normalized in {
            "change-me-to-a-long-random-string",
            "change-me-in-production",
            "changeme",
            "secret",
            "changethis",
            "changethisnow",
        }:
            raise ValueError("SECRET_KEY must not be a known placeholder value")
        return v

    @field_validator("algorithm")
    @classmethod
    def validate_algorithm(cls, v):
        """Pin the JWT signing algorithm to HS256."""
        if v != "HS256":
            raise ValueError("Only the HS256 JWT algorithm is supported")
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


# Export settings instance
settings = get_settings()
