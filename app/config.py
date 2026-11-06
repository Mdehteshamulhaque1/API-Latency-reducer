"""
Application configuration management.
Supports environment-based configuration with validation.
"""
import json
import logging
from functools import lru_cache
from typing import Annotated, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, NoDecode


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
    redis_connect_timeout: int = Field(
        default=3,
        ge=1,
        le=30,
        validation_alias="REDIS_CONNECT_TIMEOUT",
    )
    redis_socket_timeout: int = Field(
        default=3,
        ge=1,
        le=30,
        validation_alias="REDIS_SOCKET_TIMEOUT",
    )

    # OpenAI / LLM Gateway
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias="OPENAI_BASE_URL",
    )
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")
    openai_primary_model: str | None = Field(
        default=None,
        validation_alias="OPENAI_PRIMARY_MODEL",
    )
    openai_fallback_model: str | None = Field(
        default="gpt-4o",
        validation_alias="OPENAI_FALLBACK_MODEL",
    )
    llm_circuit_failure_threshold: int = Field(
        default=5,
        ge=1,
        le=100,
        validation_alias="LLM_CIRCUIT_FAILURE_THRESHOLD",
    )
    llm_circuit_cooldown_seconds: float = Field(
        default=30.0,
        gt=0,
        le=3600,
        validation_alias="LLM_CIRCUIT_COOLDOWN_SECONDS",
    )
    llm_circuit_half_open_max_probes: int = Field(
        default=1,
        ge=1,
        le=10,
        validation_alias="LLM_CIRCUIT_HALF_OPEN_MAX_PROBES",
    )
    llm_circuit_half_open_success_threshold: int = Field(
        default=1,
        ge=1,
        le=10,
        validation_alias="LLM_CIRCUIT_HALF_OPEN_SUCCESS_THRESHOLD",
    )
    openai_timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        le=120,
        validation_alias="OPENAI_TIMEOUT_SECONDS",
    )
    openai_max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        validation_alias="OPENAI_MAX_RETRIES",
    )

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
    # NoDecode keeps the raw env string so the validator below can accept a
    # JSON array OR a comma-separated list (pydantic-settings would otherwise
    # hard-crash at startup if the value is not strict JSON).
    trusted_proxies: Annotated[List[str], NoDecode] = Field(
        default=[],
        validation_alias="TRUSTED_PROXIES",
    )

    # Celery (optional: the app boots without a broker; tasks are only
    # scheduled when a celery worker is actually started)
    celery_broker_url: Optional[str] = Field(default=None, validation_alias="CELERY_BROKER_URL")
    celery_result_backend: Optional[str] = Field(default=None, validation_alias="CELERY_RESULT_BACKEND")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, validation_alias="RATE_LIMIT_ENABLED")
    rate_limit_default_requests: int = Field(default=100, validation_alias="RATE_LIMIT_DEFAULT_REQUESTS")
    rate_limit_default_period: int = Field(default=3600, validation_alias="RATE_LIMIT_DEFAULT_PERIOD")

    # CORS
    cors_origins: Annotated[List[str], NoDecode] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        validation_alias="CORS_ORIGINS",
    )

    @field_validator("cors_origins", "trusted_proxies", mode="before")
    @classmethod
    def parse_str_list(cls, v):
        """Accept a JSON array or a comma-separated string from the env."""
        if isinstance(v, str):
            value = v.strip()
            if not value:
                return []
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except (ValueError, TypeError):
                pass
            return [item.strip() for item in value.split(",") if item.strip()]
        return v

    # Pricing (per 1M tokens, overridable via env)
    chat_prompt_price_per_million: float = Field(
        default=0.0,
        validation_alias="CHAT_PROMPT_PRICE_PER_MILLION",
        description="Default prompt price per million tokens; overridden per-model in PRICING_TABLE",
    )
    chat_completion_price_per_million: float = Field(
        default=0.0,
        validation_alias="CHAT_COMPLETION_PRICE_PER_MILLION",
        description="Default completion price per million tokens; overridden per-model in PRICING_TABLE",
    )

    # Pricing table: model -> {"prompt": float, "completion": float} per 1M tokens.
    # Values are in USD.  If a model is not listed and the global default is 0,
    # the cost for that request is 0 and a warning is logged.
    PRICING_TABLE: dict[str, dict[str, float]] = {
        "gpt-3.5-turbo": {"prompt": 0.001, "completion": 0.002},
        "gpt-4o":        {"prompt": 0.03,  "completion": 0.06},
    }

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


# ---------------------------------------------------------------------------
# Cost estimation helper
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


def compute_estimated_cost(
    served_model: str,
    prompt_tokens: int,
    completion_tokens: int,
    pricing_table: dict,
    global_prompt_price: float,
    global_completion_price: float,
) -> float:
    """Return estimated cost in USD for a chat request.

    If the model is not in *pricing_table* and *global_prompt_price*/*global_completion_price*
    are zero, the cost is 0 and a warning is logged.
    """
    # Check per‑model table first
    model_pricing = pricing_table.get(served_model)
    if model_pricing is not None:
        prompt_price = model_pricing.get("prompt", global_prompt_price)
        completion_price = model_pricing.get("completion", global_completion_price)
    else:
        # Fall back to global defaults
        prompt_price = global_prompt_price
        completion_price = global_completion_price

    # If both are zero, cost is zero – we still log a warning if the model was unknown.
    if prompt_price == 0 and completion_price == 0:
        logger.warning(
            "No pricing information for model %s; cost will be 0", served_model,
        )
        return 0.0

    prompt_cost = (prompt_tokens / 1_000_000) * prompt_price
    completion_cost = (completion_tokens / 1_000_000) * completion_price
    return prompt_cost + completion_cost


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


# Export settings instance
settings = get_settings()
