"""
Guardrails audit routes.

GET  /guardrails/summary  -> counts by category, feature, blocked, severity
GET  /guardrails/events   -> recent events (admins see all users)
POST /guardrails/check    -> dry-run the input screen on a text
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.guardrails.injection import scan_text
from app.ai.guardrails.pii import mask_text
from app.config import settings
from app.core.security import get_current_user
from app.core.view_as import AsUserParam, resolve_view_as
from app.database.db import get_session
from app.ai.guardrails.events import GuardrailEventService
from app.schemas.ingest import SERVICE_NAME_PATTERN
from app.services.analytics import AnalyticsService
from app.schemas.guardrails import (
    GuardrailCheckRequest,
    GuardrailCheckResponse,
    GuardrailEventItem,
    GuardrailEventPage,
    GuardrailSummary,
)

router = APIRouter(prefix="/guardrails", tags=["AI Security"])


ServiceParam = Query(default=None, pattern=SERVICE_NAME_PATTERN, description="Monitored service name")


async def _scope(
    current_user: dict, service: Optional[str], session: AsyncSession, as_user: Optional[str] = None
) -> tuple[str, int | None]:
    """Admins see everything, others their own events; ``service`` selects a
    monitored service's gateway account (e.g. Esone's) for any role; an admin's
    ``as_user`` selects one user."""
    view = resolve_view_as(current_user, as_user)
    if view is not None:
        return "user", view.user_id
    if service:
        account = await AnalyticsService(session).service_account_id(service)
        return "service", account if account is not None else -1
    if current_user.get("role") == "admin":
        return "all", None
    return "own", int(current_user.get("sub"))


@router.get("/summary", response_model=GuardrailSummary)
async def get_guardrail_summary(
    hours: int = Query(default=24, gt=0, le=720),
    service: Optional[str] = ServiceParam,
    as_user: Optional[str] = AsUserParam,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    scope, user_id = await _scope(current_user, service, session, as_user)
    data = await GuardrailEventService(session).summary(hours=hours, user_id=user_id)
    return GuardrailSummary(
        scope=scope,
        injection_blocking_enabled=settings.guardrails_block_injection,
        pii_masking_enabled=settings.guardrails_mask_pii,
        **data,
    )


@router.get("/events", response_model=GuardrailEventPage)
async def get_guardrail_events(
    hours: int = Query(default=24, gt=0, le=720),
    limit: int = Query(default=50, gt=0, le=500),
    service: Optional[str] = ServiceParam,
    as_user: Optional[str] = AsUserParam,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    scope, user_id = await _scope(current_user, service, session, as_user)
    rows = await GuardrailEventService(session).recent(hours=hours, user_id=user_id, limit=limit)
    return GuardrailEventPage(
        hours=hours,
        scope=scope,
        items=[GuardrailEventItem.model_validate(row, from_attributes=True) for row in rows],
    )


@router.post("/check", response_model=GuardrailCheckResponse)
async def check_text(
    payload: GuardrailCheckRequest,
    current_user: dict = Depends(get_current_user),
):
    """Show what the guardrails would do with a text. Nothing is stored or sent."""
    scan = scan_text(payload.text)
    masked = mask_text(payload.text)
    return GuardrailCheckResponse(
        injection_severity=scan.severity,
        injection_rules=scan.matched,
        would_block=scan.severity == "high" and settings.guardrails_block_injection,
        pii_counts=masked.counts,
        masked_text=masked.text,
    )
