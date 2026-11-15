"""Esone web: a small FastAPI app that serves the HTML pages and static assets.

Pages are Jinja2 templates; behaviour lives in TypeScript compiled to plain
browser modules under static/js. The only configuration the pages need is the
address of the Esone API, injected as <meta name="esone-api-url">.

Run locally:   uvicorn esone_web.main:app --reload --port 4000
On Render:     uvicorn esone_web.main:app --host 0.0.0.0 --port $PORT
"""
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from esone_web import __version__

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"


def normalise_api_url(value: str) -> str:
    """Trim, drop trailing slashes and add https:// when the scheme was left out."""
    value = value.strip().rstrip("/")
    if not value:
        return "http://localhost:8000"
    if not value.lower().startswith(("http://", "https://")):
        value = "https://" + value
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ESONE_WEB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "development"
    # Public origin of the Esone API, e.g. https://esone-api.onrender.com
    api_url: str = "http://localhost:8000"

    @field_validator("api_url")
    @classmethod
    def _normalise(cls, value: str) -> str:
        return normalise_api_url(value)

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Static security headers. The CSP only lets scripts come from this origin
    and only lets fetch() talk to this origin and the API."""

    def __init__(self, app: ASGIApp, api_url: str) -> None:
        super().__init__(app)
        self.csp = "; ".join(
            [
                "default-src 'self'",
                "script-src 'self'",
                "style-src 'self' https://fonts.googleapis.com",
                "font-src https://fonts.gstatic.com",
                "img-src 'self' data:",
                f"connect-src 'self' {api_url}",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'",
            ]
        )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = self.csp
        return response


# page name -> (path, template)
PAGES: dict[str, tuple[str, str]] = {
    "index": ("/", "index.html"),
    "login": ("/login", "login.html"),
    "register": ("/register", "register.html"),
    "account": ("/account", "account.html"),
    "admin": ("/admin", "admin.html"),
}


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Esone Web", version=__version__, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(SecurityHeadersMiddleware, api_url=settings.api_url)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    templates = Jinja2Templates(directory=TEMPLATES_DIR)

    def render(request: Request, page: str) -> HTMLResponse:
        _, template = PAGES[page]
        return templates.TemplateResponse(
            request=request,
            name=template,
            context={
                "page": page,
                "api_url": settings.api_url,
                "asset_version": __version__,
                "year": datetime.now(UTC).year,
            },
        )

    for name, (path, _) in PAGES.items():
        # Bind `name` per iteration; a lambda would close over the loop variable.
        def make_handler(page: str):
            async def handler(request: Request) -> HTMLResponse:
                return render(request, page)

            handler.__name__ = f"page_{page}"
            return handler

        app.add_api_route(path, make_handler(name), methods=["GET", "HEAD"], response_class=HTMLResponse, include_in_schema=False)

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "version": __version__, "api_url": settings.api_url}

    return app


app = create_app()
