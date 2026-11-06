# AGENTS.md

Repository-specific guidance for AI coding agents and contributors.

This file describes the repository as it actually exists. Verify before adding
new technology; several capabilities suggested by the README or marketing site
are not implemented in the backend.

## 1. Verified technology stack

### Backend

| Area | Technology | Version / evidence |
| --- | --- | --- |
| Web framework | FastAPI | `fastapi==0.139.2` in `requirements.txt` |
| ASGI server | Uvicorn (standard extras) | `uvicorn[standard]==0.51.0` |
| Language runtime | Python 3.11 target | `Dockerfile` uses `python:3.11-slim`; `pyproject.toml` targets `py311`; CI uses 3.11 |
| Validation / settings | Pydantic + pydantic-settings | `pydantic==2.13.4`, `pydantic-settings==2.14.2` |
| ORM / database access | SQLAlchemy 2.0 async | `sqlalchemy==2.0.51` |
| Local database | SQLite via aiosqlite | `aiosqlite==0.22.1`; default `DATABASE_URL=sqlite+aiosqlite:///./api_optimizer.db` |
| Production database | MySQL via aiomysql / PyMySQL | `aiomysql==0.3.2`, `pymysql==1.2.0` |
| Cache / counters | Redis async client | `redis==6.4.0`; wrapper in `app/utils/redis_client.py` |
| Authentication | JWT via python-jose | `python-jose[cryptography]==3.3.0`; HS256 only |
| Password hashing | bcrypt directly | `bcrypt==5.0.0`; passlib is not used |
| Structured logging | python-json-logger | `python-json-logger==4.1.0` |
| Task queue dependency | Celery | `celery==5.6.3`; configured but not orchestrated in this repo |
| Testing | pytest + pytest-asyncio + httpx | `pytest==9.1.1`, `pytest-asyncio==1.4.0`, `httpx==0.28.1` |

### Frontend dashboard (`frontend/`)

- React 18, Vite 6, React Router 6, Tailwind CSS 4 (`@tailwindcss/vite`),
  Recharts 3, axios, framer-motion 11, lucide-react.
- Plain JavaScript/JSX. No frontend test framework is configured.
- Build command: `npm run build`; dev server: `npm run dev` (port 5173).

### Marketing site (`site/`)

- Next.js 14.2.15 App Router, TypeScript, Tailwind CSS 3, framer-motion 11,
  Radix UI primitives, Recharts, ESLint (`next/core-web-vitals`).
- Commands: `npm run lint`, `npm run build`, `npm run dev`.

### Not present (do not assume otherwise)

- **Prometheus is not integrated.** There is no `prometheus_client` dependency,
  no `/metrics` endpoint, and no Prometheus instrumentation. The backend's
  `MetricsMiddleware` only writes request metrics to logs and the database.
  README/site references to "Prometheus" are roadmap/marketing content.
- **OpenTelemetry / distributed tracing is not integrated.**
- **Alembic is not used.** Schema creation happens through
  `Base.metadata.create_all` in `app/database/db.py:init_db()` and
  `migrate_db.py`. There is no migration versioning, and `create_all` will not
  alter existing tables.
- **No LLM Gateway, LLMOps, vector database, or AI provider SDK exists yet.**
- **No Docker/Kubernetes service runs Celery workers or Celery beat.**

## 2. Actual project structure

```text
.
├── app/                        # FastAPI backend
│   ├── main.py                 # App factory, lifespan, middleware stack, routers
│   ├── config.py               # Pydantic Settings, .env loading, validation
│   ├── api/
│   │   └── v1/                 # Routers: auth.py, health.py, analytics.py,
│   │                           #          rules.py, demo.py
│   ├── core/
│   │   ├── constants.py        # Cache keys, TTLs, roles, headers, messages
│   │   ├── exceptions.py       # APIException hierarchy
│   │   └── security.py         # JWTHandler, PasswordHandler, auth dependencies
│   ├── database/
│   │   ├── base.py             # declarative Base + BaseModel (id/timestamps)
│   │   └── db.py               # async engine, session factory, get_session,
│   │                           # init_db/close_db
│   ├── middleware/
│   │   ├── auth.py             # Global JWT authentication middleware
│   │   ├── cache.py            # Redis response caching middleware
│   │   ├── correlation_id.py   # X-Correlation-ID propagation
│   │   ├── metrics.py          # Request logging + analytics persistence
│   │   └── rate_limit.py       # Token-bucket rate limiting middleware
│   ├── models/__init__.py      # User, CacheRule, APILog, RateLimitCounter,
│   │                           # Analytics
│   ├── schemas/                # Pydantic v2 request/response models
│   ├── services/
│   │   ├── analytics.py        # Request logging, aggregates, percentiles
│   │   ├── auth.py             # Registration, login, refresh, token creation
│   │   ├── cache.py            # CacheService (get/set/invalidate/stats)
│   │   └── rate_limit.py       # Atomic Redis Lua token bucket
│   ├── tasks/
│   │   ├── __init__.py         # Celery app, shared tasks, beat schedule
│   │   └── reports.py          # Plain file-persistence helpers (not Celery)
│   └── utils/
│       ├── logger.py           # JSON logging configuration
│       └── redis_client.py     # RedisClient singleton + get_redis dependency
├── tests/                      # pytest integration suite
│   ├── conftest.py             # Isolated SQLite + Redis DB 15 fixtures
│   ├── test_auth_api.py        # Auth, token types, RBAC
│   ├── test_cache.py           # Cache hit/miss, keying, TTL, exclusions
│   ├── test_jwt_token_type.py  # JWT token-type security tests
│   └── test_rate_limit.py      # Token bucket, isolation, fail-open
├── frontend/                   # React + Vite dashboard
├── site/                       # Next.js marketing site
├── loadtest/benchmark.js       # k6 cache-off vs cache-on benchmark
├── migrate_db.py               # Idempotent table creation + initial admin
├── seed_demo.py                # Demo users, rules, and synthetic traffic
├── setup_mysql.py              # Windows-only local MySQL helper
├── test_api.py                 # In-process API smoke script (TestClient)
├── requirements.txt            # Pinned backend dependencies
├── pyproject.toml              # Ruff configuration only
├── pytest.ini                  # pytest-asyncio configuration
├── Dockerfile                  # Backend image
├── docker-compose.yml          # Redis + backend + frontend
├── render.yaml                 # Render backend deployment
├── .github/workflows/ci.yml    # Backend lint/test, frontend build, site lint/build
├── .env.example                # Backend environment template
├── AUDIT.md                    # Prior audit and hardening notes
└── README.md                   # User-facing documentation
```

## 3. Architecture and reusable components

### Request lifecycle

The effective middleware order, from outermost to innermost, is:

```text
CORS -> Metrics -> CorrelationId -> Auth -> RateLimit -> Cache -> route
```

`app/main.py` registers middleware in reverse because Starlette treats the last
registered middleware as outermost. Preserve this order:

- Auth must run before rate limiting so the limiter can key on
  `request.state.user_id`.
- Cache is innermost so auth, rate limiting, and metrics still run before a
  cache hit short-circuits the route.
- CORS must remain outermost.

Middleware side effects:

- `CorrelationIdMiddleware` accepts or creates `X-Correlation-ID`, stores it in
  `request.state.correlation_id`, and echoes it in the response header.
- `AuthMiddleware` globally requires a valid Bearer access token except for
  paths in `UNPROTECTED_PATHS`. Route-level dependencies (`get_current_user`,
  `verify_role`) add role checks on top.
- `RateLimitMiddleware` keys on `X-API-Key` (SHA-256 prefix), authenticated
  user, or client IP. `X-Forwarded-For` is trusted only when the direct peer is
  listed in `TRUSTED_PROXIES`. It is fail-open when Redis is unavailable.
- `CacheMiddleware` caches only GET requests that match an enabled `CacheRule`,
  only stores HTTP 200 responses, and sets `X-Cache-Hit` / `X-Cache-Stored`.
- `MetricsMiddleware` logs every request and persists `APILog` / hourly
  `Analytics` rows in a background task. It excludes `/api/v1/demo` from
  persistence.

### Reusable backend components

- `settings` (`app/config.py`): cached Pydantic settings singleton.
- `redis_client` and `get_redis` (`app/utils/redis_client.py`): global async
  Redis wrapper.
- `get_session` (`app/database/db.py`): request-scoped async SQLAlchemy session
  with rollback handling.
- `RedisClient`: JSON-aware `get`/`set`, `delete`, `exists`, `increment`,
  `get_ttl`, `scan_iter`, `eval`, `flush_all`, `keys`.
- `CacheService`: key generation, get/set, hit/miss counters, SCAN-based
  invalidation, cache statistics.
- `RateLimitService`: atomic token-bucket Lua script, usage inspection, reset.
- `AnalyticsService`: request logging, SQL aggregates, percentile calculation,
  latency series, benchmark reports, optimization suggestions.
- `AuthService`: registration, credential authentication, token creation,
  refresh-token exchange.
- `JWTHandler` / `PasswordHandler` (`app/core/security.py`).
- Dependencies: `get_current_user`, `verify_admin`, `verify_role([...])`.
- Exception hierarchy in `app/core/exceptions.py`; register handlers in
  `app/main.py` rather than returning raw exception text.
- Pydantic schemas in `app/schemas/` and SQLAlchemy models in `app/models/`.
- Structured logging via `configure_logging()` and `get_logger(__name__)`.

### API routing structure

All backend routes are included under `settings.api_v1_prefix`, default
`/api/v1`.

| Method | Path | Router | Notes |
| --- | --- | --- | --- |
| GET | `/` | `app/main.py` | Root status payload |
| GET | `/api/v1/health` | `health.py` | DB + Redis health; unprotected |
| GET | `/api/v1/ping` | `health.py` | Unprotected but rate-limited |
| POST | `/api/v1/auth/register` | `auth.py` | Public; only viewer/guest roles |
| POST | `/api/v1/auth/login` | `auth.py` | Public |
| POST | `/api/v1/auth/refresh` | `auth.py` | Public; requires refresh token |
| GET | `/api/v1/analytics/summary` | `analytics.py` | Protected |
| GET | `/api/v1/analytics/endpoints` | `analytics.py` | Protected |
| GET | `/api/v1/analytics/endpoints/{endpoint_path}` | `analytics.py` | Protected |
| GET | `/api/v1/analytics/benchmark` | `analytics.py` | Protected |
| POST | `/api/v1/analytics/benchmark/run` | `analytics.py` | Protected; background report |
| GET | `/api/v1/analytics/slow-endpoints` | `analytics.py` | Protected |
| GET | `/api/v1/analytics/suggestions` | `analytics.py` | Protected |
| GET/POST | `/api/v1/rules` | `rules.py` | Auth required; POST requires admin/operator |
| GET/PUT/DELETE | `/api/v1/rules/{rule_id}` | `rules.py` | PUT admin/operator; DELETE admin |
| GET | `/api/v1/demo/latency` | `demo.py` | Only when `DEMO_ENDPOINT_ENABLED=True`; unprotected/unthrottled |

Docs (`/docs`, `/redoc`, `/openapi.json`) are exposed only when `DEBUG=True`.

## 4. Redis implementation

- Dependency: `redis==6.4.0` using `redis.asyncio`.
- Entry point: `app/utils/redis_client.py`; module-level singleton
  `redis_client`; `connect()`/`disconnect()` are driven by the FastAPI lifespan.
- Connections use `decode_responses=True` and 3-second socket timeouts.
- Values are JSON-serialized for dict/list; plain strings are stored directly.
- Default cache TTL: `REDIS_CACHE_TTL` (3600 seconds).
- Key conventions:
  - `rule:<endpoint_pattern>:<generated-key>` for cached responses
  - `cache:enabled_rules` for the enabled rule list (TTL 10 seconds)
  - `cache:stats:hits`, `cache:stats:misses` for cache counters
  - `rate_limit:<identifier>` for token buckets
- Cache rules are loaded from the DB once per short TTL and cached in Redis;
  rule writes invalidate `cache:enabled_rules` eagerly.
- Rate limiting uses an atomic Lua token bucket (`RateLimitService._TOKEN_BUCKET_LUA`)
  through `RedisClient.eval`.
- Fail-open behavior is intentional: Redis errors allow rate-limited requests
  and turn cache lookups into misses.

## 5. Celery implementation

- Dependency is pinned (`celery==5.6.3`), but Celery is **optional** at runtime.
- `app/tasks/__init__.py` defines `celery_app` using optional
  `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` settings.
- `@shared_task` definitions:
  - `cleanup_cache` (hourly)
  - `aggregate_logs` (every 15 minutes)
  - `generate_performance_alerts` (every 30 minutes)
  - `cleanup_old_logs` (daily)
- A `celery_app.conf.beat_schedule` is defined in the same module.
- No worker or beat process is declared in `docker-compose.yml`, `render.yaml`,
  or CI. There is no worker start script documented in the repository.
- `app/tasks/reports.py` contains synchronous report-file helpers used by a
  FastAPI `BackgroundTasks` route; they are not Celery tasks.
- Tasks create their own event loop to run async DB/Redis work. Follow that
  pattern only if extending these tasks; prefer not duplicating it.

## 6. Coding conventions

### Python

- Target Python 3.11. Use type hints; the codebase uses modern syntax such as
  `list[str]`, `dict[str, Any]`, and `X | None` sparingly.
- Use absolute imports from `app.*`.
- Every module starts with a short docstring. Public classes/functions have
  docstrings.
- Backend code is async-first. Use `async def`, `await`, `AsyncSession`, and
  the async Redis client.
- SQLAlchemy 2.0 style only: `Mapped[...]`, `mapped_column(...)`, `select(...)`,
  `await session.execute(...)`. Do not use legacy `Query` APIs.
- Pydantic v2 only:
  - `ConfigDict(from_attributes=True)` for ORM-backed schemas
  - `model_validate(...)`, `model_dump(...)`, `model_dump(exclude_unset=True)`
  - `field_validator` / `Field` for validation
  - Do not use `.dict()`, `.json()`, `.from_orm()`, or `parse_obj()`.
- Routers: `APIRouter(prefix=..., tags=[...])`, `Depends(get_session)`,
  explicit `response_model`, and `Query(...)` for bounds.
- Business logic belongs in `app/services/`, not in routers or middleware.
- Database models inherit from `app.database.base.BaseModel`, which supplies
  `id`, `created_at`, and `updated_at`.
- Use `APIException` subclasses for domain errors and let the app-level handler
  format them. Do not leak raw exception strings or Pydantic internals to
  clients.
- Use `logging.getLogger(__name__)` or `get_logger(__name__)`; include
  structured `extra` fields where useful.
- Keep line length at 100 characters (Ruff configuration).

### Frontend

- Dashboard: functional React components, `.jsx`, hooks/context in
  `src/context` and `src/hooks`, API helpers in `src/lib`.
- Site: Next.js App Router, TypeScript, path alias `@/*`, reusable UI in
  `site/components`, motion helpers in `site/components/motion`.
- The frontend currently uses `framer-motion`; do not migrate it to the
  `motion` package without explicit approval.

## 7. Error handling and logging conventions

- Custom errors live in `app/core/exceptions.py` and carry `message`,
  `status_code`, `error_code`, and `details`.
- `app/main.py` registers handlers:
  - `APIException` -> `{"detail", "error_code", "details"}`
  - unhandled `Exception` -> HTTP 500
    `{"detail": "Internal server error", "error_code": "INTERNAL_ERROR"}`
- Some routes convert `APIException` to `HTTPException`, which produces a
  FastAPI default `{"detail": ...}` body. Preserve existing response shapes.
- Middleware error responses:
  - Missing/invalid auth: 401 `{"detail", "error_code"}`
  - Rate limit exceeded: 429 with `Retry-After`
- `get_session` rolls back on `HTTPException`, `RequestValidationError`, and
  unexpected exceptions; it logs client errors at debug level and real failures
  at error level.
- Logging is JSON to stdout through `configure_logging()`. Correlation IDs are
  propagated in `X-Correlation-ID`; include them in request logs where
  possible.
- Avoid logging secrets, tokens, passwords, or full authorization headers.

## 8. Environment variable management

- Settings are loaded from environment variables and `.env` via
  `pydantic-settings`; env vars override `.env`.
- `.env` is gitignored. Only `.env.example` and `frontend/.env.example` are
  committed. Never commit real secrets.
- Required settings (app fails to start without them):
  - `DATABASE_URL`
  - `REDIS_URL`
  - `SECRET_KEY` (minimum 32 chars; known placeholders are rejected)
  - `ADMIN_EMAIL`
  - `ADMIN_PASSWORD`
- Important optional settings:
  - `APP_NAME`, `APP_VERSION`, `DEBUG`, `LOG_LEVEL`, `SERVER_HOST`,
    `SERVER_PORT`
  - `DATABASE_ECHO`, `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW`,
    `DATABASE_POOL_RECYCLE`
  - `REDIS_CACHE_TTL`
  - `ALGORITHM` (must be `HS256`), `ACCESS_TOKEN_EXPIRE_MINUTES`,
    `REFRESH_TOKEN_EXPIRE_DAYS`
  - `DEMO_ENDPOINT_ENABLED` (default `False`; keep off in production)
  - `TRUSTED_PROXIES` (JSON array or comma-separated string)
  - `RATE_LIMIT_ENABLED`, `RATE_LIMIT_DEFAULT_REQUESTS`,
    `RATE_LIMIT_DEFAULT_PERIOD`
  - `CORS_ORIGINS` (JSON array or comma-separated string)
  - `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` (optional)
- Use `get_settings()` rather than constructing `Settings()` directly in
  application code.

## 9. Security requirements

- JWT algorithm is pinned to HS256. Access tokens use `type="access"`; refresh
  tokens use `type="refresh"`. The middleware rejects the wrong token type.
- Protect endpoints through the global `AuthMiddleware`; add
  `get_current_user` / `verify_role` dependencies for route-level checks.
- Self-registration must never allow privilege escalation. Only `viewer` and
  `guest` roles are assignable; other requested roles become `viewer`.
- Passwords are hashed with bcrypt directly, truncated to 72 bytes. Do not
  reintroduce passlib.
- Role checks: `admin`, `operator`, `viewer`, `guest`. Mutating cache rules:
  create/update require admin or operator; delete requires admin.
- Keep docs/OpenAPI disabled outside debug mode.
- Do not log or return secrets, tokens, password hashes, or raw exception
  internals.
- `X-Forwarded-For` is trusted only for peers in `TRUSTED_PROXIES`.
- Demo endpoints are unauthenticated and unthrottled; keep
  `DEMO_ENDPOINT_ENABLED=False` in production.
- Redis fail-open is intentional. Do not change it to fail-closed without an
  explicit architectural decision.

## 10. Testing instructions

- Framework: pytest with `pytest-asyncio` in auto mode and session-scoped loops
  (`pytest.ini`). New async tests do not need `@pytest.mark.asyncio`.
- Test location: `tests/`. `testpaths = tests`.
- Isolation:
  - Dedicated SQLite file `test_api_optimizer.db`, deleted before/after the run.
  - Dedicated Redis database `redis://localhost:6379/15`, flushed around tests.
  - Environment variables are set in `tests/conftest.py` before importing
    `app.*`. Do not import app modules before that in new test modules.
- Redis must be running locally for the suite (CI starts a `redis:7-alpine`
  service). Tests never touch the development Redis DB 0 or the dev database.
- Reuse shared fixtures instead of creating your own engine/client:
  - `client` (httpx `AsyncClient` with `ASGITransport`)
  - `admin_headers`, `operator_headers`, `viewer_headers`
  - `app_env` and `_clean_state` are autouse.
- Existing coverage: auth flows, JWT token-type confusion, RBAC, cache
  hit/miss/keying/TTL/exclusions, token-bucket limits and fail-open.
- Commands:

```bash
# Full suite (requires local Redis)
pytest -q

# Focused JWT security tests
pytest tests/test_jwt_token_type.py -v

# In-process smoke script (uses TestClient; expects configured DB/users)
python test_api.py
```

- Linting must pass exactly as CI runs it:

```bash
ruff check app tests seed_demo.py
```

- Ruff configuration: `line-length = 100`, `target-version = "py311"`,
  selected rules `E4, E7, E9, F, W605`.
- There is no configured frontend test runner. Do not claim frontend tests
  exist; use the existing build/lint gates:
  - `cd frontend && npm run build`
  - `cd site && npm run lint && npm run build`

## 11. Common commands

```bash
# Backend setup
pip install -r requirements.txt
cp .env.example .env            # Windows: Copy-Item .env.example .env
python migrate_db.py            # create tables + initial admin (idempotent)
python seed_demo.py             # optional demo data
python seed_demo.py --reset     # wipe logs/analytics, then reseed

# Run backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
# or
python -m app.main

# Docker (backend + Redis + frontend)
docker-compose up --build

# Frontend dashboard
cd frontend
npm install
npm run dev
npm run build

# Marketing site
cd site
npm install
npm run dev
npm run lint
npm run build
```

- Deployment: `render.yaml` runs `python migrate_db.py` pre-deploy and starts
  Uvicorn on `$PORT`. Secrets are marked `sync: false`.
- Load test: `python seed_demo.py` first, then run k6 with
  `CACHE=off`/`CACHE=on`. On PowerShell use `$env:CACHE='off'` before
  `k6 run loadtest/benchmark.js`.

## 12. Strict development rules

1. **Do not introduce new dependencies without asking the user first.** This
   includes Python packages, npm packages, services, and tools. Prefer the
   standard library and what is already pinned.
2. **Reuse existing implementations wherever possible.** Extend the existing
   services, middleware, clients, schemas, and exception types rather than
   creating parallel versions.
3. **Do not unnecessarily modify existing features.** Keep changes additive and
   scoped. Do not refactor unrelated code or rename existing public APIs.
4. **Do not expose API keys or secrets.** Never commit `.env`, hardcode
   credentials, log tokens, or return secret material in responses.
5. **Write tests for new functionality.** Add tests under `tests/` using the
   existing fixtures, and make sure `pytest -q` and Ruff still pass.
6. **Preserve backward compatibility.** Keep existing routes, response shapes,
   environment variable names, cache key formats, Redis key formats, and
   database table/column names stable unless a breaking change is explicitly
   approved.
7. **Explain significant architectural decisions.** Document trade-offs,
   alternatives considered, and operational impact in the change description.

Additional guardrails:

- Do not add Prometheus, OpenTelemetry, an LLM gateway, vector storage, or
  LLMOps features unless the user explicitly requests that work.
- Do not change the middleware order or make Redis failures fail-closed
  without an explicit decision.
- Do not replace the current schema-creation approach with Alembic or another
  migration tool without approval (it is a new dependency and a workflow
  change).
- Do not use `setup_mysql.py` in CI or production; it is a Windows-only,
  interactive local helper that rewrites `.env`.
- Do not modify `AUDIT.md` or `README.md` to claim capabilities that are not
  implemented.
