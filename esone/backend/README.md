# Esone API

FastAPI backend for the Esone frontend (`frontend/`, a FastAPI page server with Jinja2 templates and TypeScript). JWT auth with short-lived
access tokens, server-tracked rotating refresh tokens, roles, admin user
management and per-IP rate limiting on the credential endpoints. Python 3.11,
SQLAlchemy 2 async. SQLite locally, Supabase (Postgres) in production.

## Endpoints (`/api/v1`)

| Method | Path                     | Auth        | Purpose                                       |
| ------ | ------------------------ | ----------- | --------------------------------------------- |
| POST   | `/auth/register`         | none        | Create a viewer account                       |
| POST   | `/auth/login`            | none        | Username + password, returns token pair       |
| POST   | `/auth/refresh`          | none        | Rotate refresh token, returns new pair        |
| POST   | `/auth/logout`           | none        | Revoke a refresh token (idempotent)           |
| GET    | `/users/me`              | bearer      | Current user profile                          |
| POST   | `/users/me/password`     | bearer      | Change password, revokes all refresh tokens   |
| GET    | `/admin/users`           | admin       | List users (`limit`, `offset`)                |
| PATCH  | `/admin/users/{id}`      | admin       | Change `role` and/or `is_active`              |
| GET    | `/chat/status`           | bearer      | Whether an LLM gateway is configured          |
| POST   | `/chat`                  | bearer      | Ask a question; answered by the API Optimizer |
| GET    | `/health`                | none        | Database check and version                    |

`POST /chat` is a proxy: Esone signs in to the API Optimizer with one
service account (`ESONE_OPTIMIZER_URL`, `_USERNAME`, `_PASSWORD`) and forwards
the question to its `POST /api/v1/answers` pipeline, which checks a semantic
cache in Redis and, on a miss, crawls for the answer and stores it. The reply
(answer, cache hit or crawled, similarity, sources, latency) is returned as
is. Users and their sessions stay in Esone; the Optimizer only ever sees the
service account.

The same service account ships Esone's request telemetry: every request
Esone serves and every call it makes (method, path, status, latency, sizes,
correlation id; never bodies) is buffered by `esone_api/telemetry.py` and
POSTed in batches to the Optimizer's `/api/v1/ingest/requests`, where the
Optimizer dashboard analyses it. The account needs the operator or admin role
there. `ESONE_TELEMETRY_ENABLED=false` turns it off; each response carries an
`X-Correlation-ID` header that ties inbound and outbound rows together.

Refresh tokens are stored by `jti`. A refresh token that is presented again
after it has been rotated is treated as stolen and every session for that user
is revoked. Login and register are limited to 5 attempts per IP per minute
(`ESONE_AUTH_RATE_LIMIT_PER_MINUTE`); a 429 carries `Retry-After`,
`RateLimit-Limit` and `RateLimit-Policy`.

## Run locally

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env                           # then set ESONE_SECRET_KEY
uvicorn esone_api.main:app --reload --port 8000
```

Swagger UI is at `http://localhost:8000/docs` outside production. Tables are
created on startup. To get a first admin, set `ESONE_ADMIN_USERNAME`,
`ESONE_ADMIN_EMAIL` and `ESONE_ADMIN_PASSWORD` before the first start.

## Tests

```bash
cd backend
pytest -q
```

## Deploy

See [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) for the Render and Supabase
walkthrough and the full list of environment variables.

## Schema changes

Tables are created with `create_all` on startup. There are no migrations yet;
future changes to `users` or `refresh_tokens` need Alembic or manual SQL in
Supabase.
