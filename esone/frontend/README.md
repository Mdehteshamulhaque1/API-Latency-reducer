# Esone Web

The Esone frontend: a small FastAPI app that serves HTML pages. No React, no
Next.js, no bundler.

| Layer | What |
| --- | --- |
| Pages | Jinja2 templates in `esone_web/templates/` (`base.html` layout, one file per page) |
| Styling | One plain stylesheet, `esone_web/static/css/app.css` |
| Behaviour | TypeScript in `src/`, compiled by `tsc` to browser ES modules in `esone_web/static/js/` |
| Server | `esone_web/main.py`: routes `/`, `/login`, `/register`, `/chat`, `/account`, `/admin`, `/healthz`, static files, security headers |

The pages talk to the Esone API (`../backend`) with `fetch`. The `/chat` page
sends questions to the Esone API, which forwards them to the API Optimizer's
answers pipeline (semantic Redis cache, then crawler). The API origin is
read from `ESONE_WEB_API_URL` and injected into every page as
`<meta name="esone-api-url">`; `src/api.ts` reads it from there. Tokens live in
`localStorage`, with one shared refresh on 401 and a single retry.

## Run locally

```bash
cd frontend
pip install -r requirements.txt
copy .env.example .env               # ESONE_WEB_API_URL=http://localhost:8000
uvicorn esone_web.main:app --reload --port 4000
```

The backend must be running on the URL in `.env` (see `../backend/README.md`).
Its `ESONE_CORS_ORIGINS` already allows `http://localhost:4000`.

## Editing the TypeScript

The compiled JavaScript is committed so the Render service needs no Node.js.
After changing anything in `src/`, rebuild and commit the output:

```bash
cd frontend
npm install          # once; installs only typescript
npm run build        # tsc -> esone_web/static/js
npm run watch        # or rebuild on save while developing
```

`npm run check` type-checks without writing files.

## Tests

```bash
cd frontend
pytest -q
```

The tests render every page, check the API URL and security headers, confirm
every referenced script exists, and fail if the compiled JS is missing.

## Deploy on Vercel

The frontend is deployed as a **static site**. `build.py` renders every
template to HTML once and copies `static/` next to it; Vercel serves the
result from its CDN. Nothing runs on a server, so there are no cold starts.

```bash
cd frontend
ESONE_WEB_API_URL=https://esone-api.onrender.com python build.py   # -> dist/
npx serve dist        # optional local preview with clean URLs
```

On Vercel:

1. Import the GitHub repo. Set **Root Directory** to `frontend` and leave
   **Framework Preset** on *Other*. `vercel.json` already supplies the install
   command (a virtual environment, because Vercel's Python is managed by `uv`
   and refuses system-wide `pip install`), the build command
   (`.venv/bin/python build.py --out dist`), output directory, clean URLs and
   security headers.
2. Add the environment variable `ESONE_WEB_API_URL` =
   `https://esone-api.onrender.com` (no trailing slash) for Production and
   Preview. It is baked into the pages at build time, so changing it needs a
   redeploy.
3. Deploy, then put the Vercel URL into `ESONE_CORS_ORIGINS` on the API
   service (and `ESONE_CORS_ORIGIN_REGEX` for preview URLs). Full
   walkthrough: [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md).

The dev server (`uvicorn esone_web.main:app`) and `build.py` share the same
templates, settings and page table, so what you see locally is what Vercel
serves. The page server can also be hosted on Render if you ever prefer a
single provider; see the note in `render.yaml`.
