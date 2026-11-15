from esone_api.config import normalise_database_url


def test_supabase_and_render_urls_are_mapped_to_asyncpg():
    supabase = "postgresql://postgres.abc:pw@aws-0-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require"
    assert (
        normalise_database_url(supabase)
        == "postgresql+asyncpg://postgres.abc:pw@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
    )
    assert normalise_database_url("postgres://u:p@host:5432/db") == "postgresql+asyncpg://u:p@host:5432/db"
    assert normalise_database_url("sqlite:///./x.db") == "sqlite+aiosqlite:///./x.db"
    assert normalise_database_url("sqlite+aiosqlite:///./x.db") == "sqlite+aiosqlite:///./x.db"


def test_blank_cors_regex_means_no_regex(monkeypatch):
    from esone_api.config import Settings

    monkeypatch.setenv("ESONE_CORS_ORIGIN_REGEX", "   ")
    assert Settings().cors_origin_regex is None

    monkeypatch.setenv("ESONE_CORS_ORIGIN_REGEX", r"^https://esone(-[a-z0-9-]+)?\.vercel\.app$")
    assert Settings().cors_origin_regex == r"^https://esone(-[a-z0-9-]+)?\.vercel\.app$"


def test_supabase_engine_is_pooler_safe(monkeypatch):
    from esone_api import database

    captured: dict = {}

    def fake_create_async_engine(url, **kwargs):
        captured["url"], captured["kwargs"] = url, kwargs
        return object()

    monkeypatch.setattr(database, "create_async_engine", fake_create_async_engine)
    database.make_engine(
        "postgresql+asyncpg://postgres.abc:pw@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
    )
    connect_args = captured["kwargs"]["connect_args"]
    assert connect_args["statement_cache_size"] == 0
    assert connect_args["ssl"] == "require"
    names = {connect_args["prepared_statement_name_func"]() for _ in range(3)}
    assert len(names) == 3 and all(n.startswith("__asyncpg_") for n in names)
    assert captured["kwargs"]["pool_pre_ping"] is True

    # Local Postgres gets no forced TLS; SQLite gets neither.
    database.make_engine("postgresql+asyncpg://u:p@localhost:5432/db")
    assert "ssl" not in captured["kwargs"]["connect_args"]
    database.make_engine("sqlite+aiosqlite:///./x.db")
    assert "statement_cache_size" not in captured["kwargs"]["connect_args"]
