"""
Shared fixtures for the API integration test suite.

Test isolation strategy:
  * A dedicated SQLite file (``test_api_optimizer.db``) — never the dev DB.
  * A dedicated Redis database (``redis://localhost:6379/15``) — never the
    dev DB (0). It is flushed before and after every test.
  * All async work (DB, Redis, HTTP client) runs in one session-scoped event
    loop (configured in ``pytest.ini``), so no cross-event-loop errors.

Environment variables are set here, BEFORE any ``app.*`` module is imported,
so ``app.config.Settings`` reads the test values (env vars override .env).
"""
import os
import sys

# Ensure the repo root is importable (works on Windows and POSIX).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# MUST be set before importing app.config / app.main.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_api_optimizer.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["SECRET_KEY"] = "test-secret-key-0123456789abcdef0123456789abcdef"
os.environ["ADMIN_EMAIL"] = "admin@example.com"
os.environ["ADMIN_PASSWORD"] = "admin-pass-123"
os.environ["RATE_LIMIT_DEFAULT_REQUESTS"] = "5"
os.environ["RATE_LIMIT_DEFAULT_PERIOD"] = "3600"

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.constants import UserRole  # noqa: E402
from app.core.security import JWTHandler, PasswordHandler  # noqa: E402
from app.database.db import async_session_maker, close_db, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.utils.redis_client import redis_client  # noqa: E402

TEST_DB_FILE = "test_api_optimizer.db"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def app_env():
    """Create tables, seed base users, and wire up Redis for the whole run."""
    # Clean up any stale test DB from a previous run.
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)

    await init_db()
    await redis_client.connect()
    await _flush_redis()

    async with async_session_maker() as session:
        users = [
            User(
                username="admin",
                email=os.environ["ADMIN_EMAIL"],
                hashed_password=PasswordHandler.hash_password(os.environ["ADMIN_PASSWORD"]),
                role=UserRole.ADMIN,
                is_active=True,
                is_superuser=True,
                api_quota=100000,
            ),
            User(
                username="operator",
                email="operator@example.com",
                hashed_password=PasswordHandler.hash_password("operator-pass-123"),
                role=UserRole.OPERATOR,
                is_active=True,
            ),
            User(
                username="viewer",
                email="viewer@example.com",
                hashed_password=PasswordHandler.hash_password("viewer-pass-123"),
                role=UserRole.VIEWER,
                is_active=True,
            ),
        ]
        session.add_all(users)
        await session.commit()

    yield

    await redis_client.disconnect()
    await close_db()
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)


@pytest_asyncio.fixture(autouse=True)
async def _clean_state():
    """Give every test a fresh cache, rate-limit state, and rule set."""
    await _flush_redis()
    from sqlalchemy import text

    async with async_session_maker() as session:
        await session.execute(text("DELETE FROM cache_rules"))
        await session.commit()
    yield
    await _flush_redis()


async def _flush_redis():
    """Flush only the test Redis database (never the shared dev DB 0)."""
    try:
        if redis_client.client is not None:
            await redis_client.client.flushdb()
    except Exception:
        pass


@pytest_asyncio.fixture(scope="session")
async def client():
    """Async HTTP client that calls the app in-process (no network server)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


def make_token(user_id: int, role: str) -> str:
    """Mint a JWT access token with the given role claim (no DB lookup)."""
    return JWTHandler.create_access_token({"sub": str(user_id), "role": role})


@pytest_asyncio.fixture
async def admin_headers():
    return {"Authorization": f"Bearer {make_token(1, 'admin')}"}


@pytest_asyncio.fixture
async def operator_headers():
    return {"Authorization": f"Bearer {make_token(2, 'operator')}"}


@pytest_asyncio.fixture
async def viewer_headers():
    return {"Authorization": f"Bearer {make_token(3, 'viewer')}"}
