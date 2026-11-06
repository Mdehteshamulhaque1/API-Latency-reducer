# API Optimizer — Audit & Hardening Report

**Date:** 2026-08-10
**Scope:** Full audit of the monorepo — backend (FastAPI), marketing site (Next.js), dashboard (React/Vite), scripts, config, and deployment readiness.

---

## 1. Repository inventory

| Path | What it is | State |
| --- | --- | --- |
| `app/` | FastAPI backend (routers, middleware, models, schemas, services, tasks, utils) | Audited, fixed, running |
| `site/` | Next.js 14 marketing site (`/` + `/dashboard`) | Linted, builds clean |
| `frontend/` | React + Vite + Recharts dashboard | Env-driven, builds clean |
| `tests/` | pytest suite — JWT token-type security | 13/13 pass |
| `test_api.py` | End-to-end API smoke tests (TestClient) | Passes, Windows-safe |
| `migrate_db.py` | Idempotent table + admin seeding | Cross-platform |
| `setup_mysql.py` | Windows-only MySQL setup helper | Kept (documented as local helper) |
| `requirements.txt` | Pinned, verified-working dependency set | Rewritten |
| `Dockerfile` / `render.yaml` | Container + Render deploy config | Added / fixed |
| `.env.example` / `frontend/.env.example` | Env templates | Added |
| `.gitignore` × 3 | Root, site, frontend | Added/fixed |
| `README.md` | Docs | Rewritten |
| `AUDIT.md` | This report | — |

## 2. Environment verification

- Machine has **only Python 3.14.3**. The old `venv/` was **broken** — its `pyvenv.cfg` referenced `C:\Users\hp\...` from another machine.
- Old pinned `requirements.txt` (fastapi 0.104.1, pydantic 2.4.2, SQLAlchemy 2.0.0, etc.) would not build on 3.14.
- **Clean-install proof:** fresh venv at `C:\Users\LENOVO\AppData\Local\Temp\opencode\apiopt-venv` installed the rewritten `requirements.txt` with zero conflicts.
- System Python's versions match the pins exactly (fastapi 0.139.2, pydantic 2.13.4, SQLAlchemy 2.0.51).
- Redis is running locally on `:6379`; the restarted backend connects to it (`Connected to Redis` in logs, `redis: healthy` in `/api/v1/health`).

## 3. Verification matrix

| Check | Result |
| --- | --- |
| Fresh `pip install -r requirements.txt` | Pass (no conflicts) |
| `pytest tests/test_jwt_token_type.py` | **13/13 passed** |
| `python test_api.py` (full smoke) | Pass |
| Live `/` , `/api/v1/ping`, `/api/v1/health` | 200 / 200 / healthy (db + redis) |
| Live login + refresh (OAuth2 `username`/`password`) | 200 / 200 (new access token) |
| Live rules **CREATE → LIST → UPDATE → DELETE** | 200 all (incl. datetime fields serialize) |
| Live `/analytics/summary`, `/benchmark`, `/suggestions` | 200 all |
| Client errors `401`/`422` return correct codes, **no ERROR log spam** | Verified |
| `npm run lint` in `site/` | Clean (8 unescaped-entity errors fixed) |
| `next build` in `site/` | Pass (static `/` + `/dashboard`) |
| `vite build` in `frontend/` | Pass (2632 modules) |

## 4. Bugs found & fixed

1. **Cache rule serialization 500** — `app/schemas/rules.py`: `created_at`/`updated_at` were typed `str`, so every rule returned an internal 500 (`string_type` validation). Changed to `datetime`.
2. **Analytics summary 500 on sparse data** — `app/services/analytics.py` (benchmark): indexing `logs[midpoint]` raised `IndexError` when exactly one log existed. Guarded with `min(midpoint, len(logs) - 1)`.
3. **Middleware ordering** — `app/main.py`: Auth ran **inside** RateLimit, so `request.state.user_id` was never populated when the limiter ran (and per-user rate limits keyed on nothing). Order is now `CORS → Metrics → CorrelationID → Auth → RateLimit → Cache`.
4. **Pydantic v1 → v2 migration** — `app/config.py` (`validation_alias`, `field_validator`, `SettingsConfigDict`); all schemas via `ConfigDict(from_attributes=True)`; `from_orm()` → `model_validate()`, `.dict()` → `.model_dump()` / `exclude_unset` in `app/api/v1/rules.py` and `app/api/v1/auth.py`.
5. **Windows-only path bug** — `migrate_db.py`: `rsplit('\\', 1)` hard-failed on POSIX; replaced with `os.path.dirname(os.path.abspath(__file__))`.
6. **Deprecated naive timestamps** — `app/core/security.py` `datetime.utcnow()` → aware `datetime.now(UTC)` (token expiry). `app/services/analytics.py` kept *naive* UTC (DB values read back from SQLite are naive) but replaced all `datetime.utcnow()` calls with an explicit `_utcnow()` helper to silence the 3.12+ deprecation without introducing aware-vs-naive comparison crashes.
7. **Windows console crash in tests** — `test_api.py` forced UTF-8 on stdout/stderr (emoji output crashed under cp1252).

## 5. Security & hardening

- **Info leaks removed:** `app/api/v1/rules.py`, `app/api/v1/analytics.py`, `app/api/v1/health.py` no longer return raw exception strings / Pydantic internals to clients; details go to server logs, clients get a generic message.
- **`bcrypt` 5.x used directly** (`migrate_db.py`, `app/services/auth.py`) — `passlib` is incompatible with bcrypt 5 and was removed.
- **JWT token-type enforcement** (access vs refresh) verified by the 13 security tests.
- **CORS, SECRET_KEY, DB pool size** now env-driven; `SECRET_KEY` min-length (32) validated at startup.
- **Log hygiene:** client 4xx (HTTPException, validation errors) no longer logged as `ERROR Database session error` (`app/database/db.py`); only true 5xx paths are.

## 6. Hygiene & packaging

- **Removed unused deps:** `fastapi-cors`, `flower`, `alembic`, `passlib[bcrypt]`, `black`, `flake8`, `isort`, `mypy`. Added explicit `bcrypt`, `aiosqlite`.
- **Pool defaults for free-tier MySQL:** `DATABASE_POOL_SIZE=5`, `DATABASE_MAX_OVERFLOW=2` (was 20/unbounded), wired through `app/config.py` → `app/database/db.py`.
- **Celery is optional:** `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` are `Optional` — app boots without a broker.
- **Deleted junk:** `frontend/vite.log`, `site/tsconfig.tsbuildinfo`. `site/next-dev.log` is locked by the running `next dev` server (remove it once the dev server is stopped).
- **gitignore coverage** for `logs/`, `*.log`, `.env`, `venv/`, `node_modules`, `.next`, `dist`, `*.db`.
- **Env templates:** root `.env.example` (full reference), `frontend/.env.example` (`VITE_API_URL`, `VITE_DOCS_URL`, `VITE_PROXY_TARGET`).

## 7. Deployment (Render + static hosts)

- `render.yaml`: builds backend image, `preDeployCommand: python migrate_db.py`, `healthCheckPath: /api/v1/health`, unversioned secrets (`sync: false`).
- `Dockerfile`: CMD honors `$PORT` (`sh -c 'uvicorn ... --port ${PORT:-8000}'`).
- Required Render env vars: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, optional `CORS_ORIGINS`, `LOG_LEVEL`.
- Frontend static builds read `VITE_API_URL` / `VITE_DOCS_URL` at build time; site is fully static.
- Local dev default DB is SQLite (`sqlite+aiosqlite:///./api_optimizer.db`); MySQL only when you set `DATABASE_URL`.

## 8. Known limitations / intentionally unchanged

- **`venv/` is still broken and left in place** (gitignored). Delete it and recreate with the new `requirements.txt` (`python -m venv venv`). It is not referenced by any config.
- **`setup_mysql.py`** is a Windows-only, dev-only helper. Kept because it's documented; not used in CI/deploy.
- **`DateTime(timezone=True)` + naive UTC:** SQLite returns naive datetimes regardless; analytics intentionally compares naive UTC. On MySQL, `DATETIME` also round-trips naive — consistent. If you later use `TIMESTAMP`-style aware columns, revisit `_utcnow()` in `app/services/analytics.py`.
- **Fail-open design:** when Redis is down, rate limiting allows requests and cache lookups miss — the API keeps serving. Confirmed intended.
- The **live backend on `:8000` now runs the audited code** (restarted from source with system Python, which matches the pinned versions). Local dashboard dev on `:5173` is currently used by an unrelated project (`Hire_Loop`).
