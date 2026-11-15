"""Health and liveness."""
import logging

from fastapi import APIRouter
from sqlalchemy import text

from esone_api import __version__
from esone_api.deps import SessionDep
from esone_api.schemas import HealthResponse

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse)
async def health(session: SessionDep):
    database = "healthy"
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - report, never raise, from a health probe
        database = "unhealthy"
        logger.error("database health check failed: %s", type(exc).__name__)
    status = "healthy" if database == "healthy" else "degraded"
    return HealthResponse(status=status, database=database, version=__version__)


@router.get("/ping")
async def ping():
    return {"message": "pong"}
