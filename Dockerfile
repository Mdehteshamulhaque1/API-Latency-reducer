# API Optimizer backend image (FastAPI + Alembic). The dashboard (site/) and
# Esone (esone/) are deployed separately and excluded by .dockerignore.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Build tools for wheels without binaries (asyncpg, aiomysql on some platforms).
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run as an unprivileged user; ChromaDB writes to ./data.
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/data \
    && chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
  CMD python -c "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\",\"8000\")}/api/v1/health').status==200 else 1)"

# Apply migrations + seed the admin, then serve. Honors $PORT (Render), falls
# back to 8000. --proxy-headers keeps client IPs correct behind a load balancer;
# set TRUSTED_PROXIES so the rate limiter trusts X-Forwarded-For.
CMD ["sh", "-c", "python scripts/migrate_db.py && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
