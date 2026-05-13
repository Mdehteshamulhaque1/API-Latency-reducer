"""
Application configuration management.
Supports environment-based configuration with validation.
"""
import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App Configuration
    app_name: str = Field(default="API Optimizer", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = Field(env="DATABASE_URL")
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE")
    database_pool_recycle: int = Field(default=3600, env="DATABASE_POOL_RECYCLE")
    database_echo: bool = False

    # Redis
    redis_url: str = Field(env="REDIS_URL")
    redis_cache_ttl: int = Field(default=3600, env="REDIS_CACHE_TTL")

    # JWT
    secret_key: str = Field(env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")

    # Celery
    celery_broker_url: str = Field(env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(env="CELERY_RESULT_BACKEND")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_default_requests: int = Field(default=100, env="RATE_LIMIT_DEFAULT_REQUESTS")
    rate_limit_default_period: int = Field(default=3600, env="RATE_LIMIT_DEFAULT_PERIOD")

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )

    # Admin User
    admin_email: str = Field(env="ADMIN_EMAIL")
    admin_password: str = Field(env="ADMIN_PASSWORD")

    class Config:
        env_file = ".env"
        case_sensitive = False

    @validator("secret_key")
    def validate_secret_key(cls, v):
        """Ensure secret key is long enough for production."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


# Export settings instance
settings = get_settings()
