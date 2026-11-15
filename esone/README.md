# Esone

JWT authentication platform. Two small Python services:

| Folder | What | Stack |
| --- | --- | --- |
| `backend/` | Esone API: register, login, refresh, logout, profile, password change, admin user management | FastAPI, SQLAlchemy 2 async, SQLite locally, Supabase Postgres in production |
| `frontend/` | Esone Web: the landing page, sign-in and sign-up forms, session console and admin users table | FastAPI page server, Jinja2 templates, plain CSS, TypeScript compiled to browser JavaScript |

No React, no Next.js, no bundler. The TypeScript in `frontend/src` is compiled
by `tsc` to plain ES modules which are committed, so deploying needs only
Python.

## Repository layout

```
esone/
├── backend/                 Esone API (FastAPI)
│   ├── esone_api/           application package: config, models, security, services, routers/
│   ├── tests/               pytest suite (SQLite, no external services)
│   ├── requirements.txt
│   └── .env.example         ESONE_* variables
├── frontend/                Esone Web (FastAPI page server)
│   ├── esone_web/
│   │   ├── main.py          routes, settings, security headers
│   │   ├── templates/       Jinja2 pages and partials
│   │   └── static/          css/app.css and js/ (compiled from src/, committed)
│   ├── src/                 TypeScript sources (tsc -> esone_web/static/js)
│   ├── tests/               pytest suite for the page server
│   ├── requirements.txt
│   ├── package.json         only devDependency: typescript
│   └── .env.example         ESONE_WEB_* variables
├── docs/
│   └── DEPLOYMENT.md        Render + Supabase walkthrough and variables
├── .github/workflows/ci.yml tests, lint and type-check on every push
├── render.yaml              Render Blueprint (esone-api, esone-web)
├── ruff.toml                shared Python lint settings
└── .editorconfig
```

Each half has its own README with details: [backend/README.md](backend/README.md)
and [frontend/README.md](frontend/README.md).

## Local development

```bash
# terminal 1: API on http://localhost:8000
cd backend
pip install -r requirements.txt
copy .env.example .env        # set ESONE_SECRET_KEY, optionally ESONE_ADMIN_*
uvicorn esone_api.main:app --reload --port 8000

# terminal 2: pages on http://localhost:4000
cd frontend
pip install -r requirements.txt
copy .env.example .env        # ESONE_WEB_API_URL=http://localhost:8000
uvicorn esone_web.main:app --reload --port 4000
```

Open http://localhost:4000. If port 8000 is busy, run the API on another port
and change `ESONE_WEB_API_URL` to match. To edit the browser code, see
`frontend/README.md` (`npm install`, `npm run build`).

## Checks

```bash
cd backend  && pytest -q && ruff check .
cd frontend && pytest -q && ruff check . && npm run check
```

The same checks run in GitHub Actions on every push (`.github/workflows/ci.yml`).

## Deploy

Both services run on Render; the database is Supabase Postgres. Everything is
declared in `render.yaml`. The step-by-step guide with every environment
variable is [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Short version:

1. Create a Supabase project and copy the **session pooler** connection string.
2. Render > New > Blueprint > pick this repo. Fill in the variables Render asks
   for (`DATABASE_URL`, `ESONE_CORS_ORIGINS`, `ESONE_ADMIN_*`,
   `ESONE_WEB_API_URL`).
3. Open `https://esone-api.onrender.com/api/v1/health`, then
   `https://esone-web.onrender.com`.

Free Render instances sleep after 15 minutes without traffic; the first
request afterwards can take up to a minute. The sign-in form shows a
"waking the server" note while it waits.

Tokens live in the browser's local storage; the frontend holds no secrets and
needs no configuration other than the API URL.
