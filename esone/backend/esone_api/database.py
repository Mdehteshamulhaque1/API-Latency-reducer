"""Async SQLAlchemy engine, session factory and declarative base."""
import uuid
from collections.abc import AsyncIterator
from urllib.parse import urlsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from esone_api.config import get_settings


class Base(DeclarativeBase):
    pass


LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", None}

# Any constant works; it only has to be the same in every instance of this API.
SCHEMA_LOCK_ID = 7_312_004


def _unique_statement_name() -> str:
    """Prepared-statement names that cannot collide across pooled connections.

    Supabase's pooler (Supavisor) in transaction mode multiplexes many client
    connections onto few server connections. asyncpg's default names
    (``__asyncpg_stmt_1__`` ...) are per-client counters, so two clients can
    create the same name on one server connection and fail with
    "prepared statement already exists". Random names avoid that.
    """
    return f"__asyncpg_{uuid.uuid4().hex}__"


def make_engine(url: str) -> AsyncEngine:
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool
    elif url.startswith("postgresql+asyncpg"):
        host = urlsplit(url).hostname
        connect_args: dict = {
            # Supabase's pooler in transaction mode does not support server-side
            # prepared statements, which asyncpg caches by default. Disabling the
            # cache plus unique names keeps both pooler modes working.
            "statement_cache_size": 0,
            "prepared_statement_name_func": _unique_statement_name,
        }
        if host not in LOCAL_HOSTS:
            connect_args["ssl"] = "require"
        kwargs["connect_args"] = connect_args
        kwargs["pool_size"] = 5
        kwargs["max_overflow"] = 5
        # Recycle before the pooler's idle timeout closes the server side.
        kwargs["pool_recycle"] = 1800
    return create_async_engine(url, **kwargs)


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine, _session_factory
    if _engine is None:
        _engine = make_engine(get_settings().database_url)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    get_engine()
    assert _session_factory is not None
    return _session_factory


async def init_db() -> None:
    """Create tables. Small project; no migrations yet.

    On Postgres the work runs under a transaction-scoped advisory lock so two
    instances starting at once (Render's zero-downtime deploys overlap the old
    and new instance) cannot race each other on CREATE TABLE.
    """
    from esone_api import models  # noqa: F401  (register models on Base)

    engine = get_engine()
    async with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            await conn.execute(text("SELECT pg_advisory_xact_lock(:id)"), {"id": SCHEMA_LOCK_ID})
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_missing_columns)


def _add_missing_columns(connection) -> None:
    """``create_all`` never alters existing tables; add columns that newer
    models declare so a database created by an older version keeps working."""
    from sqlalchemy import inspect

    inspector = inspect(connection)
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue
        existing = {column["name"] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing:
                continue
            spec = column.type.compile(dialect=connection.dialect)
            numeric = spec.upper().startswith(("INT", "FLOAT", "NUM", "REAL", "DOUBLE", "BOOL"))
            default = ""
            if column.server_default is not None:
                arg = column.server_default.arg
                value = arg.text if hasattr(arg, "text") else str(arg)
                default = f" DEFAULT {value}" if numeric else f" DEFAULT '{value}'"
            elif not column.nullable:
                default = " DEFAULT 0" if numeric else " DEFAULT ''"
            connection.execute(text(f'ALTER TABLE {table.name} ADD COLUMN "{column.name}" {spec}{default}'))


async def dispose_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_session_factory()() as session:
        yield session
