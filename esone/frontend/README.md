# Esone Web

The Esone frontend: a small FastAPI app that serves HTML pages. No React, no
Next.js, no bundler.

| Layer | What |
| --- | --- |
| Pages | Jinja2 templates in `esone_web/templates/` (`base.html` layout, one file per page) |
| Styling | One plain stylesheet, `esone_web/static/css/app.css` |
| Behaviour | TypeScript in `src/`, compiled by `tsc` to browser ES modules in `esone_web/static/js/` |
| Server | `esone_web/main.py`: routes `/`, `/login`, `/register`, `/account`, `/admin`, `/healthz`, static files, security headers |

The pages talk to the Esone API (`../backend`) with `fetch`. The API origin is
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

## Deploy on Render

The service is `esone-web` in the repo-root `render.yaml` (Python runtime,
`rootDir: frontend`). It needs one variable, `ESONE_WEB_API_URL`, the public URL
of the API. The value is read at request time, so changing it only needs a
restart. Full walkthrough: [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md).
