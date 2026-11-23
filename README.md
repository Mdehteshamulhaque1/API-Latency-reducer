<div align="center">

# ⚡ API Optimizer

### AI-powered API performance, intelligence and security platform

A FastAPI gateway that sits in front of your HTTP API and makes it **faster**, **safer** and **observable**,
with an LLM gateway, a RAG knowledge base and an assistant that reasons over *measured* data.

<br/>

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?logo=sqlalchemy&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-%7C%20MySQL%20%7C%20SQLite-4169E1?logo=postgresql&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14-000000?logo=nextdotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-k3d-326CE5?logo=kubernetes&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-metrics-E6522C?logo=prometheus&logoColor=white)

**[🌐 Live dashboard](https://api-latency-reducer.vercel.app)** ·
**[🔌 Live API health](https://api-latency-reducer-1.onrender.com/api/v1/health)** ·
**[📐 Architecture PDF](docs/ARCHITECTURE.pdf)** ·
**[🧪 Manual testing](docs/MANUAL_TESTING.md)** ·
**[🗂 Project structure](docs/PROJECT_STRUCTURE.md)**

<sub>The backend runs on Render's free tier, so the first request after idle can take ~30–60 s to wake up.</sub>

</div>

---

## 📖 Table of contents

- [Why this exists](#-why-this-exists)
- [Highlights](#-highlights)
- [Features](#-features)
- [Architecture](#-architecture)
- [Dashboard](#-dashboard)
- [Tech stack](#-tech-stack)
- [Quick start](#-quick-start)
- [Configuration](#%EF%B8%8F-configuration)
- [API reference](#-api-reference)
- [Deep dives](#-deep-dives)
- [Kubernetes deployment & load test](#%EF%B8%8F-kubernetes-deployment-local-k3d-cluster)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Known limitations](#%EF%B8%8F-known-limitations)
- [Roadmap](#%EF%B8%8F-roadmap)

---

## 🎯 Why this exists

> Teams usually discover slow endpoints from **user complaints**, add caching by **guesswork**, and cannot tell what an AI feature **costs** or whether a prompt was **abused**.

**API Optimizer** measures every request, applies caching and rate limits with explicit rules, and puts an assistant on top of the measured data, with every answer showing the facts it was built from.

## ✨ Highlights

<table>
<tr>
<td width="33%" valign="top">

### 🚀 Performance
- Rule-based **Redis response cache**
- **Semantic answer cache** shared across users
- p50 / p95 / p99 latency analytics
- k6 benchmarks: cache on vs off

</td>
<td width="33%" valign="top">

### 🛡️ Security
- JWT auth, **RBAC** (admin · operator · viewer)
- Token-bucket **rate limiting** in Lua
- Prompt-injection detection, **PII masking**
- Full guardrail audit trail

</td>
<td width="33%" valign="top">

### 🤖 AI
- **LLM gateway**: cache, fallback, circuit breaker
- **RAG** knowledge base on ChromaDB
- Assistant grounded on real metrics
- Per-token cost tracking & billing

</td>
</tr>
</table>

**Built for production:**
✅ Redis **fails open**: if Redis is down, requests still succeed
✅ Correlation IDs on every log line and response
✅ Prometheus metrics at `/metrics`
✅ Async end to end
✅ Alembic migrations (`0001` → `0012`)
✅ 227 pytest tests
✅ Runs on SQLite, MySQL or PostgreSQL

---

## 🧩 Features

| | Area | What it does |
| :---: | --- | --- |
| 💾 | **Response caching** | Rules per endpoint pattern: TTL, key by user/query/headers, size budget, priority. Only `GET` + `200` is cached; authenticated responses are keyed per user. Stats and invalidation API. |
| 🚦 | **Rate limiting** | Token bucket in a Redis Lua script, keyed by user or client IP, sized by tier: anonymous **60/min**, signed-in **300/min**, operator and admin **1000/min**. IETF `RateLimit-*` plus `X-RateLimit-*` headers, `Retry-After` on 429. Fails open. |
| 🔐 | **Auth & RBAC** | bcrypt, HS256 access and refresh tokens with `jti`, logout with a Redis revocation denylist. Roles `admin`, `operator`, `viewer`. |
| 📊 | **Analytics** | Totals, error and 429 counts, cache ratio, p50/p95/p99 via SQL window functions, latency series, slow endpoints, benchmark, real-query breakdown. |
| 🧾 | **Structured logging** | JSON logs with a correlation id on every line and in the `X-Correlation-ID` header. No secrets, no bodies. |
| 🧠 | **LLM gateway** | `POST /api/v1/chat`: exact-match cache, retries, primary then fallback model, circuit breaker, Prometheus metrics, estimated cost. |
| 💰 | **AI usage & pricing** | One row per LLM call: tokens, latency, outcome, estimated cost. Per-user token billing on the Pricing page. |
| 🛡️ | **Guardrails** | Prompt-injection heuristics (block on high severity), regex PII masking before the provider call, output validation, grounding score, audit events. |
| 🤖 | **Assistant** | `/api/v1/assistant/ask`: controlled metric tools, facts returned next to the answer, measured vs hypothesis labelling. Cache recommendations (advisory) and troubleshooting. |
| 📚 | **Knowledge base** | Upload PDF/TXT/MD, chunk, embed, store in ChromaDB, semantic search, grounded answers with sources or an explicit "not enough information". |
| 💬 | **Answer engine** | `POST /api/v1/answers`: a shared semantic question cache (exact → embedding → lexical match) with model-first answering and a multi-source web crawler fallback. [Details ↓](#-answer-engine) |
| 👥 | **Users directory** | Admin-only view of every account and monitored end user: traffic, rate-limit bucket, searches, billing, AI usage and guardrail events. Admins can **view the dashboard as** any user. |
| 🛰️ | **Service monitoring** | Analyse another application's traffic (e.g. Esone) via telemetry ingest or a reverse proxy through the gateway. [Details ↓](#%EF%B8%8F-monitoring-another-service-esone) |

---

## 🏗 Architecture

### Request pipeline

```mermaid
flowchart LR
    C([Client]) --> CORS --> M[Metrics] --> CID[CorrelationId] --> A[Auth] --> RL[RateLimit] --> CA[Cache] --> R([Route])
    M -. background task .-> L[(api_logs)]
    RL -. token buckets .-> RD[(Redis)]
    CA -. cached responses .-> RD
```

### AI request flow

```mermaid
flowchart LR
    Q([AI question]) --> G[Guardrails<br/>injection + PII]
    G --> T{Metric tools /<br/>vector retrieval}
    T --> CTX[Context] --> LLM[LLM gateway<br/>cache · fallback · breaker]
    LLM --> V[Output validation<br/>+ sources] --> RES([Response])
    RES -.-> DB[(ai_request_logs<br/>guardrail_events)]
```

**Modular monolith:**

| Layer | Location |
| --- | --- |
| Routes | `app/api/v1` |
| Business logic | `app/services` |
| AI (answers, assistant, guardrails, RAG) | `app/ai` |
| Models / Schemas | `app/models` (SQLAlchemy) · `app/schemas` (Pydantic) |
| Middleware | `app/middleware` |
| Cross-cutting helpers | `app/core`, `app/utils` |

Full description with the data model, failure behaviour and configuration: [`docs/ARCHITECTURE.pdf`](docs/ARCHITECTURE.pdf).

### Repository layout

```
app/             FastAPI backend: api/v1 (routes), services, ai (answers, assistant,
                 guardrails, rag), middleware, models, schemas, core, database, utils
alembic/         migrations 0001..0012
tests/           pytest suite (integration at the top level, unit/ for pure logic)
scripts/         migrate_db.py, seed_demo.py, dev.sh (whole local stack)
site/            Next.js dashboard: app/ (routes), components/, lib/api.ts
esone/           Esone: backend/ (FastAPI) and frontend/ (static Jinja2 + TypeScript)
loadtest/        k6 benchmarks
k8s/             Kubernetes manifests for the local k3d cluster
docs/            architecture, manual test checklist, project structure
```

---

## 🖥 Dashboard

A Next.js 14 console that shows **only real data from real endpoints**. The landing page is a static preview.

| Group | Pages |
| --- | --- |
| **Gateway** | Overview · Analytics · Users *(admin)* · Cache · Rate limits · Cache rules · System status |
| **AI** | LLM gateway · Assistant · Knowledge base · AI usage · Pricing · Guardrails |

- 🔀 **Service switch:** view the gateway's own traffic or a monitored service's
- 👁️ **View as user:** admins pick any user in the top bar and every page is scoped to them
- 🔒 **Role-aware:** admins see everyone's data; other roles see their own

---

## 🧰 Tech stack

| Layer | Technologies |
| --- | --- |
| **Backend** | Python 3.11 · FastAPI · SQLAlchemy 2 (async) · Alembic · Pydantic v2 · httpx |
| **Data** | PostgreSQL / MySQL / SQLite · Redis 7 (`redis.asyncio`) · ChromaDB |
| **Auth** | python-jose (HS256 JWT) · bcrypt |
| **AI** | OpenAI-compatible API (Gemini by default · OpenAI · Ollama) · pypdf |
| **Observability** | prometheus_client · structured JSON logs |
| **Frontend** | Next.js 14 (App Router) · TypeScript strict · Tailwind · recharts · framer-motion · Radix |
| **Testing** | pytest · pytest-asyncio · httpx `ASGITransport` · k6 |
| **Infra** | Docker · Docker Compose · Kubernetes (k3d) · Render · Vercel · Supabase |

---

## 🚀 Quick start

### Prerequisites

- 🐍 Python 3.11
- 🟢 Node 20 (dashboard)
- 🟥 Redis 7 (local install or `docker run -p 6379:6379 redis:7-alpine`)
- 🔑 *Optional:* a Google Gemini API key (default provider), an OpenAI key, or a local Ollama server. **Core features work without any of them.**

### Option A: run everything with one command

Starts Redis (Docker), the API Optimizer API and dashboard, and the Esone API and frontend, and creates any missing `.env` files from the examples:

```bash
bash scripts/dev.sh start     # then open http://localhost:4000 (Esone) and http://localhost:3001 (dashboard)
bash scripts/dev.sh status
bash scripts/dev.sh logs
bash scripts/dev.sh stop      # add --with-redis to stop the Redis container too
```

Requires `venv/` created with both requirements files installed, Node.js and Docker Desktop.

### Option B: step by step

**1️⃣ Backend**

```bash
python -m venv venv
venv/Scripts/activate            # Windows   (source venv/bin/activate on POSIX)
pip install -r requirements.txt
cp .env.example .env             # then edit: SECRET_KEY, ADMIN_PASSWORD, OPENAI_API_KEY (your Gemini key)
python scripts/migrate_db.py     # alembic upgrade head + admin user
uvicorn app.main:app --reload --port 8000
```

✅ `GET http://localhost:8000/api/v1/health` should report `database` and `redis` healthy. With `DEBUG=True` the OpenAPI docs are at `/docs`.

🌱 Optional demo data: `python scripts/seed_demo.py` creates operator and viewer accounts, cache rules, and 24 hours of synthetic request logs.

**2️⃣ Dashboard**

```bash
cd site
npm ci
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                         # http://localhost:3000
```

Sign in with the admin account from `.env`.

**🐳 Or with Docker**

```bash
docker compose up --build     # redis + backend on :8000
```

The backend image runs `python scripts/migrate_db.py` before `uvicorn`. Pass `OPENAI_API_KEY` through your shell or a `.env` file next to the compose file. The dashboard is not containerised; run it with `npm run dev` or deploy it to Vercel.

<details>
<summary><b>🦙 Free local AI with Ollama (no API key)</b></summary>

<br/>

Install [Ollama](https://ollama.com), then:

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

In `.env`:

```
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
OPENAI_MODEL=llama3.2
OPENAI_FALLBACK_MODEL=
EMBEDDING_MODEL=nomic-embed-text
```

</details>

---

## ⚙️ Configuration

All variables, with comments, are in [`.env.example`](.env.example). The important ones:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | `sqlite+aiosqlite:///./api_optimizer.db`, or MySQL / PostgreSQL URLs |
| `REDIS_URL` | cache, token buckets, LLM cache, revoked tokens |
| `SECRET_KEY` | JWT signing, at least 32 characters |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | first admin, created by `scripts/migrate_db.py` |
| `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, `OPENAI_FALLBACK_MODEL` | LLM gateway (Gemini by default; the key is your Gemini key) |
| `LLM_PROVIDER` | provider label in usage rows, logs and metrics (`gemini`) |
| `EMBEDDING_MODEL`, `EMBEDDING_BASE_URL`, `EMBEDDING_API_KEY` | RAG embeddings (default to the gateway values; `gemini-embedding-001`) |
| `CHROMA_PERSIST_DIR` | local vector store directory |
| `GUARDRAILS_BLOCK_INJECTION`, `GUARDRAILS_MASK_PII` | guardrail switches |
| `ANSWERS_CACHE_TTL`, `ANSWERS_VOLATILE_TTL`, `ANSWERS_RECENT_TTL` | answer cache lifetime (2 h, sliding on every hit; 10 min for time-sensitive questions) and the recent-questions window (1 h) |
| `ANSWERS_SIMILARITY_THRESHOLD`, `ANSWERS_MODEL_FIRST`, `ANSWERS_LOCK_TTL`, `ANSWERS_LOCK_WAIT_SECONDS` | semantic match floor (0.92), model-first order, stampede lock |
| `ANSWERS_INR_PER_TOKEN` | per-token billing for non-cached answers (default 5) |
| `EMBEDDING_PRICE_PER_MILLION`, `PRICING_CURRENCY`, `PRICING_EFFECTIVE_DATE` | embedding price for models not in `EMBEDDING_PRICING_TABLE`; cost figures are estimates, never billing |
| `CRAWLER_SOURCES`, `WEB_SEARCH_PROVIDER`, `WEB_SEARCH_API_KEY`, `GOOGLE_CSE_ID`, `CRAWLER_TRUSTED_DOMAINS` | crawler sources; keyed web search is optional |
| `RATE_LIMIT_ANONYMOUS_*`, `RATE_LIMIT_USER_*`, `RATE_LIMIT_PRIVILEGED_*` | bucket capacity and refill period per tier (`_REQUESTS`, `_PERIOD`) |
| `PROXY_UPSTREAMS` | JSON map of services reachable at `/proxy/<service>/...` |
| `CORS_ORIGINS` | JSON array of dashboard origins |
| `DEMO_ENDPOINT_ENABLED` | unauthenticated latency endpoint for benchmarks, off in production |

> [!WARNING]
> Never commit `.env`. Secrets are never logged or returned by the API.

---

## 🔌 API reference

All routes are under `/api/v1`. Protected routes need `Authorization: Bearer <access token>`.
Admins see every user's analytics, usage and events (and can scope reads with `as_user`); other roles see their own.

<details open>
<summary><b>Core gateway</b></summary>

<br/>

| Route | Access | Purpose |
| --- | --- | --- |
| `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout` | public / bearer | accounts and sessions |
| `GET /analytics/summary`, `/endpoints`, `/slow-endpoints`, `/benchmark`, `/suggestions`, `/queries`, `/services` | any role | measured traffic, `hours` 1..720 |
| `POST /analytics/benchmark/run` | any role | schedule a benchmark report |
| `GET\|POST /rules`, `GET\|PUT\|DELETE /rules/{id}` | read any · write admin, operator · delete admin | cache rules |
| `GET /cache/stats`, `POST /cache/invalidate` | any · admin, operator | counters and invalidation |
| `GET /rate-limits/config`, `/rate-limits/me`, `/rate-limits/events` | any role | limiter state and 429s |
| `GET /users`, `/users/detail` | admin | users directory |
| `GET /health`, `GET /ping`, `GET /metrics` | public | probes and Prometheus |

</details>

<details open>
<summary><b>AI</b></summary>

<br/>

| Route | Access | Purpose |
| --- | --- | --- |
| `POST /chat` | any role | LLM gateway, OpenAI-style messages |
| `GET /ai-usage/summary`, `/ai-usage/requests` | any role | tokens, latency, estimated cost |
| `GET /pricing`, `/pricing/users` | any role | pricing table and per-user token billing |
| `GET /guardrails/summary`, `/guardrails/events`, `POST /guardrails/check` | any role | audit trail and dry run |
| `POST /assistant/ask`, `GET /assistant/suggested-questions`, `GET /assistant/cache-recommendations`, `POST /assistant/troubleshoot` | any role | assistant features |
| `POST /documents`, `GET /documents`, `GET\|DELETE /documents/{id}` | upload/delete admin, operator | knowledge base files |
| `POST /knowledge-base/search`, `POST /knowledge-base/ask` | any role | semantic search and grounded answers |
| `POST /answers`, `GET /answers/recent`, `/top`, `/stats`, `/cache`, `/costs`, `/users` | any role (own rows; admins all; `service=` for a monitored service) | question answering, query log, most asked, hit rate, cache contents, cost and savings, per-user totals |

</details>

<details>
<summary><b>Service monitoring</b></summary>

<br/>

| Route | Access | Purpose |
| --- | --- | --- |
| `POST /ingest/requests` | operator, admin | request-log batch from a monitored service (Esone) |
| `ANY /proxy/{service}/{path}` *(no `/api/v1` prefix)* | upstream's own auth | reverse proxy to a `PROXY_UPSTREAMS` service; logged under that service |

</details>

---

## 🔬 Deep dives

<details>
<summary><b>💬 Answer engine</b></summary>

<br/>

`POST /api/v1/answers` is a shared semantic question cache in Redis:

1. **Lookup:** exact match, then embeddings with a lexical fallback. TTL is 2 h, or 10 min for time-sensitive questions. Numbers, dates and words like "today" must agree before two questions share an answer. Questions carrying personal data are never cached.
2. **On a miss:** the model answers from its own knowledge first (it must say `UNKNOWN` when unsure, and is skipped for time-sensitive questions), then Wikipedia, then DuckDuckGo, Wikidata and an optional keyed web search (Brave or Google, trusted domains first, pages fetched and reduced to text). The answer is composed by the LLM from the pages or quoted from the best page. `ANSWERS_MODEL_FIRST=False` restores sources-first.
3. **Logging:** every request writes its own `answer_logs` row per caller and end user (`user_ref`), including shared cache hits and blocked or failed requests, with cache key, latency components, tokens and estimated cost. A Redis list keeps the last hour.
4. **Billing:** non-cached answers are billed per token in INR (`ANSWERS_INR_PER_TOKEN`, default 5). Cache hits and RAG are free. The dashboard's Pricing page shows each user's charges.

Esone's chat uses this engine and keeps each user's private query log.

</details>

<details>
<summary><b>🗄 Database</b></summary>

<br/>

The schema is managed by Alembic (`alembic/versions`). `python scripts/migrate_db.py` runs `alembic upgrade head` and seeds the admin.

```bash
alembic current
alembic upgrade head
alembic downgrade -1
```

SQLite is the default and runs in WAL mode; MySQL and PostgreSQL work via `DATABASE_URL`.

**Tables:** `users`, `cache_rules`, `api_logs`, `ai_request_logs`, `answer_logs`, `guardrail_events`, `documents`, `document_chunks`, `end_users`. The old hourly roll-up table was removed (revision 0005): every number is aggregated from `api_logs` directly.

</details>

<details>
<summary><b>🟥 Redis keys</b></summary>

<br/>

| Key | Holds |
| --- | --- |
| `rule:*` | cached responses |
| `chat:*` | LLM responses |
| `answers:q:*` | shared answers (question, answer, sources, embedding, generating model, original tokens and cost, timestamps, hit count; 2 h sliding TTL) |
| `answers:lock:*` | generation locks (stampede protection) |
| `answers:stats:stored` | entries-written counter |
| `answers:recent` | last hour of asked questions |
| `rate_limit:*` | token buckets |
| `auth:revoked:*` | revoked token ids |
| `cache:stats:*` | hit/miss counters |

Every feature fails open: with Redis down, requests still succeed without caching, limiting or revocation checks, and `/health` reports `degraded`.

</details>

<details>
<summary><b>📚 RAG pipeline</b></summary>

<br/>

1. **Upload** (`POST /documents`): type and size validation, SHA-256 duplicate check, text extraction (pypdf for PDF), cleaning.
2. **Scan:** the text is scanned for instruction-like content; matches flag the document and record a `document_flagged` event. It is still indexed.
3. **Chunk:** paragraph-aware, `RAG_CHUNK_SIZE` characters with `RAG_CHUNK_OVERLAP`.
4. **Embed** through an OpenAI-compatible `/embeddings` endpoint.
5. **Store:** vectors plus chunk text and metadata go to ChromaDB (cosine space); chunk text and metadata also go to SQL, which is the source of truth for listing and deletion.
6. **Search** embeds the query, takes the top `k`, drops results below `RAG_MIN_SIMILARITY`, and hydrates only chunks whose document is `ready`.
7. **Answer:** chunks are wrapped in numbered `<source>` blocks, the model is told they are data and not instructions, inline citations are required, and the fixed "not enough information" reply is returned (without calling the model) when nothing relevant was found. A lexical grounding score is reported with every answer.

</details>

<details>
<summary><b>🧠 LLM gateway</b></summary>

<br/>

The gateway speaks the OpenAI Chat Completions protocol to `OPENAI_BASE_URL`, which defaults to Gemini's OpenAI-compatible endpoint.

- Requests at temperature 0 are cached by exact match (successful responses only).
- Retry-eligible failures (timeouts, 429, 5xx) go to `OPENAI_FALLBACK_MODEL`.
- Repeated failures open a process-local circuit breaker for `LLM_CIRCUIT_COOLDOWN_SECONDS`.

**Prometheus metrics** at `/metrics`: `chat_requests_total`, `chat_provider_latency_seconds`, `chat_request_latency_seconds`, token counters, `chat_estimated_cost_usd_total`, `chat_fallback_total`, `chat_circuit_breaker_state`.

Cost estimates use `PRICING_TABLE` in `app/config.py` (USD per million tokens) and are labelled as estimates everywhere they appear.

</details>

<details>
<summary><b>🛡️ Guardrails</b></summary>

<br/>

- **Input:** every caller-supplied message is scanned against named prompt-injection rules. `high` severity blocks the request with `error_code=GUARDRAIL_BLOCKED` when `GUARDRAILS_BLOCK_INJECTION=True`; lower severities are allowed and recorded.
- **PII:** emails, phone numbers and Luhn-valid card numbers are replaced with placeholders before text leaves the service.
- **Output:** answers are validated (non-empty, bounded) and scored against the facts or sources that were provided; low scores are recorded.
- **Audit:** `guardrail_events` stores category, severity, feature, a short detail (rule names or counts) and whether the request was blocked. Prompts and documents are never stored there.
- **Limitations:** detection is heuristic. Paraphrased or encoded injections, other languages, names and addresses are not caught. Microsoft Presidio can replace `app/ai/guardrails/pii.py` behind the same `mask_text` function.

</details>

<details>
<summary><b>🛰️ Monitoring another service (Esone)</b></summary>

<br/>

The dashboard can analyse a different application's traffic instead of the gateway's own.

**Telemetry ingest:** Esone ships one record per request it served (`inbound`) and per call it made to another host (`outbound`) to `POST /api/v1/ingest/requests` (operator or admin role), batched every `ESONE_TELEMETRY_FLUSH_SECONDS` by `esone_api/telemetry.py`. Rows land in `api_logs` with `service`, `direction` and `upstream_host`, and every analytics read takes `?service=esone` (plus optional `direction=inbound|outbound`). `GET /api/v1/analytics/services` lists the services with data; the dashboard's service switch defaults to the first monitored one. Inbound and outbound rows share a correlation id, returned to Esone's callers as `X-Correlation-ID`.

The ingest calls count against the service account's rate limit. The account must be operator, so the privileged tier `RATE_LIMIT_PRIVILEGED_REQUESTS` applies; give that tier enough headroom.

**Reverse proxy:** `PROXY_UPSTREAMS={"esone":"http://localhost:8000"}` makes `/proxy/esone/<path>` forward to Esone and return its response unchanged. Point the service's frontend at `http://<gateway>/proxy/esone` and every call passes through this gateway's middleware:

- recorded under `service=esone` as it happens (no 30 s telemetry delay)
- rate limited per client address
- cached when a rule whose pattern starts with `/proxy/esone/` matches

Gateway rules never apply to proxied paths, and a proxied request that carries credentials is cached only by a rule that keys on headers. The upstream keeps authenticating its own users; the gateway forwards `X-Forwarded-For`, `X-Correlation-ID` and `X-Proxied-By`, and records an upstream `X-Cache-Hit: true` as a cache hit. Esone skips its own inbound telemetry for proxied requests so nothing is counted twice.

</details>

---

## ☸️ Kubernetes deployment (local k3d cluster)

The gateway also runs on a local Kubernetes cluster (k3d / k3s) with PostgreSQL, Redis, an Ingress and a Horizontal Pod Autoscaler. Everything runs on a laptop; no cloud account is needed.

```mermaid
flowchart LR
    U([Browser / k6]) --> P[localhost:8085]
    P --> I[Traefik Ingress] --> S[Service: gateway]
    S --> G1[gateway pod]
    S --> G2[gateway pod]
    S -.HPA 2–4.-> G3[gateway pod …]
    G1 & G2 --> PG[(PostgreSQL 16<br/>1 Gi PV)]
    G1 & G2 --> RD[(Redis 7)]
```

### 📊 Load test results

k6, 5.5 minutes, ramping to **150 requests/second held for 3 minutes**, hitting `/api/v1/health` (DB check + Redis check + one analytics insert per request). The cluster, k6 and other apps all ran on the same laptop, so these are laptop numbers, not production numbers.

| | Run 1: DB pool 5 + 2 | Run 2: DB pool 10 + 5 |
|---|---|---|
| Requests completed | 30,474 of 37,349 (6,875 dropped) | ✅ **37,349 of 37,349** |
| Failed requests | 56 non-200 (+ DB failures the test did not catch) | ✅ **0** |
| `"database": "healthy"` check | not checked | ✅ **100%** |
| p95 latency | 17.9 ms | ✅ **11.9 ms** |
| Max latency | 30.5 s | ✅ **0.22 s** |
| DB pool timeout errors in logs | hundreds | ✅ **0** |
| Autoscaling | 2 → 4 pods | 2 → 4 pods (and back to 2 after the test) |

> [!NOTE]
> **What happened:** Run 1 passed the k6 thresholds, but the logs showed
> `QueuePool limit of size 5 overflow 2 reached, connection timed out, timeout 30.00`.
> Every request uses the database twice (health check + analytics insert), so each pod's 7 connections ran out at 150 req/s and requests waited 30 seconds for a connection. The health endpoint also returns HTTP 200 when its DB check fails, so the k6 test was extended to assert `"database": "healthy"`. Raising the pool size through the ConfigMap (no code change) fixed it.

<details>
<summary><b>📁 Manifests</b></summary>

<br/>

| File | What it does |
|---|---|
| `k8s/redis.yaml` | Redis Deployment + Service |
| `k8s/postgres.yaml` | PostgreSQL Deployment + 1 Gi PersistentVolumeClaim + Service, `pg_isready` readiness probe |
| `k8s/config.yaml` | ConfigMap with non-secret settings (Redis URL, DB pool size, rate limiting) |
| `k8s/gateway.yaml` | Gateway Deployment (2 replicas, probes, CPU/memory requests) + Service |
| `k8s/ingress.yaml` | Traefik Ingress → gateway on `localhost:8085` |
| `k8s/hpa.yaml` | HorizontalPodAutoscaler: 2–4 pods, target 50% CPU |
| `loadtest/k8s-rush.js` | k6 load test: ramps to 150 req/s and checks status + DB health |

</details>

<details>
<summary><b>▶️ Run it</b></summary>

<br/>

```powershell
# 1. Cluster (port 8085 on the laptop → Ingress)
k3d cluster create apiopt -p "8085:80@loadbalancer"

# 2. Build the image and load it into the cluster (no registry needed)
docker build -t api-optimizer:v1 .
k3d image import api-optimizer:v1 -c apiopt

# 3. Secrets are created with kubectl, never committed to Git (replace the placeholder values)
kubectl create secret generic postgres-secret --from-literal=POSTGRES_USER=apiopt --from-literal=POSTGRES_PASSWORD=changeme --from-literal=POSTGRES_DB=apiopt
kubectl create secret generic apiopt-secrets --from-literal=SECRET_KEY=change-me-to-a-long-random-string --from-literal=ADMIN_EMAIL=admin@apioptimizer.dev --from-literal=ADMIN_PASSWORD=ChangeMe@12345 --from-literal=DATABASE_URL=postgresql+asyncpg://apiopt:changeme@postgres:5432/apiopt

# 4. Everything else
kubectl apply -f k8s/
kubectl get pods,svc,ingress,hpa,pvc

# 5. Check
curl http://127.0.0.1:8085/api/v1/health
# {"status":"healthy","version":"1.0.0","database":"healthy","redis":"healthy"}
```

</details>

<details>
<summary><b>🧠 Design decisions</b></summary>

<br/>

- **Secrets vs config:** passwords, the JWT secret and the DB URL live in Kubernetes Secrets created with `kubectl`; non-secret settings live in a ConfigMap. Nothing secret is in Git.
- **Probes:** readiness = HTTP `/api/v1/health` (pod gets traffic only when ready); liveness = TCP port 8000 (only "is the process alive?"). Liveness deliberately does **not** check the database, so a short DB outage does not restart every gateway pod. Verified: deleting the Postgres pod left all gateway pods at `RESTARTS 0`, and the data survived on the PersistentVolume.
- **Rolling updates:** new pods come up one at a time and only replace old ones after passing readiness, so the database migration that runs at container start never runs twice at the same moment.
- **Autoscaling:** HPA on CPU (request 100m, target 50%), min 2 / max 4 pods (max kept low because it runs on a laptop).
- **Connection pool math:** (pool 10 + overflow 5) × 4 pods = 60 connections, below PostgreSQL's `max_connections` of 100.

**Next steps:** single-node cluster with k6 on the same machine; migrations run at container start (a Job or init container would be cleaner); analytics are written per request (batching would cut DB load); rate limiting was switched off only during the load test (all k6 traffic comes from one IP).

</details>

<details>
<summary><b>📸 Screenshots</b></summary>

<br/>

| | |
|---|---|
| Health check through the Ingress | ![Health](docs/k8s/health-ingress.png) |
| Cluster overview: pods, services, Ingress, HPA, PVC | ![HPA](docs/k8s/hpa-scaling.png) |
| HPA scaling events (2 → 3 → 4 → 2) | ![HPA events](docs/k8s/hpa-events.png) |
| k6 result after the fix | ![k6](docs/k8s/k6-summary.png) |

</details>

---

## 🧪 Testing

```bash
pytest -q          # needs a local Redis; uses DB 15 and a temp ChromaDB dir
ruff check .
cd site && npm run lint && npx tsc --noEmit && npm run build
```

The suite covers auth and revocation, caching and invalidation, the rate limiter and its headers, analytics maths against seeded rows, Prometheus metrics, AI usage persistence, guardrails, the RAG pipeline end to end (fake embeddings, real ChromaDB in a temp dir), and the assistant, recommendation and troubleshooting services with a fake provider.

### Cache benchmark (k6)

```bash
python scripts/seed_demo.py                    # creates the demo cache rule
CACHE=off k6 run loadtest/benchmark.js
CACHE=on  k6 run loadtest/benchmark.js
```

The script drives `GET /api/v1/demo/latency` (needs `DEMO_ENDPOINT_ENABLED=True`), which simulates a 150 ms upstream. Report your own numbers with the VU count, duration, machine and database used; results depend heavily on the environment.

---

## 🌍 Deployment

| Component | Platform | Notes |
| --- | --- | --- |
| Backend | **Render** | `render.yaml` describes the service; set the `sync: false` variables in the Render dashboard. `scripts/migrate_db.py` runs as the pre-deploy command. ChromaDB is on local disk, so a persistent disk (or a managed vector store) is needed for the knowledge base to survive deploys. |
| Dashboard | **Vercel** | Import `site/`, set `NEXT_PUBLIC_API_URL` to the backend URL, and add the Vercel origin to `CORS_ORIGINS`. |
| Database | **Supabase** (PostgreSQL) | Any PostgreSQL works through `DATABASE_URL` (`postgresql+asyncpg://...`). |

---

## ⚠️ Known limitations

- Circuit breaker, Prometheus counters and guardrail rules are **process-local**; multiple workers do not share them.
- Prompt-injection and PII detection are **heuristics** (see Guardrails).
- The grounding score is lexical and can under-score short numeric answers.
- ChromaDB persists to local disk; there is no multi-node vector store.
- Analytics are scoped per user; there is no cross-tenant isolation beyond roles.
- `answer_logs` stores the question and answer text (the dashboard shows them); LLM prompts elsewhere are still never stored.
- Cost figures (LLM, embedding, savings) are **estimates** from the pricing tables in `app/config.py`, checked on `PRICING_EFFECTIVE_DATE`; they are not provider billing. "Expired" cache entries are estimated as entries written minus entries present. The semantic lookup scans up to 500 entries linearly; a vector index would be needed well beyond that.
- Stampede protection and the answer cache are per Redis instance; the generation lock is best effort (a crashed generator blocks identical questions for at most `ANSWERS_LOCK_TTL` seconds). Keyed web search and page fetching reach the open web: results are ranked by trusted domain but not fact-checked.
- Background tasks run in-process; a crash can lose the last usage row.

## 🗺️ Roadmap

- [ ] Presidio-based PII detection, multi-language injection rules
- [ ] Refresh-token rotation on every refresh
- [ ] Alembic autogenerate checks in CI
- [ ] OpenTelemetry tracing and shared breaker state across workers
- [ ] Managed vector store option for multi-instance deployments
- [ ] Run migrations as a Kubernetes Job; batch analytics writes

---

<div align="center">

**Built with FastAPI, Redis and Next.js** · [Report an issue](https://github.com/Mdehteshamulhaque1/API-Latency-reducer/issues)

⭐ If this project helped you, consider giving it a star!

</div>
