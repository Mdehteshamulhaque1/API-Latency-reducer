# Deploying Esone: Render + Supabase

Esone runs as two Render web services with a Supabase Postgres database.
Both are declared in the repo-root `render.yaml`, so the whole stack can be
created from the Render Blueprint screen in one go.

| Service | Folder | Runtime | Health check |
| --- | --- | --- | --- |
| `esone-api` | `backend/` | Python 3.11, uvicorn | `/api/v1/health` |
| `esone-web` | `frontend/` | Python 3.11, uvicorn | `/healthz` |

Both services are defined in `render.yaml`: `esone-api` (`rootDir: backend`)
and `esone-web` (`rootDir: frontend`). Both are Python; no Node is needed on
Render because the frontend's compiled JavaScript is committed.

## 1. Supabase

1. Create a project at https://supabase.com and save the database password.
2. Click **Connect** at the top of the dashboard (or *Project Settings >
   Database*). Under *Connection string* pick **Session pooler** and copy the
   URI. It looks like
   `postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`.
   - Use a pooler host (`*.pooler.supabase.com`). Render's outbound traffic is
     IPv4 only and the direct `db.<ref>.supabase.co` host is IPv6 only.
   - Session mode (port 5432) is the best fit for a long-running server.
     Transaction mode (port 6543) also works: the API disables asyncpg's
     prepared-statement cache and uses unique statement names.
   - If the password contains special characters, URL-encode them
     (`@` becomes `%40`, `#` becomes `%23`). `?sslmode=require` may stay; it is
     stripped and TLS is enforced in code for every non-local host.
3. Nothing else to create. Tables (`users`, `refresh_tokens`) are created on
   the first start.

## 2. Render

1. Push the repo to GitHub.
2. Render dashboard > **New > Blueprint** > select the repo. Render reads
   `render.yaml` and offers `api-optimizer`, `esone-api` and `esone-web`.
   Deselect `api-optimizer` if you only want Esone.
3. Render prompts for every variable marked `sync: false`. Fill them in:

   `esone-api`

   | Variable | Value |
   | --- | --- |
   | `DATABASE_URL` | the Supabase session-pooler URI from step 1 |
   | `ESONE_CORS_ORIGINS` | `https://esone-web.onrender.com` (comma-separated if several; no trailing slash) |
   | `ESONE_CORS_ORIGIN_REGEX` | leave blank (only needed to allow extra origins by pattern) |
   | `ESONE_ADMIN_USERNAME` | first admin's username, e.g. `admin` |
   | `ESONE_ADMIN_EMAIL` | first admin's email |
   | `ESONE_ADMIN_PASSWORD` | first admin's password, 8 to 100 characters |

   `ESONE_ENV=production`, `PYTHON_VERSION=3.11.9` and a generated
   `ESONE_SECRET_KEY` come from the blueprint. Do not reuse the secret across
   environments; rotating it signs everyone out.

   `esone-web`

   | Variable | Value |
   | --- | --- |
   | `ESONE_WEB_API_URL` | `https://esone-api.onrender.com` (no trailing slash) |

   `ESONE_WEB_ENV=production` and `PYTHON_VERSION` come from the blueprint.
   The Render service name becomes the hostname. If Render had to pick another
   name (for example `esone-api-x1y2`), use that hostname in both
   `ESONE_WEB_API_URL` and `ESONE_CORS_ORIGINS`. The page server reads
   `ESONE_WEB_API_URL` at request time, so a restart is enough.
4. Click **Apply**. Builds take a few minutes.

Manual alternative (no blueprint): create two Web Services by hand with
root directory `backend` (build `pip install -r requirements.txt`, start
`uvicorn esone_api.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"`,
health check `/api/v1/health`) and root directory `frontend` (build
`pip install -r requirements.txt`, start
`uvicorn esone_web.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"`,
health check `/healthz`), with the same variables.

## 3. Verify

1. `https://esone-api.onrender.com/api/v1/health` returns
   `{"status":"healthy","database":"healthy","version":"1.0.0"}`.
2. Supabase Table Editor shows `users` and `refresh_tokens`, with the admin row.
3. Open `https://esone-web.onrender.com`, sign in as the admin, open
   **Users**. Register a second account in a private window; it appears in
   the list with role `viewer`.
4. Once the admin exists you can delete the three `ESONE_ADMIN_*` variables
   from the Render dashboard.

Free Render instances sleep after inactivity; the first request after a sleep
can take 30 to 60 seconds. The frontend shows a "waking the server" note while
it waits. Both free services sleep independently. The in-memory login rate
limiter is per instance, which is fine on one free instance.
