"""Application factory.

Run locally:   uvicorn esone_api.main:app --reload --port 8000
On Render:     uvicorn esone_api.main:app --host 0.0.0.0 --port $PORT \
                   --proxy-headers --forwarded-allow-ips="*"
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from esone_api import __version__, services
from esone_api.config import get_settings
from esone_api.database import dispose_db, get_session_factory, init_db
from esone_api.optimizer import reset_optimizer
from esone_api.ratelimit import AuthRateLimitMiddleware
from esone_api.routers import admin, auth, chat, health, users
from esone_api.telemetry import RequestTelemetryMiddleware, start_shipper, stop_shipper

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    await init_db()
    if settings.admin_username and settings.admin_email and settings.admin_password:
        async with get_session_factory()() as session:
            await services.ensure_admin(
                session, settings.admin_username, settings.admin_email, settings.admin_password
            )
    await start_shipper()
    if not settings.is_production:
        logger.info("Esone API %s ready (env=%s)", __version__, settings.env)
    yield
    await stop_shipper()
    await reset_optimizer()
    await dispose_db()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
    )
    # Middleware order (outer to inner): CORS, telemetry, rate limit. Telemetry
    # sits outside the limiter so rejected (429) requests are recorded too,
    # and CORS is outermost so a 429 still carries the CORS headers the
    # browser needs to read it. Starlette makes the LAST added middleware the
    # outermost, so they are added innermost first.
    app.add_middleware(AuthRateLimitMiddleware)
    app.add_middleware(RequestTelemetryMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    prefix = "/api/v1"
    app.include_router(auth.router, prefix=prefix)
    app.include_router(users.router, prefix=prefix)
    app.include_router(admin.router, prefix=prefix)
    app.include_router(chat.router, prefix=prefix)
    app.include_router(health.router, prefix=prefix)
    return app


app = create_app()
