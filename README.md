# API Optimizer

**High-performance API optimization platform** — Redis response caching, token-bucket rate limiting, JWT authentication, and real-time request analytics for FastAPI services.

[![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white)](https://redis.io)
[![MySQL](https://img.shields.io/badge/MySQL-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com)
[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com)
[![JWT](https://img.shields.io/badge/JWT-000000?logo=jsonwebtokens&logoColor=white)](https://jwt.io)

---

## Overview

API Optimizer is a backend infrastructure platform that reduces API latency and improves application performance. It combines:

- **Redis-based response caching** — rules-driven keys, TTLs, and automatic invalidation so most reads never reach the database.
- **Token-bucket rate limiting** — atomic per-user, per-IP, and per-key limits enforced before business logic runs.
- **JWT authentication** — strict access/refresh token-type validation across every protected endpoint.
- **Request analytics** — real-time latency percentiles (p50/p95/p99), cache hit ratio, and slow-endpoint rankings.

## Architecture

```
 Client
   │
   ▼
 FastAPI (middleware stack — CORS → Metrics → CorrelationID → Auth → RateLimit → Cache)
   │
   ├── Metrics ────────────────► logs to database
   ├── Auth ───────────────────► JWT (type = "access")
   ├── Rate Limit ─────────────► Redis token bucket
   └── Cache ──────────────────► Redis lookup
         │
         ├── HIT  ─────────────► respond from cache
         └── MISS ─────────────► business logic ──► database
                                    │
                                    ▼
                              write-through to Redis (TTL)
```

Middleware order is deliberate: **Auth runs outside the rate limiter** so the limiter always has `request.state.user_id`, and the cache layer sits innermost so auth, rate limiting, and metrics always run before a cached response short-circuits the request.

**Fail-open behavior:** if Redis is down, caching and rate limiting degrade gracefully — rate limits are allowed and cache lookups miss — so the API keeps serving traffic.

## Features

| Area | What it does |
| --- | --- |
| ⚡ Redis response caching | Pattern-based rules, user/param keying, automatic invalidation, hit/miss tracking |
| 📊 Request analytics | Real-time counts, latency trends, percentile rankings, optimization suggestions |
| 🚦 Token-bucket rate limiter | User + IP + API-key limits, configurable per endpoint, Redis-backed |
| 🔐 JWT authentication | Access (30m) and refresh (7d) tokens with strict type validation |
| 📈 Performance monitoring | p50 / p95 / p99 latency, slow-endpoint rankings |
| 🛡 Role-based access control | Admin, operator, and viewer roles gate every mutation |
| 🐳 Docker support | Single-container deploy with health checks (`render.yaml` included) |
| 📋 API documentation | Auto-generated interactive OpenAPI docs at `/docs` |

## Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | FastAPI (async) |
| Language | Python 3.11+ (verified on 3.14) |
| Database | SQLAlchemy 2.0 async — SQLite (local, default) or MySQL |
| Cache / queue | Redis |
| Authentication | JWT (`python-jose`) |
| Task queue | Celery (optional — app boots without a broker) |
| Frontend (dashboard) | React + Vite + Recharts |
| Frontend (marketing site) | Next.js 14 + Tailwind + Framer Motion |
| Container | Docker |

## Repository Layout

```
.
├── app/                 # FastAPI backend
│   ├── api/v1/          # Routers: auth, health, analytics, rules
│   ├── core/            # Config, security, exceptions, constants
│   ├── database/        # SQLAlchemy engine, session, base
│   ├── middleware/      # auth · cache · rate_limit · metrics · correlation_id
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic request/response schemas
│   ├── services/        # Business logic: analytics, auth, cache, rate_limit
│   ├── tasks/           # Celery background tasks
│   └── utils/           # Logging, Redis client
├── frontend/            # React dashboard (Vite)
├── site/                # Next.js marketing site
├── tests/               # pytest suite (JWT token-type security tests)
├── migrate_db.py        # Creates tables + default admin user
├── setup_mysql.py       # One-shot MySQL setup helper
├── test_api.py          # End-to-end API smoke tests
├── requirements.txt
├── Dockerfile
├── render.yaml          # Render.com deploy config
└── .env.example         # Backend env template
```

## Getting Started

### Prerequisites

- Python 3.11+
- Redis (local install or managed instance)
- MySQL only if you want production storage — the app runs on SQLite out of the box

### 1. Configure environment

Copy the sample environment variables into `.env`:

```bash
cp .env.example .env
```

Key values (see `.env.example` for the full reference with comments):

```dotenv
DATABASE_URL=sqlite+aiosqlite:///./api_optimizer.db   # or mysql+aiomysql://USER:PASSWORD@HOST:3306/api_optimizer
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=<long-random-string>                        # min 32 chars; python -c "import secrets; print(secrets.token_urlsafe(64))"
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-me-in-production                 # change before deploying
```

### 2. Install and migrate

```bash
python -m venv venv
venv\Scripts\activate            # Windows
source venv/bin/activate         # macOS / Linux

pip install -r requirements.txt
python migrate_db.py             # creates 5 tables + default admin user
```

`migrate_db.py` creates the following tables: `users`, `api_logs`, `cache_rules`, `rate_limit_counters`, and `analytics`. It is idempotent — existing tables are left untouched.

### 3. Run the backend

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- Interactive API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/v1/health`

### 4. Run the dashboard (React/Vite)

```bash
cd frontend
cp .env.example .env.local       # optional — defaults proxy /api to localhost:8000
npm install
npm run dev                      # http://localhost:5173 (proxies /api to :8000)
```

### 5. Run the marketing site (Next.js)

```bash
cd site
npm install
npm run lint                     # eslint
npm run dev                      # http://localhost:3000
```

### Docker

```bash
docker build -t api-optimizer .
docker run -p 8000:8000 --env-file .env api-optimizer
```

## Deployment (Render)

`render.yaml` ships in the repo. It builds the backend image, runs `python migrate_db.py` as a pre-deploy step, and health-checks `/api/v1/health`. Set these environment variables in the Render dashboard (never hardcode secrets in the repo):

| Variable | Required | Notes |
| --- | --- | --- |
| `DATABASE_URL` | ✅ | `mysql+aiomysql://...` (e.g. Render's managed Postgres/MySQL or a free-tier MySQL) |
| `REDIS_URL` | ✅ | e.g. Render Redis or Upstash — without it caching/rate-limit fail open |
| `SECRET_KEY` | ✅ | Unique, ≥ 32 chars, **generated per deployment** |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | ✅ | Seed admin (created by `migrate_db.py`) |
| `CORS_ORIGINS` | — | JSON array of your deployed dashboard/site origins |
| `LOG_LEVEL` | — | `INFO` default |

Deploy the `site/` folder (Next.js) and `frontend/` (Vite static) to a static host (Vercel/Netlify/Render static site) and point them at the backend URL via `VITE_API_URL` / `VITE_DOCS_URL`.

## Authentication & Security

Tokens carry a `type` claim that is enforced at the middleware level:

- `access` tokens (30 min) may call **protected endpoints** only.
- `refresh` tokens (7 days) may only be exchanged at `POST /api/v1/auth/refresh`.
- A token of the wrong type is rejected with `401 Invalid token type`.

This closes the token-type-confusion vulnerability where a refresh token could be replayed against protected endpoints. See `tests/test_jwt_token_type.py` for the security test scenarios.

## Testing

```bash
# JWT token-type security tests
pytest tests/test_jwt_token_type.py -v

# Full test suite: auth flows, cache hit/miss semantics, rate limiting
pytest -q                      # 44 tests, no external services needed (isolated Redis db 15 + SQLite)

# End-to-end API smoke tests (uses FastAPI TestClient — no server needed)
python test_api.py
```

The test suite runs entirely against isolated resources — it never touches your
development Redis or database. Redis must be running locally (it uses db 15);
the tests use their own SQLite file (`test_api_optimizer.db`). See `pytest.ini`
and `tests/conftest.py`.

## Load-test benchmark (cache OFF vs ON)

A k6 script drives synthetic traffic at `GET /api/v1/demo/latency`, an endpoint
that simulates a slow 150 ms upstream call so the caching layer has real work to
absorb. The script logs in as admin, toggles the demo cache rule, and measures
both runs under an identical load profile.

```bash
# prerequisites: backend running on :8000, Redis up, demo rule seeded
python seed_demo.py            # creates users + rules incl. /api/v1/demo/latency

# install k6 (https://k6.io), then:
CACHE=off k6 run loadtest/benchmark.js     # bash:  cache disabled
CACHE=on  k6 run loadtest/benchmark.js     #        cache enabled
```

Env vars: `BASE_URL`, `VUS` (default 20), `DURATION` (default 30s), `SLEEP`,
`ADMIN_USER` / `ADMIN_PASS`. On Windows PowerShell use `$env:CACHE='off'` first.

### Results (10 VUs, 30s, same load profile)

| Metric | Cache OFF | Cache ON | Improvement |
| --- | --- | --- | --- |
| Avg latency | 183 ms | 7.5 ms | **~24× faster (−95.9%)** |
| P95 latency | 208 ms | 18 ms | ~11× faster |
| Throughput | ~35 req/s | ~91 req/s | **~2.6× more** |
| Cache hit rate | 0% | 99.6% | — |

Run with `VUS=10` (as above) for stable, spike-free numbers on SQLite; higher
concurrency is bounded by the SQLite write path, not the cache. The demo
endpoint is deliberately excluded from auth, rate limiting, and analytics
persistence so the benchmark isolates the caching layer.

## CI/CD (GitHub Actions)

`.github/workflows/ci.yml` runs on every push/PR:

- **backend**: Python 3.11, Redis service, `ruff check` (lint) + `pytest` (44 tests)
- **frontend**: `npm ci` + `npm run build` (Vite)
- **site**: `npm ci` + `npm run lint` + `npm run build` (Next.js)

## Roadmap

- Prometheus metrics + Grafana dashboards
- OpenTelemetry tracing
- Kubernetes autoscaling
- Redis Cluster (no single point of failure)
- AI-assisted cache-rule suggestions
