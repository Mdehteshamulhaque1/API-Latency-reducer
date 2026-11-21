"""The page server renders every page, injects the API URL and serves the compiled assets."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FRONTEND_DIR = Path(__file__).resolve().parents[1]
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

from esone_web.main import PAGES, STATIC_DIR, create_app, get_settings, normalise_api_url  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ESONE_WEB_API_URL", "https://esone-api.example.com/")
    get_settings.cache_clear()
    with TestClient(create_app()) as c:
        yield c
    get_settings.cache_clear()


@pytest.mark.parametrize("page", list(PAGES))
def test_every_page_renders_with_api_url_and_security_headers(client, page):
    path, _ = PAGES[page]
    res = client.get(path)
    assert res.status_code == 200, res.text
    assert res.headers["content-type"].startswith("text/html")
    assert '<meta name="esone-api-url" content="https://esone-api.example.com">' in res.text
    assert f'data-page="{page}"' in res.text
    assert "static/js/site.js" in res.text
    assert res.headers["X-Frame-Options"] == "DENY"
    assert "connect-src 'self' https://esone-api.example.com" in res.headers["Content-Security-Policy"]
    assert client.head(path).status_code == 200  # uptime monitors often use HEAD


def test_page_scripts_exist_for_each_interactive_page(client):
    """Every <script src> a page references must resolve, or the page is dead on arrival."""
    for page, (path, _) in PAGES.items():
        html = client.get(path).text
        for src in _script_sources(html):
            assert client.get(src).status_code == 200, f"{page} references missing script {src}"


def test_compiled_js_is_committed():
    """TypeScript output is committed so the Render Python service needs no Node at build time."""
    for name in ("site", "api", "dom", "home", "searchbar", "login", "register", "chat", "account", "admin"):
        assert (STATIC_DIR / "js" / f"{name}.js").is_file(), f"run `npm run build` to produce {name}.js"


def test_healthz_reports_api_url(client):
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["api_url"] == "https://esone-api.example.com"


def test_api_url_normalisation():
    assert normalise_api_url(" https://x.onrender.com/ ") == "https://x.onrender.com"
    assert normalise_api_url("x.onrender.com") == "https://x.onrender.com"
    assert normalise_api_url("http://localhost:8000") == "http://localhost:8000"
    assert normalise_api_url("") == "http://localhost:8000"


def _script_sources(html: str) -> list[str]:
    sources = []
    marker = 'src="'
    start = 0
    while True:
        i = html.find(marker, start)
        if i == -1:
            return sources
        j = html.find('"', i + len(marker))
        src = html[i + len(marker) : j]
        if src.startswith("/static/js/"):
            sources.append(src.split("?")[0])
        start = j
