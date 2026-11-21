# Project structure

The repository holds two products that deploy independently.

| Product | Folder | Runs on |
| --- | --- | --- |
| API Optimizer backend (FastAPI gateway) | `app/` | Render (`render.yaml`, `Dockerfile`) |
| API Optimizer dashboard (Next.js) | `site/` | Vercel |
| Esone API (FastAPI) | `esone/backend/` | Render (`render.yaml` or `esone/render.yaml`) |
| Esone web (Jinja2 + TypeScript, static) | `esone/frontend/` | Vercel (`esone/frontend/vercel.json`) |

Esone is also published on its own as a separate repository, which is why
`esone/` carries its own `render.yaml`, `.github/workflows/ci.yml`,
`ruff.toml` and README. In this repository the root CI tests it.

```
.
├── app/                      API Optimizer backend package
│   ├── main.py               app factory, middleware order, router registration
│   ├── config.py             settings from the environment (.env), pricing tables
│   ├── api/v1/               HTTP routes only: parse input, call a service
│   │                         auth, analytics, rules, cache, rate_limits, chat,
│   │                         answers, pricing, ai_usage, guardrails, assistant,
│   │                         documents, ingest, proxy, health, demo
│   ├── services/             business logic (analytics, cache, rate limiting,
│   │                         auth, LLM gateway, circuit breaker, answers,
│   │                         answer history, AI usage, pricing)
│   ├── ai/                   AI features
│   │   ├── answers/          shared semantic cache, multi-source crawler,
│   │   │                     answer composer (model-first)
│   │   ├── assistant/        metric tools, engine, recommendations, troubleshoot
│   │   ├── guardrails/       injection, PII masking, output checks, audit events
│   │   ├── rag/              extract, chunk, embeddings, vector store, retrieval
│   │   └── provider.py       chat service factory
│   ├── middleware/           metrics, correlation id, auth, rate limit, cache
│   ├── models/               SQLAlchemy tables
│   ├── schemas/              Pydantic request/response models, one file per router
│   ├── core/                 security (JWT, bcrypt, roles), exceptions, metrics, constants
│   ├── database/             engine, session factory, declarative base
│   └── utils/                Redis client, JSON logging
├── alembic/                  migrations 0001 … 0010 (alembic.ini at the root)
├── tests/                    pytest: integration tests at the top, unit/ for pure logic
├── scripts/                  migrate_db.py, seed_demo.py, dev.sh (runs the whole stack)
├── loadtest/                 k6 cache-off vs cache-on benchmark
├── site/                     dashboard
│   ├── app/                  routes: landing, login, register, status, dashboard/*
│   ├── components/           ui/, charts/, dashboard/, landing/, auth/
│   └── lib/                  api.ts (the only HTTP client), auth and service hooks
├── esone/
│   ├── backend/esone_api/    routers, models, schemas, services, telemetry, optimizer client
│   ├── backend/tests/
│   ├── frontend/src/         TypeScript sources, compiled to esone_web/static/js (committed)
│   ├── frontend/esone_web/   page server, Jinja2 templates, CSS
│   ├── frontend/build.py     renders the static site for Vercel
│   └── docs/DEPLOYMENT.md
├── docs/                     architecture (HTML + PDF), manual test checklist, this file
├── .github/workflows/ci.yml  backend, dashboard and Esone jobs
├── Dockerfile, docker-compose.yml, render.yaml
├── pyproject.toml            ruff and pytest configuration
└── requirements.txt          backend dependencies (pinned)
```

## Conventions

- Routes never contain business logic; they call a service. AI code lives in
  `app/ai/`. New tables get an Alembic migration.
- The dashboard talks to the backend only through `site/lib/api.ts`. Every
  endpoint it calls exists in `app/api/v1/`.
- Esone's compiled JavaScript is committed; run `npm run build` in
  `esone/frontend` after editing `src/` (CI fails if they drift).
- Never commit `.env` files. `.env.example` files document every variable.

## Generated, never committed

`venv/`, `node_modules/`, `site/.next/`, `esone/frontend/dist/`, `data/`
(ChromaDB), `.dev/` (logs and pids from `scripts/dev.sh`), `*.db`, caches.
All are listed in `.gitignore` and can be deleted at any time.
