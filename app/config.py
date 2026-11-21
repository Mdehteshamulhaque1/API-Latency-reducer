"""
Application configuration management.
Supports environment-based configuration with validation.
"""
import json
import logging
from functools import lru_cache
from typing import Optional, Annotated, List

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

    # LLM gateway. The gateway speaks the OpenAI Chat Completions protocol, so
    # the OPENAI_* setting names are kept, but the default provider is Google
    # Gemini through its OpenAI-compatible endpoint (OPENAI_API_KEY holds the
    # Gemini key). Point OPENAI_BASE_URL at api.openai.com or a local Ollama
    # to use a different provider.
    llm_provider: str = Field(
        default="gemini",
        validation_alias="LLM_PROVIDER",
        description="Provider label stored in ai_request_logs.provider and used in logs/metrics",
    )
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai",
        validation_alias="OPENAI_BASE_URL",
    )
    openai_model: str = Field(default="gemini-3.5-flash-lite", validation_alias="OPENAI_MODEL")
    openai_primary_model: str | None = Field(
        default=None,
        validation_alias="OPENAI_PRIMARY_MODEL",
    )
    openai_fallback_model: str | None = Field(
        default="gemini-3.5-flash",
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

    # Reverse proxy for monitored services: /proxy/<name>/<path> is forwarded
    # to the base URL mapped here, e.g. PROXY_UPSTREAMS={"esone":"http://localhost:8000"}.
    # Every proxied call is logged under that service, rate limited per client
    # and cached when a /proxy/<name>/... cache rule exists.
    proxy_upstreams: dict[str, str] = Field(default_factory=dict, validation_alias="PROXY_UPSTREAMS")
    proxy_timeout_seconds: float = Field(default=30.0, gt=0, le=300, validation_alias="PROXY_TIMEOUT_SECONDS")

    # AI guardrails
    guardrails_block_injection: bool = Field(
        default=True, validation_alias="GUARDRAILS_BLOCK_INJECTION"
    )
    guardrails_mask_pii: bool = Field(default=True, validation_alias="GUARDRAILS_MASK_PII")

    # Embeddings + RAG. The embedding endpoint is OpenAI-compatible
    # (POST {base_url}/embeddings); it defaults to the chat provider's
    # base URL and key so one configuration serves both.
    embedding_model: str = Field(
        default="gemini-embedding-001", validation_alias="EMBEDDING_MODEL"
    )
    embedding_base_url: str | None = Field(default=None, validation_alias="EMBEDDING_BASE_URL")
    embedding_api_key: str | None = Field(default=None, validation_alias="EMBEDDING_API_KEY")
    chroma_persist_dir: str = Field(default="./data/chroma", validation_alias="CHROMA_PERSIST_DIR")
    max_upload_mb: int = Field(default=10, ge=1, le=100, validation_alias="MAX_UPLOAD_MB")
    rag_chunk_size: int = Field(default=900, ge=200, le=4000, validation_alias="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(default=150, ge=0, le=1000, validation_alias="RAG_CHUNK_OVERLAP")
    rag_top_k: int = Field(default=5, ge=1, le=20, validation_alias="RAG_TOP_K")
    # Question answering (POST /api/v1/answers): semantic Redis cache, then crawler.
    answers_similarity_threshold: float = Field(
        default=0.92, ge=0.0, le=1.0, validation_alias="ANSWERS_SIMILARITY_THRESHOLD"
    )
    answers_lexical_threshold: float = Field(
        default=0.80, ge=0.0, le=1.0, validation_alias="ANSWERS_LEXICAL_THRESHOLD"
    )
    # Answered questions stay in the semantic cache for two hours.
    answers_cache_ttl: int = Field(default=2 * 3600, ge=60, validation_alias="ANSWERS_CACHE_TTL")
    answers_max_tokens: int = Field(default=400, ge=50, le=4096, validation_alias="ANSWERS_MAX_TOKENS")
    # The newest asked questions are also kept in a Redis list for fast reads
    # by the dashboard; entries older than this drop out of the list (the
    # database keeps every row).
    answers_recent_ttl: int = Field(default=3600, ge=60, validation_alias="ANSWERS_RECENT_TTL")
    # Time-sensitive questions (weather, prices, scores, "today") are cached
    # only this long and never matched semantically.
    answers_volatile_ttl: int = Field(default=600, ge=30, validation_alias="ANSWERS_VOLATILE_TTL")
    # On a cache miss ask the model from its own knowledge first; only when it
    # says it does not know (or the question needs current information) read
    # Wikipedia, then the other sources. False restores sources-first.
    answers_model_first: bool = Field(default=True, validation_alias="ANSWERS_MODEL_FIRST")
    # Stampede protection: the first request for an uncached question takes a
    # short Redis lock while it generates; identical concurrent requests wait
    # up to ANSWERS_LOCK_WAIT_SECONDS for the entry to appear instead of
    # generating again. Lock TTL caps how long a crashed generator blocks others.
    answers_lock_ttl: int = Field(default=45, ge=5, le=300, validation_alias="ANSWERS_LOCK_TTL")
    answers_lock_wait_seconds: float = Field(default=12.0, ge=0.0, le=120.0, validation_alias="ANSWERS_LOCK_WAIT_SECONDS")
    # Cached answers whose embedding was produced by another model are still
    # matched exactly, never semantically.
    # Embedding pricing (USD per million tokens), used for the per-request
    # embedding cost. 0 means free (e.g. a local Ollama model).
    embedding_price_per_million: float = Field(default=0.0, ge=0.0, validation_alias="EMBEDDING_PRICE_PER_MILLION")
    EMBEDDING_PRICING_TABLE: dict[str, float] = {
        "gemini-embedding-001": 0.15,
        "text-embedding-3-small": 0.02,
        "text-embedding-3-large": 0.13,
        "nomic-embed-text": 0.0,
    }
    pricing_currency: str = Field(default="USD", validation_alias="PRICING_CURRENCY")
    # When the prices in PRICING_TABLE / EMBEDDING_PRICING_TABLE were last checked.
    pricing_effective_date: str = Field(default="2026-11-01", validation_alias="PRICING_EFFECTIVE_DATE")
    answers_inr_per_token: float = Field(
        default=5.0,
        ge=0.0,
        validation_alias="ANSWERS_INR_PER_TOKEN",
        description="INR charged per token of a non-cached answer",
    )

    def embedding_price_for(self, model: Optional[str]) -> float:
        """USD per million tokens for an embedding model (table, else the global default)."""
        if model and model in self.EMBEDDING_PRICING_TABLE:
            return self.EMBEDDING_PRICING_TABLE[model]
        return self.embedding_price_per_million
    answers_recent_max: int = Field(default=500, ge=10, le=5000, validation_alias="ANSWERS_RECENT_MAX")
    crawler_max_results: int = Field(default=3, ge=1, le=10, validation_alias="CRAWLER_MAX_RESULTS")
    crawler_timeout_seconds: float = Field(default=15.0, ge=1.0, validation_alias="CRAWLER_TIMEOUT_SECONDS")
    crawler_user_agent: str = Field(
        default="APIOptimizer/1.0 (answers crawler; contact: admin@example.com)",
        validation_alias="CRAWLER_USER_AGENT",
    )
    # Which sources the crawler asks, comma separated. Known names:
    # wikipedia, duckduckgo, wikidata, websearch (needs WEB_SEARCH_* below).
    crawler_sources: str = Field(
        default="wikipedia,duckduckgo,wikidata,websearch", validation_alias="CRAWLER_SOURCES"
    )
    # Keyed web search for the open web: "brave" (WEB_SEARCH_API_KEY) or
    # "google" (WEB_SEARCH_API_KEY + GOOGLE_CSE_ID). Unset disables it.
    web_search_provider: str | None = Field(default=None, validation_alias="WEB_SEARCH_PROVIDER")
    web_search_api_key: str | None = Field(default=None, validation_alias="WEB_SEARCH_API_KEY")
    google_cse_id: str | None = Field(default=None, validation_alias="GOOGLE_CSE_ID")
    # Follow web search result links and extract the page text (stdlib HTML
    # parser); otherwise only the search snippets are used.
    crawler_fetch_pages: bool = Field(default=True, validation_alias="CRAWLER_FETCH_PAGES")
    crawler_fetch_limit: int = Field(default=3, ge=0, le=10, validation_alias="CRAWLER_FETCH_LIMIT")
    crawler_max_page_bytes: int = Field(default=400_000, ge=10_000, validation_alias="CRAWLER_MAX_PAGE_BYTES")
    # Domain suffixes ranked first among web results (government, academic,
    # international bodies, reference sites).
    crawler_trusted_domains: str = Field(
        default=(
            ".gov,.gov.in,.nic.in,.gov.uk,.gov.au,.gc.ca,.edu,.ac.uk,.ac.in,who.int,un.org,europa.eu,"
            "wikipedia.org,britannica.com,nih.gov,nasa.gov,bbc.co.uk,reuters.com,nature.com"
        ),
        validation_alias="CRAWLER_TRUSTED_DOMAINS",
    )

    @property
    def crawler_source_list(self) -> list[str]:
        return [s.strip().lower() for s in self.crawler_sources.split(",") if s.strip()]

    @property
    def crawler_trusted_domain_list(self) -> list[str]:
        return [s.strip().lower() for s in self.crawler_trusted_domains.split(",") if s.strip()]

    @property
    def web_search_configured(self) -> bool:
        provider = (self.web_search_provider or "").lower()
        if provider == "brave":
            return bool(self.web_search_api_key)
        if provider == "google":
            return bool(self.web_search_api_key and self.google_cse_id)
        return False
    rag_min_similarity: float = Field(
        default=0.25, ge=0.0, le=1.0, validation_alias="RAG_MIN_SIMILARITY"
    )
    assistant_max_tokens: int = Field(
        default=700, ge=64, le=4096, validation_alias="ASSISTANT_MAX_TOKENS"
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

    # Rate limiting: one token bucket per caller, sized by tier (the usual
    # public-API scheme: anonymous callers get a small budget, signed-in users
    # more, service accounts and admins the most). Capacity = requests, refilled
    # evenly over the period, so short bursts up to the capacity are allowed.
    rate_limit_enabled: bool = Field(default=True, validation_alias="RATE_LIMIT_ENABLED")
    # Anonymous callers, keyed by client IP (also proxied traffic of monitored services).
    rate_limit_anonymous_requests: int = Field(default=60, ge=1, validation_alias="RATE_LIMIT_ANONYMOUS_REQUESTS")
    rate_limit_anonymous_period: int = Field(default=60, ge=1, validation_alias="RATE_LIMIT_ANONYMOUS_PERIOD")
    # Signed-in viewers (and guests), keyed by user id.
    rate_limit_user_requests: int = Field(default=300, ge=1, validation_alias="RATE_LIMIT_USER_REQUESTS")
    rate_limit_user_period: int = Field(default=60, ge=1, validation_alias="RATE_LIMIT_USER_PERIOD")
    # Operators and admins: dashboards and service accounts that ship telemetry.
    rate_limit_privileged_requests: int = Field(default=1000, ge=1, validation_alias="RATE_LIMIT_PRIVILEGED_REQUESTS")
    rate_limit_privileged_period: int = Field(default=60, ge=1, validation_alias="RATE_LIMIT_PRIVILEGED_PERIOD")
    # Legacy single-tier settings. No longer used by the limiter; kept so an
    # older .env still loads.
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

    # Pricing table: model -> {"prompt": float, "completion": float} in USD per
    # 1,000,000 tokens (Google and OpenAI list prices, 2025; standard tier,
    # prompts under the long-context threshold). If a model is not listed and
    # the global default is 0, the cost for that request is 0 and a warning is
    # logged. All costs are estimates and are labelled as such.
    PRICING_TABLE: dict[str, dict[str, float]] = {
        "gemini-2.5-pro":        {"prompt": 1.25, "completion": 10.00},
        "gemini-2.5-flash":      {"prompt": 0.30, "completion": 2.50},
        "gemini-2.5-flash-lite": {"prompt": 0.10, "completion": 0.40},
        # Newer Flash generations: priced like their 2.5 counterparts until
        # Google publishes list prices for them (estimates either way).
        "gemini-3.8-flash":      {"prompt": 0.30, "completion": 2.50},
        "gemini-3.5-flash":      {"prompt": 0.30, "completion": 2.50},
        "gemini-3.5-flash-lite": {"prompt": 0.10, "completion": 0.40},
        "gemini-2.0-flash":      {"prompt": 0.10, "completion": 0.40},
        "gpt-4o-mini":           {"prompt": 0.15, "completion": 0.60},
        "gpt-4o":                {"prompt": 2.50, "completion": 10.00},
        "gpt-3.5-turbo":         {"prompt": 0.50, "completion": 1.50},
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
