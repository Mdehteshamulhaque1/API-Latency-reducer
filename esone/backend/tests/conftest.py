"""Shared fixtures: a fresh SQLite database and an HTTP client per test."""
import os
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

ADMIN = {"username": "root", "email": "root@example.com", "password": "root-password-1"}


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ESONE_ENV", "test")
    monkeypatch.setenv("ESONE_SECRET_KEY", "test-secret-key-test-secret-key-test")
    monkeypatch.setenv("ESONE_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("ESONE_ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.setenv("ESONE_ADMIN_USERNAME", ADMIN["username"])
    monkeypatch.setenv("ESONE_ADMIN_EMAIL", ADMIN["email"])
    monkeypatch.setenv("ESONE_ADMIN_PASSWORD", ADMIN["password"])
    monkeypatch.delenv("DATABASE_URL", raising=False)

    from esone_api import services
    from esone_api.config import get_settings
    from esone_api.database import dispose_db, get_session_factory, init_db
    from esone_api.main import app
    from esone_api.ratelimit import limiter

    get_settings.cache_clear()
    limiter.reset()
    await dispose_db()
    await init_db()
    async with get_session_factory()() as session:
        await services.ensure_admin(session, ADMIN["username"], ADMIN["email"], ADMIN["password"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    await dispose_db()
    get_settings.cache_clear()
    os.environ.pop("ESONE_DATABASE_URL", None)


async def register(client: AsyncClient, username="alice", email="alice@example.com", password="alice-pass-123"):
    res = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    return res


async def login(client: AsyncClient, username="alice", password="alice-pass-123") -> dict:
    res = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, res.text
    return res.json()


def bearer(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}
