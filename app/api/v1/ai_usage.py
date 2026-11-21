"""
AI usage, token, and cost monitoring routes.

GET /ai-usage/summary   -> totals, per-model breakdown, time series
GET /ai-usage/requests  -> recent individual calls (no prompt text)

Admins see every user's calls; other roles see their own. With ``service``
the calls made by a monitored service's gateway account (e.g. Esone's) are
shown instead, for any role.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.core.view_as import AsUserParam, resolve_view_as
from app.database.db import get_session
from app.schemas.ai_usage import AIRequestLogPage, AIUsageSummary
from app.schemas.ingest import SERVICE_NAME_PATTERN
from app.services.ai_usage import AIUsageService
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/ai-usage", tags=["AI Usage"])

ServiceParam = Query(default=None, pattern=SERVICE_NAME_PATTERN, description="Monitored service name")


async def _scope(
    current_user: dict, service: Optional[str], session: AsyncSession, as_user: Optional[str] = None
) -> tuple[str, int | None]:
    view = resolve_view_as(current_user, as_user)
    if view is not None:
        return "user", view.user_id
    if service:
        account = await AnalyticsService(session).service_account_id(service)
        # No account yet: an id no row can carry, so the result is empty rather than everyone's.
        return "service", account if account is not None else -1
    if current_user.get("role") == "admin":
        return "all", None
    return "own", int(current_user.get("sub"))


@router.get("/summary", response_model=AIUsageSummary)
async def get_ai_usage_summary(
    hours: int = Query(default=24, gt=0, le=720),
    service: Optional[str] = ServiceParam,
    as_user: Optional[str] = AsUserParam,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Aggregate LLM usage over the window. Costs are estimates."""
    scope, user_id = await _scope(current_user, service, session, as_user)
    return await AIUsageService(session).summary(hours=hours, user_id=user_id, scope=scope)


@router.get("/requests", response_model=AIRequestLogPage)
async def get_ai_usage_requests(
    hours: int = Query(default=24, gt=0, le=720),
    limit: int = Query(default=50, gt=0, le=500),
    service: Optional[str] = ServiceParam,
    as_user: Optional[str] = AsUserParam,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List recent LLM calls, newest first."""
    scope, user_id = await _scope(current_user, service, session, as_user)
    return await AIUsageService(session).recent(
        hours=hours, user_id=user_id, scope=scope, limit=limit
    )
