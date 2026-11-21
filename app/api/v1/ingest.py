"""
Request-log ingestion for monitored services.

``POST /api/v1/ingest/requests`` accepts a batch of request records from
another application (Esone ships one per request it served and per call it
made) and stores them in ``api_logs`` so the dashboard can analyse that
service's traffic. Requires the operator or admin role: the monitored
service signs in with its own service account.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_role
from app.database.db import get_session
from app.schemas.ingest import IngestBatch, IngestResult
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/ingest", tags=["Ingest"])
logger = logging.getLogger(__name__)


@router.post("/requests", response_model=IngestResult, status_code=202)
async def ingest_requests(
    batch: IngestBatch,
    current_user: dict = Depends(verify_role(["admin", "operator"])),
    session: AsyncSession = Depends(get_session),
) -> IngestResult:
    """Store a batch of request records observed by a monitored service."""
    try:
        accepted = await AnalyticsService(session).log_requests_batch(
            batch.records, user_id=int(current_user.get("sub"))
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to store ingested request logs: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to store request logs")
    return IngestResult(accepted=accepted)
