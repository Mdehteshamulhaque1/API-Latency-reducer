"""
Database connection and session management.
"""

import logging
from typing import AsyncGenerator

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)

from app.config import settings

logger = logging.getLogger(__name__)

# Create async engine
if settings.database_url.startswith("sqlite"):
    engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        connect_args={"timeout": 30},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record):
        """Enable WAL so concurrent reads/writes don't stall the event loop.

        WAL lets readers proceed while a writer holds the lock, and the
        busy_timeout prevents SQLITE_BUSY errors from short lock waits.
        """
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

else:
    engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_recycle=settings.database_pool_recycle,
        pool_pre_ping=True,
    )

# Session factory
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Backward compatibility for older imports
AsyncSessionLocal = async_session_maker


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    """
    async with async_session_maker() as session:
        try:
            yield session
        except HTTPException as e:
            logger.debug(f"Request rejected (HTTP {e.status_code}): {e.detail}")
            await session.rollback()
            raise
        except RequestValidationError:
            logger.debug("Request validation failed")
            await session.rollback()
            raise
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Initialize database tables.
    """
    from app.database.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables initialized")


async def close_db():
    """
    Close database connections.
    """
    await engine.dispose()
    logger.info("Database connection closed")