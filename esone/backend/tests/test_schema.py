"""init_db adds columns that newer models declare to tables created by an older version."""
import pytest
from sqlalchemy import text


@pytest.fixture
async def old_database(tmp_path, monkeypatch):
    monkeypatch.setenv("ESONE_ENV", "test")
    monkeypatch.setenv("ESONE_SECRET_KEY", "test-secret-key-test-secret-key-test")
    monkeypatch.setenv("ESONE_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'old.db'}")
    from esone_api.config import get_settings
    from esone_api.database import dispose_db, get_engine

    get_settings.cache_clear()
    await dispose_db()
    engine = get_engine()
    async with engine.begin() as conn:
        # The chat_messages table as the first version created it: no status, cost or cache_type columns.
        await conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(100), email VARCHAR(255), "
                                "hashed_password VARCHAR(255), role VARCHAR(20), is_active BOOLEAN, created_at DATETIME)"))
        await conn.execute(text("CREATE TABLE chat_messages (id INTEGER PRIMARY KEY, user_id INTEGER, question TEXT, answer TEXT, "
                                "answered_by VARCHAR(10), cached BOOLEAN, match_method VARCHAR(12), similarity FLOAT, "
                                "compose_method VARCHAR(10), sources TEXT, latency_ms FLOAT, crawl_ms FLOAT, created_at DATETIME)"))
        await conn.execute(text("INSERT INTO chat_messages (user_id, question, answer, answered_by, cached, sources, latency_ms, created_at) "
                                "VALUES (1, 'old question', 'old answer', 'crawler', 0, '[]', 12.5, '2026-01-01 00:00:00')"))
    yield engine
    await dispose_db()
    get_settings.cache_clear()


async def test_init_db_adds_missing_columns_with_defaults(old_database):
    from esone_api.database import init_db

    await init_db()
    async with old_database.connect() as conn:
        columns = {row[1]: row for row in (await conn.execute(text("PRAGMA table_info(chat_messages)"))).all()}
        for name in ("status", "error_message", "cache_type", "sources_count", "cache_lookup_ms", "llm_ms",
                     "total_tokens", "estimated_cost_usd", "served_model", "correlation_id"):
            assert name in columns, f"{name} was not added"
        row = (await conn.execute(text("SELECT status, sources_count, total_tokens, estimated_cost_usd, served_model FROM chat_messages"))).one()
        assert tuple(row) == ("ok", 0, 0, 0.0, None)  # old rows get the defaults
    await init_db()  # idempotent
