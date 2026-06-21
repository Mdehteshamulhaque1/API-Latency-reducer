"""
Health check and status endpoints.
"""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.db import get_session
from app.schemas.analytics import HealthCheckResponse
from app.utils.redis_client import redis_client

router = APIRouter(tags=["Health"])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(session: AsyncSession = Depends(get_session)):
    """Health check endpoint."""
    redis_status = "healthy"
    db_status = "healthy"

    try:
        await session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        logger.error("Database health check failed: %s", e)

    try:
        if redis_client.client is None:
            raise RuntimeError("Redis client not initialized")
        await redis_client.client.ping()
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"
        logger.error("Redis health check failed: %s", e)

    overall_status = "healthy" if db_status == "healthy" and redis_status == "healthy" else "degraded"

    return HealthCheckResponse(
        status=overall_status,
        version=settings.app_version,
        database=db_status,
        redis=redis_status,
    )


@router.get("/ping")
async def ping():
    """Simple ping endpoint."""
    return {"message": "pong"}
