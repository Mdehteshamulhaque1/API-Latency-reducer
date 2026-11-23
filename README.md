# API Optimizer

AI-powered API performance, intelligence and security platform.

A FastAPI gateway that sits in front of an HTTP API and makes it faster,
safer, and observable: Redis response caching, token-bucket rate limiting,
per-request analytics, an LLM gateway with fallback and a circuit breaker,
a RAG knowledge base over uploaded documentation, an assistant that reasons
over measured data, and basic AI guardrails. A Next.js dashboard shows all
of it from real endpoints only.

Architecture document: [`docs/ARCHITECTURE.pdf`](docs/ARCHITECTURE.pdf)
(source: `docs/ARCHITECTURE.html`). Manual test checklist:
[`docs/MANUAL_TESTING.md`](docs/MANUAL_TESTING.md). Repository layout:
[`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md).

---

## Problem statement

Teams usually discover slow endpoints from user complaints, add caching by
guesswork, and cannot tell what an AI feature costs or whether a prompt was
abused. API Optimizer measures every request, applies caching and limits
with explicit rules, and puts an assistant on top of the measured data,
with every answer showing the facts it was built from.

## Features

| Area | What it does |
| --- | --- |
| Response caching | Rules per endpoint pattern: TTL, key by user/query/headers, size budget, priority. Only `GET` + `200` is cached; authenticated responses are keyed per user. Stats and invalidation API. |
| Rate limiting | Token bucket in a Redis Lua script, keyed by user or client IP, sized by tier: anonymous 60/min, signed-in 300/min, operator and admin 1000/min. IETF `RateLimit-*` plus `X-RateLimit-*` headers, `Retry-After` on 429. Fails open. |
| Auth and RBAC | bcrypt, HS256 access and refresh tokens with `jti`, logout with a Redis revocation denylist. Roles `admin`, `operator`, `viewer`. |
| Analytics | Totals, error and 429 counts, cache ratio, p50/p95/p99 via SQL window functions, latency series, slow endpoints, benchmark. |
| Structured logging | JSON logs with a correlation id on every line and in the `X-Correlation-ID` header. No secrets, no bodies. |
| LLM gateway | `POST /api/v1/chat`: exact-match cache, retries, primary then fallback model, circuit breaker, Prometheus metrics, estimated cost. |
| AI usage | One row per LLM call: tokens, latency, outcome, estimated cost. `/api/v1/ai-usage`. |
| Guardrails | Prompt-injection heuristics (block on high severity), regex PII masking before the provider call, output validation, grounding score, audit events. |
| Assistant | `/api/v1/assistant/ask`: controlled metric tools, facts returned next to the answer, measured vs hypothesis labelling. Cache recommendations (advisory) and troubleshooting. |
| Knowledge base | Upload PDF/TXT/MD, chunk, embed, store in ChromaDB, semantic search, grounded answers with sources or an explicit "not enough information". |
| Dashboard | Next.js 14 console: overview, analytics, cache, rate limits, cache rules, assistant, knowledge base, LLM gateway, AI usage, AI security, status. |
| Answers | `POST /api/v1/answers`: a shared semantic question cache in Redis (exact match, then embeddings with a lexical fallback; 2 h TTL, 10 min for time-sensitive questions; numbers, dates and words like "today" must agree before two questions share an answer; questions carrying personal data are never cached), on a miss the model answers from its own knowledge first (it must say UNKNOWN when unsure, and is skipped for time-sensitive questions), then Wikipedia, then DuckDuckGo, Wikidata and an optional keyed web search (Brave or Google, trusted domains first, pages fetched and reduced to text), with the answer composed by the LLM from the pages or quoted from the best page; `ANSWERS_MODEL_FIRST=False` restores sources-first. Every request writes its own `answer_logs` row per caller and end user (`user_ref`), including shared cache hits, blocked and failed requests, with cache key, latency components, tokens and estimated cost; a Redis list keeps the last hour. `GET /api/v1/answers/recent`, `/top` and `/stats` (optionally `?end_user=`) feed the dashboard's Answer cache page. Esone's chat uses this and keeps each user's private query log. Non-cached answers are billed per token in INR (`ANSWERS_INR_PER_TOKEN`, default 5); cache hits and RAG are free; the dashboard's Pricing page shows each user's charges. |

## Architecture

```
client ──► CORS ──► Metrics ──► CorrelationId ──► Auth ──► RateLimit ──► Cache ──► route
                       │                                       │            │
                       │                                       │            └─ Redis response cache
                       │                                       └─ Redis token buckets
                       └─ api_logs + hourly analytics (background task)

AI question ──► guardrails ──► metric tools / vector retrieval ──► context ──► LLM gateway
            ──► output validation + sources ──► response ──► ai_request_logs + guardrail_events
```

Modular monolith: `app/api/v1` (routers), `app/services` (business logic),
`app/ai` (guardrails, assistant, RAG), `app/models` (SQLAlchemy),
`app/schemas` (Pydantic), `app/middleware`. Full description with the data
model, failure behaviour, and configuration in `docs/ARCHITECTURE.pdf`.

## Tech stack

Python 3.11, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2, Redis
(`redis.asyncio`), httpx, python-jose, bcrypt, prometheus_client, ChromaDB,
pypdf. Dashboard: Next.js 14, TypeScript strict, Tailwind, recharts.
Tests: pytest, pytest-asyncio, httpx `ASGITransport`. Load test: k6.

## Repository layout

```
app/             FastAPI backend: api/v1 (routes), services, ai (answers, assistant,
                 guardrails, rag), middleware, models, schemas, core, database, utils
alembic/         migrations 0001..0012
tests/           pytest suite (integration at the top level, unit/ for pure logic)
scripts/         migrate_db.py, seed_demo.py, dev.sh (whole local stack)
site/            Next.js dashboard: app/ (routes), components/, lib/api.ts
esone/           Esone: backend/ (FastAPI) and frontend/ (static Jinja2 + TypeScript)
loadtest/        k6 benchmark
k8s/             Kubernetes manifests for the local k3d cluster (see "Kubernetes deployment")
docs/            architecture, manual test checklist, project structure
```

Details and conventions: [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md).

## Run everything locally

One command starts Redis (Docker), the API Optimizer API and dashboard, and
the Esone API and frontend, creating any missing `.env` files from the
examples:

```bash
bash scripts/dev.sh start     # then open http://localhost:4000 (Esone) and http://localhost:3001 (dashboard)
bash scripts/dev.sh status
bash scripts/dev.sh logs
bash scripts/dev.sh stop      # add --with-redis to stop the Redis container too
```

Requires Python (with `venv/` created and both requirements files installed),
Node.js and Docker Desktop.

## Getting started

### Prerequisites

- Python 3.11
- Node 20 (dashboard)
- Redis 7 (local install or `docker run -p 6379:6379 redis:7-alpine`)
- A Google Gemini API key (default provider, via Gemini's OpenAI-compatible
  endpoint), an OpenAI API key, or a local Ollama server, for the AI
  features. The core features work without any of them.

### 1. Backend

```bash
python -m venv venv
venv/Scripts/activate            # Windows   (source venv/bin/activate on POSIX)
pip install -r requirements.txt
cp .env.example .env             # then edit: SECRET_KEY, ADMIN_PASSWORD, OPENAI_API_KEY (your Gemini key)
python scripts/migrate_db.py             # alembic upgrade head + admin user
uvicorn app.main:app --reload --port 8000
```

`GET http://localhost:8000/api/v1/health` should report `database` and
`redis` healthy. With `DEBUG=True` the OpenAPI docs are at `/docs`.

Optional demo data: `python scripts/seed_demo.py` creates operator and viewer
accounts, cache rules, and 24 hours of synthetic request logs.

### 2. Dashboard

```bash
cd site
npm ci
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                         # http://localhost:3000
```

Sign in with the admin account from `.env`.

### Free local AI (no key)

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

## Environment variables

All variables, with comments, are in `.env.example`. The important ones:

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
| `ANSWERS_CACHE_TTL`, `ANSWERS_VOLATILE_TTL`, `ANSWERS_RECENT_TTL` | answer cache lifetime (2 h, sliding on every hit; 10 min for time-sensitive questions) and the fast recent-questions window (1 h) |
| `ANSWERS_SIMILARITY_THRESHOLD`, `ANSWERS_MODEL_FIRST`, `ANSWERS_LOCK_TTL`, `ANSWERS_LOCK_WAIT_SECONDS` | semantic match floor (0.92), model-first order, stampede lock |
| `EMBEDDING_PRICE_PER_MILLION`, `PRICING_CURRENCY`, `PRICING_EFFECTIVE_DATE` | embedding price for models not in `EMBEDDING_PRICING_TABLE`; cost figures are estimates, never billing |
| `CRAWLER_SOURCES`, `WEB_SEARCH_PROVIDER`, `WEB_SEARCH_API_KEY`, `GOOGLE_CSE_ID`, `CRAWLER_TRUSTED_DOMAINS` | crawler sources; keyed web search is optional |
| `RATE_LIMIT_ANONYMOUS_*`, `RATE_LIMIT_USER_*`, `RATE_LIMIT_PRIVILEGED_*` | bucket capacity and refill period per tier (`_REQUESTS`, `_PERIOD`) |
| `CORS_ORIGINS` | JSON array of dashboard origins |
| `DEMO_ENDPOINT_ENABLED` | unauthenticated latency endpoint for benchmarks, off in production |

Never commit `.env`. Secrets are never logged or returned by the API.

## API overview

All routes are under `/api/v1`. Protected routes need
`Authorization: Bearer <access token>`.

| Route | Access | Purpose |
| --- | --- | --- |
| `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout` | public / bearer | accounts and sessions |
| `GET /analytics/summary`, `/analytics/endpoints`, `/analytics/slow-endpoints`, `/analytics/benchmark`, `/analytics/suggestions` | any role | measured traffic, `hours` 1..720 |
| `GET|POST /rules`, `GET|PUT|DELETE /rules/{id}` | read any · write admin, operator · delete admin | cache rules |
| `GET /cache/stats`, `POST /cache/invalidate` | any · admin, operator | counters and invalidation |
| `GET /rate-limits/config`, `/rate-limits/me`, `/rate-limits/events` | any role | limiter state and 429s |
| `POST /chat` | any role | LLM gateway, OpenAI-style messages |
| `POST /ingest/requests` | operator, admin | request-log batch from a monitored service (Esone) |
| `ANY /proxy/{service}/{path}` | upstream's own auth | reverse proxy to a `PROXY_UPSTREAMS` service; logged under that service |
| `GET /analytics/services` | any role | services with request rows: this gateway and monitored ones |
| `GET /ai-usage/summary`, `/ai-usage/requests` | any role | tokens, latency, estimated cost |
| `GET /guardrails/summary`, `/guardrails/events`, `POST /guardrails/check` | any role | audit trail and dry run |
| `POST /assistant/ask`, `GET /assistant/suggested-questions`, `GET /assistant/cache-recommendations`, `POST /assistant/troubleshoot` | any role | assistant features |
| `POST /documents`, `GET /documents`, `GET|DELETE /documents/{id}` | upload/delete admin, operator | knowledge base files |
| `POST /knowledge-base/search`, `POST /knowledge-base/ask` | any role | semantic search and grounded answers |
| `POST /answers`, `GET /answers/recent`, `/answers/top`, `/answers/stats`, `/answers/cache`, `/answers/costs`, `/answers/users` | any role (own rows; admins all; `service=` for a monitored service) | question answering; per-caller query log (paginated, `end_user` and `cache_status` filters), most asked, hit rate, what the shared cache holds, LLM vs embedding cost and estimated savings, per-user totals |
| `GET /health`, `GET /ping`, `GET /metrics` | public | probes and Prometheus |

Admins see every user's analytics, usage, and events; other roles see their
own.

## Database

Schema is managed by Alembic (`alembic/versions`). `python scripts/migrate_db.py`
runs `alembic upgrade head` and seeds the admin. Useful commands:

```bash
alembic current
alembic upgrade head
alembic downgrade -1
```

SQLite is the default and runs in WAL mode; MySQL and PostgreSQL work via
`DATABASE_URL`. Tables: `users`, `cache_rules`, `api_logs`,
`ai_request_logs`, `answer_logs`, `guardrail_events`, `documents`, `document_chunks`.
The old hourly roll-up table was removed (revision 0005): every number is
aggregated from `api_logs` directly.

## Redis

Keys: `rule:*` cached responses, `chat:*` LLM responses, `answers:q:*`
shared answers (question, answer, sources, embedding, generating model and
its original tokens and cost, created / last-accessed / expires, hit count;
2 h sliding TTL), `answers:lock:*` generation locks (stampede protection),
`answers:stats:stored` entries-written counter, `answers:recent` the last
hour of asked questions, `rate_limit:*` token buckets, `auth:revoked:*`
revoked token ids, `cache:stats:*` hit/miss counters. Every feature fails open: with Redis down, requests
still succeed without caching, limiting, or revocation checks, and
`/health` reports `degraded`.

## RAG pipeline

1. Upload (`POST /documents`): type and size validation, SHA-256 duplicate
   check, text extraction (pypdf for PDF), cleaning.
2. The text is scanned for instruction-like content; matches flag the
   document and record a `document_flagged` event. It is still indexed.
3. Chunking: paragraph-aware, `RAG_CHUNK_SIZE` characters with
   `RAG_CHUNK_OVERLAP`.
4. Embedding through an OpenAI-compatible `/embeddings` endpoint.
5. Vectors plus chunk text and metadata go to ChromaDB (cosine space);
   chunk text and metadata also go to SQL, which is the source of truth for
   listing and deletion.
6. Search embeds the query, takes the top `k`, drops results below
   `RAG_MIN_SIMILARITY`, and hydrates only chunks whose document is `ready`.
7. Answering wraps the chunks in numbered `<source>` blocks, tells the model
   they are data and not instructions, requires inline citations, and
   returns the fixed "not enough information" reply (without calling the
   model) when nothing relevant was found. A lexical grounding score is
   reported with every answer.

## LLM configuration

The gateway speaks the OpenAI Chat Completions protocol to
`OPENAI_BASE_URL`, which defaults to Gemini's OpenAI-compatible endpoint. Requests at temperature 0 are cached by exact match.
Failures that are retry-eligible (timeouts, 429, 5xx) go to
`OPENAI_FALLBACK_MODEL`; repeated failures open a process-local circuit
breaker for `LLM_CIRCUIT_COOLDOWN_SECONDS`. Metrics at `/metrics`:
`chat_requests_total`, `chat_provider_latency_seconds`,
`chat_request_latency_seconds`, token counters,
`chat_estimated_cost_usd_total`, `chat_fallback_total`,
`chat_circuit_breaker_state`.

Cost estimates use `PRICING_TABLE` in `app/config.py` (USD per million
tokens) and are labelled as estimates everywhere they appear.

## Guardrails

- Input: every caller-supplied message is scanned against named
  prompt-injection rules; `high` severity blocks the request with
  `error_code=GUARDRAIL_BLOCKED` when `GUARDRAILS_BLOCK_INJECTION=True`,
  lower severities are allowed and recorded.
- PII: emails, phone numbers, and Luhn-valid card numbers are replaced with
  placeholders before text leaves the service.
- Output: answers are validated (non-empty, bounded) and scored against the
  facts or sources that were provided; low scores are recorded.
- Audit: `guardrail_events` stores category, severity, feature, a short
  detail (rule names or counts), and whether the request was blocked.
  Prompts and documents are never stored there.
- Limitations: detection is heuristic. Paraphrased or encoded injections,
  other languages, names, and addresses are not caught. Microsoft Presidio
  can replace `app/ai/guardrails/pii.py` behind the same `mask_text`
  function.

## Monitoring another service (Esone)

The dashboard can analyse a different application's traffic instead of the
gateway's own. Esone ships one record per request it served ("inbound") and
per call it made to another host ("outbound") to
`POST /api/v1/ingest/requests` (operator or admin role), batched every
`ESONE_TELEMETRY_FLUSH_SECONDS` by `esone_api/telemetry.py`. Rows land in
`api_logs` with `service`, `direction` and `upstream_host`, and every
analytics read takes `?service=esone` (plus optional
`direction=inbound|outbound`). `GET /api/v1/analytics/services` lists the
services with data; the dashboard's service switch defaults to the first
monitored one. Inbound and outbound rows share a correlation id, returned to
Esone's callers as `X-Correlation-ID`.

The ingest calls count against the service account's rate limit
(the account must be operator, so the privileged tier
`RATE_LIMIT_PRIVILEGED_REQUESTS` applies); give that tier enough headroom.

### Proxying the service through the gateway

`PROXY_UPSTREAMS={"esone":"http://localhost:8000"}` makes
`/proxy/esone/<path>` forward to Esone and return its response unchanged.
Point the service's frontend at `http://<gateway>/proxy/esone` and every call
passes through this gateway's middleware: it is recorded under `service=esone`
as it happens (no 30 s telemetry delay), rate limited per client address, and
cached when a rule whose pattern starts with `/proxy/esone/` matches. Gateway
rules never apply to proxied paths, and a proxied request that carries
credentials is cached only by a rule that keys on headers. The upstream keeps
authenticating its own users; the gateway forwards `X-Forwarded-For`,
`X-Correlation-ID` and `X-Proxied-By`, and records an upstream
`X-Cache-Hit: true` as a cache hit. Esone skips its own inbound telemetry for
proxied requests so nothing is counted twice.

## Testing

```bash
pytest -q          # needs a local Redis; uses DB 15 and a temp ChromaDB dir
ruff check .
cd site && npm run lint && npx tsc --noEmit && npm run build
```

The suite covers auth and revocation, caching and invalidation, the rate
limiter and its headers, analytics maths against seeded rows, Prometheus
metrics, AI usage persistence, guardrails, the RAG pipeline end to end
(fake embeddings, real ChromaDB in a temp dir), and the assistant,
recommendation, and troubleshooting services with a fake provider.

## Load test

```bash
python scripts/seed_demo.py                    # creates the demo cache rule
CACHE=off k6 run loadtest/benchmark.js
CACHE=on  k6 run loadtest/benchmark.js
```

The script drives `GET /api/v1/demo/latency` (needs
`DEMO_ENDPOINT_ENABLED=True`), which simulates a 150 ms upstream. Report
your own numbers with the VU count, duration, machine, and database used;
results depend heavily on the environment.

## Docker

```bash
docker compose up --build     # redis + backend on :8000
```

The backend image runs `python scripts/migrate_db.py` before `uvicorn`. Pass
`OPENAI_API_KEY` through your shell or a `.env` file next to the compose
file. The dashboard is not containerised; run it with `npm run dev` or
deploy it to Vercel.

## Kubernetes deployment (local k3d cluster)

The gateway also runs on a local Kubernetes cluster (k3d / k3s) with PostgreSQL, Redis, an Ingress and a Horizontal Pod Autoscaler. Everything runs on a laptop — no cloud account needed.

### Architecture

```
Browser / k6
     │
     ▼
localhost:8085 ──► Traefik Ingress ──► Service "gateway" ──► gateway pods (2–4, scaled by HPA)
                                                               │
                                                               ├──► Service "postgres" ──► PostgreSQL 16 (1 Gi PersistentVolume)
                                                               └──► Service "redis"    ──► Redis 7
```

### Files

| File | What it does |
|---|---|
| `k8s/redis.yaml` | Redis Deployment + Service |
| `k8s/postgres.yaml` | PostgreSQL Deployment + 1 Gi PersistentVolumeClaim + Service, `pg_isready` readiness probe |
| `k8s/config.yaml` | ConfigMap with non-secret settings (Redis URL, DB pool size, rate limiting) |
| `k8s/gateway.yaml` | Gateway Deployment (2 replicas, probes, CPU/memory requests) + Service |
| `k8s/ingress.yaml` | Traefik Ingress → gateway on `localhost:8085` |
| `k8s/hpa.yaml` | HorizontalPodAutoscaler: 2–4 pods, target 50% CPU |
| `loadtest/k8s-rush.js` | k6 load test: ramps to 150 req/s and checks status + DB health |

### Run it

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

### Design decisions

- **Secrets vs config:** passwords, the JWT secret and the DB URL live in Kubernetes Secrets created with `kubectl`; non-secret settings live in a ConfigMap. Nothing secret is in Git.
- **Probes:** readiness = HTTP `/api/v1/health` (pod gets traffic only when ready); liveness = TCP port 8000 (only "is the process alive?"). Liveness deliberately does **not** check the database, so a short DB outage does not restart every gateway pod. Verified: deleting the Postgres pod left all gateway pods at `RESTARTS 0`, and the data survived on the PersistentVolume.
- **Rolling updates:** new pods come up one at a time and only replace old ones after passing readiness, so the database migration that runs at container start never runs twice at the same moment.
- **Autoscaling:** HPA on CPU (request 100m, target 50%), min 2 / max 4 pods (max kept low because it runs on a laptop).
- **Connection pool math:** (pool 10 + overflow 5) × 4 pods = 60 connections, below PostgreSQL's `max_connections` of 100.

### Load test results

k6, 5.5 minutes, ramping to **150 requests/second held for 3 minutes**, hitting `/api/v1/health` (DB check + Redis check + one analytics insert per request). Everything — cluster, k6 and other apps — ran on the same laptop, so these are laptop numbers, not production numbers.

| | Run 1 — DB pool 5 + 2 | Run 2 — DB pool 10 + 5 |
|---|---|---|
| Requests completed | 30,474 of 37,349 (6,875 dropped) | **37,349 of 37,349** |
| Failed requests | 56 non-200 (+ DB failures the test did not catch) | **0** |
| `"database": "healthy"` check | not checked | **100%** |
| p95 latency | 17.9 ms | **11.9 ms** |
| Max latency | 30.5 s | **0.22 s** |
| DB pool timeout errors in logs | hundreds | **0** |
| Autoscaling | 2 → 4 pods | 2 → 4 pods (and back to 2 after the test) |

**What happened:** Run 1 passed the k6 thresholds, but the logs showed
`QueuePool limit of size 5 overflow 2 reached, connection timed out, timeout 30.00`.
Every request uses the database twice (health check + analytics insert), so each pod's 7 connections ran out at 150 req/s and requests waited 30 seconds for a connection. The health endpoint also returns HTTP 200 when its DB check fails, so the k6 test was extended to assert `"database": "healthy"`. Raising the pool size through the ConfigMap (no code change) fixed it.

### Known limitations / next steps

- Single-node local cluster; k6 ran on the same machine as the cluster.
- Migrations run at container start; a Kubernetes Job (or init container) would be cleaner.
- Analytics are written to the DB on every request; batching them would cut DB load further.
- Rate limiting was switched off only during the load test (all k6 traffic comes from one IP).

### Screenshots

| | |
|---|---|
| Health check through the Ingress | ![Health](docs/k8s/health-ingress.png) |
| Cluster overview: pods, services, Ingress, HPA, PVC | ![HPA](docs/k8s/hpa-scaling.png) |
| HPA scaling events (2 → 3 → 4 → 2) | ![HPA events](docs/k8s/hpa-events.png) |
| k6 result after the fix | ![k6](docs/k8s/k6-summary.png) |

## Deployment

- Backend on Render: `render.yaml` describes the service; set the
  `sync: false` variables in the Render dashboard. `scripts/migrate_db.py` runs as
  the pre-deploy command. The ChromaDB directory is on local disk, so a
  persistent disk (or a managed vector store) is needed for the knowledge
  base to survive deploys.
- Dashboard on Vercel: import `site/`, set `NEXT_PUBLIC_API_URL` to the
  backend URL, and add the Vercel origin to `CORS_ORIGINS`.

## Known limitations

- Circuit breaker, Prometheus counters, and guardrail rules are
  process-local; multiple workers do not share them.
- Prompt-injection and PII detection are heuristics (see Guardrails).
- The grounding score is lexical and can under-score short numeric answers.
- ChromaDB persists to local disk; there is no multi-node vector store.
- Analytics are scoped per user; there is no cross-tenant isolation beyond
  roles.
- `answer_logs` stores the question and answer text (the dashboard shows
  them); LLM prompts elsewhere are still never stored.
- Cost figures (LLM, embedding, savings) are estimates from the pricing
  tables in `app/config.py`, checked on `PRICING_EFFECTIVE_DATE`; they are not
  provider billing. "Expired" cache entries are estimated as entries written
  minus entries present. The semantic lookup scans up to 500 entries linearly;
  a vector index would be needed well beyond that.
- Stampede protection and the answer cache are per Redis instance; the
  generation lock is best effort (a crashed generator blocks identical
  questions for at most `ANSWERS_LOCK_TTL` seconds). Keyed web search and
  page fetching reach the open web: results are ranked by trusted domain but
  not fact-checked.
- Background tasks run in-process; a crash can lose the last usage row.

## Future improvements

- Presidio-based PII detection, multi-language injection rules.
- Refresh-token rotation on every refresh.
- Alembic autogenerate checks in CI.
- OpenTelemetry tracing and shared breaker state across workers.
- Managed vector store option for multi-instance deployments.
