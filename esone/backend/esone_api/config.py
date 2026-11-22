"""
Settings for the Esone API, read from environment variables prefixed ESONE_.

Deployment notes
----------------
* Render injects DATABASE_URL as ``postgres://...``; it is normalised to the
  async driver (``postgresql+asyncpg://``) automatically.
* Render injects PORT; the start command passes it to uvicorn.
* ESONE_SECRET_KEY must be set in production. The dev default is refused
  when ESONE_ENV=production.
"""
from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET = "dev-only-change-me-dev-only-change-me"


def normalise_database_url(url: str) -> str:
    """Map common sync URLs (as supplied by hosting providers) to async drivers.

    Supabase and Render hand out ``postgres://`` / ``postgresql://`` URLs,
    sometimes with ``?sslmode=require``. asyncpg does not understand
    ``sslmode`` as a URL option (SSL is configured in ``database.make_engine``),
    so that parameter is stripped here.
    """
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    elif url.startswith("sqlite://") and "+aiosqlite" not in url:
        url = "sqlite+aiosqlite://" + url[len("sqlite://") :]
    elif url.startswith("mysql://"):
        url = "mysql+aiomysql://" + url[len("mysql://") :]

    if url.startswith("postgresql+asyncpg://"):
        parts = urlsplit(url)
        query = [(k, v) for k, v in parse_qsl(parts.query) if k not in {"sslmode", "ssl"}]
        url = urlunsplit(parts._replace(query=urlencode(query)))
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ESONE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "development"
    app_name: str = "Esone API"

    # Accept both ESONE_DATABASE_URL and the bare DATABASE_URL that Render sets.
    database_url: str = Field(
        default="sqlite+aiosqlite:///./esone.db",
        validation_alias=AliasChoices("ESONE_DATABASE_URL", "DATABASE_URL"),
    )

    secret_key: str = DEV_SECRET
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Comma-separated list, e.g. "http://localhost:4000,https://esone.vercel.app"
    cors_origins: str = "http://localhost:4000,http://127.0.0.1:4000"
    # Optional regex for extra origins, e.g. Vercel previews:
    #   ^https://esone(-[a-z0-9-]+)?\.vercel\.app$
    cors_origin_regex: str | None = None

    # Behind Render's load balancer the real client IP arrives in X-Forwarded-For.
    trust_proxy: bool = True
    # Login/register attempts per IP per minute. 0 disables the limiter.
    # Login and register attempts per client IP per sliding minute (OWASP-style
    # brute-force protection; 0 disables).
    auth_rate_limit_per_minute: int = 5

    # Optional first administrator, created on startup if the username is free.
    admin_username: str | None = None
    admin_email: str | None = None
    admin_password: str | None = None

    # API Optimizer (LLM gateway) used by POST /api/v1/chat. Esone signs in
    # there with this service account; users never see these values.
    optimizer_url: str | None = None
    optimizer_username: str | None = None
    optimizer_password: str | None = None
    optimizer_timeout_seconds: float = 60.0

    # Request telemetry: every request Esone serves and every call it makes
    # is shipped in batches to the Optimizer's POST /api/v1/ingest/requests
    # (same service account), where the Optimizer dashboard analyses it.
    # Needs the Optimizer settings above; the service account must have the
    # operator or admin role there.
    telemetry_enabled: bool = True
    telemetry_service_name: str = "esone"
    telemetry_flush_seconds: float = 30.0

    # Project chatbot (POST /api/v1/chatbot, public). Answers from
    # esone_api/chatbot/project_knowledge.txt; with a Gemini key the model
    # phrases the answer, without one the closest section is returned.
    gemini_api_key: str | None = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    gemini_model: str = "gemini-3.5-flash-lite"
    chatbot_timeout_seconds: float = 20.0
    chatbot_max_tokens: int = Field(default=500, ge=50, le=4096)
    # Chatbot messages per client IP per sliding minute (0 disables).
    chatbot_rate_limit_per_minute: int = 10

    @field_validator("optimizer_url")
    @classmethod
    def _clean_optimizer_url(cls, value: str | None) -> str | None:
        value = (value or "").strip().rstrip("/")
        return value or None

    @field_validator("gemini_api_key")
    @classmethod
    def _blank_key_is_none(cls, value: str | None) -> str | None:
        value = (value or "").strip()
        return value or None

    @field_validator("gemini_base_url")
    @classmethod
    def _clean_gemini_url(cls, value: str) -> str:
        return value.strip().rstrip("/")

    @field_validator("database_url")
    @classmethod
    def _normalise(cls, value: str) -> str:
        return normalise_database_url(value)

    @field_validator("cors_origin_regex")
    @classmethod
    def _blank_regex_is_none(cls, value: str | None) -> str | None:
        # An empty value (common when the variable exists but is left blank in
        # a dashboard or .env file) means "no regex", not "match nothing".
        value = (value or "").strip()
        return value or None

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.is_production and settings.secret_key == DEV_SECRET:
        raise RuntimeError("ESONE_SECRET_KEY must be set when ESONE_ENV=production")
    return settings
