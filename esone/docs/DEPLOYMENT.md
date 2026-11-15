# Deploying Esone: Render + Supabase

Esone runs as three pieces:

| Piece | Where | Folder | How |
| --- | --- | --- | --- |
| Database | Supabase | | Postgres, session pooler |
| API (`esone-api`) | Render | `backend/` | Python web service from `render.yaml`, health `/api/v1/health` |
| Frontend | Vercel | `frontend/` | Static site built by `build.py`, config in `frontend/vercel.json` |

Order matters only slightly: create the API first so you know its URL, then
the frontend, then paste the frontend URL back into the API's CORS variable.

No Node.js is needed on either host: the frontend's compiled JavaScript is
committed, and both the Render build and the Vercel build only run Python.

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
   `render.yaml` and offers `esone-api`.
3. Render prompts for every variable marked `sync: false`. Fill them in:

   `esone-api`

   | Variable | Value |
   | --- | --- |
   | `DATABASE_URL` | the Supabase session-pooler URI from step 1 |
   | `ESONE_CORS_ORIGINS` | your Vercel production URL, e.g. `https://esone.vercel.app` (comma-separated if several; no trailing slash). Fill in after step 3 if you do not know it yet |
   | `ESONE_CORS_ORIGIN_REGEX` | `^https://esone[a-z0-9-]*\.vercel\.app$` so Vercel preview deployments can call the API (adjust `esone` to your Vercel project name) |
   | `ESONE_ADMIN_USERNAME` | first admin's username, e.g. `admin` |
   | `ESONE_ADMIN_EMAIL` | first admin's email |
   | `ESONE_ADMIN_PASSWORD` | first admin's password, 8 to 100 characters |

   `ESONE_ENV=production`, `PYTHON_VERSION=3.11.9` and a generated
   `ESONE_SECRET_KEY` come from the blueprint. Do not reuse the secret across
   environments; rotating it signs everyone out.

   The Render service name becomes the hostname. If Render had to pick another
   name (for example `esone-api-x1y2`), use that hostname as the API URL in
   step 3.
4. Click **Apply**. The build takes a few minutes. Note the service URL.

Manual alternative (no blueprint): create a Web Service by hand with root
directory `backend`, build `pip install -r requirements.txt`, start
`uvicorn esone_api.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"`,
health check `/api/v1/health`, and the same variables.

## 3. Vercel (frontend)

1. https://vercel.com > **Add New > Project** > import the GitHub repo.
2. Set **Root Directory** to `frontend`. Leave **Framework Preset** as
   *Other*; `frontend/vercel.json` supplies the install command
   (`python3 -m pip install -r requirements.txt`), the build command
   (`python3 build.py --out dist`), the output directory, clean URLs and the
   security headers.
3. Under **Environment Variables** add, for Production and Preview:

   | Variable | Value |
   | --- | --- |
   | `ESONE_WEB_API_URL` | the Render API URL, e.g. `https://esone-api.onrender.com` (no trailing slash) |

   The value is baked into the HTML at build time, so changing it later means
   **Redeploy** from the Vercel dashboard.
4. Click **Deploy**. Vercel prints the production URL (for example
   `https://esone.vercel.app`).
5. Back on Render, set `ESONE_CORS_ORIGINS` on `esone-api` to that URL and
   save; the service restarts. Without this step the browser blocks every
   API call with a CORS error.

## 4. Verify

1. `https://esone-api.onrender.com/api/v1/health` returns
   `{"status":"healthy","database":"healthy","version":"1.0.0"}`.
2. Supabase Table Editor shows `users` and `refresh_tokens`, with the admin row.
3. Open the Vercel URL, sign in as the admin, open **Users**. Register a
   second account in a private window; it appears in the list with role
   `viewer`. If sign-in fails with a network or CORS error, re-check
   `ESONE_CORS_ORIGINS` and `ESONE_WEB_API_URL`.
4. Once the admin exists you can delete the three `ESONE_ADMIN_*` variables
   from the Render dashboard.

The free Render instance sleeps after inactivity; the first API request after
a sleep can take 30 to 60 seconds. The frontend shows a "waking the server"
note while it waits. The static frontend on Vercel never sleeps. The
in-memory login rate limiter is per instance, which is fine on one free
instance.
