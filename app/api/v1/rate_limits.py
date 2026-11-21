"""
Rate-limit API routes.

GET /rate-limits/config  -> effective limiter settings
GET /rate-limits/me      -> the caller's own bucket
GET /rate-limits/events  -> recent HTTP 429 rejections (admins see all users)
"""
import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import get_current_user
from app.core.view_as import AsUserParam, resolve_view_as
from app.database.db import get_session
from app.middleware.rate_limit import RateLimitMiddleware
from app.models import APILog, User
from app.schemas.ingest import SERVICE_NAME_PATTERN
from app.schemas.rate_limits import (
    RateLimitConfig,
    RateLimitEvent,
    RateLimitEventSummary,
    RateLimitTierInfo,
    RateLimitUsage,
)
from app.services.analytics import _utcnow
from app.services.rate_limit import RateLimitService, limits_for_role, tiers
from app.utils.redis_client import redis_client

router = APIRouter(prefix="/rate-limits", tags=["Rate Limits"])
logger = logging.getLogger(__name__)


@router.get("/config", response_model=RateLimitConfig)
async def get_rate_limit_config(current_user: dict = Depends(get_current_user)):
    """Describe how the limiter is configured: every tier, and the caller's own."""
    mine = limits_for_role(current_user.get("role"))
    return RateLimitConfig(
        enabled=settings.rate_limit_enabled,
        your_tier=mine.name,
        capacity=mine.requests,
        period_seconds=mine.period,
        refill_per_second=round(mine.refill_per_second, 6),
        tiers=[
            RateLimitTierInfo(
                name=tier.name,
                applies_to=tier.applies_to,
                capacity=tier.requests,
                period_seconds=tier.period,
                refill_per_second=round(tier.refill_per_second, 6),
                policy=tier.policy,
            )
            for tier in tiers()
        ],
        excluded_paths=sorted(RateLimitMiddleware.EXCLUDED_PATHS),
    )


@router.get("/me", response_model=RateLimitUsage)
async def get_my_rate_limit(
    as_user: Optional[str] = AsUserParam,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Return the caller's own token bucket (or, for an admin, the viewed user's) without consuming a token."""
    view = resolve_view_as(current_user, as_user)
    role = current_user.get("role")
    identifier = f"user:{current_user.get('sub')}"
    if view is not None:
        identifier = f"user:{view.user_id}"
        account = await session.get(User, view.user_id) if view.account_id is not None else None
        role = account.role if account is not None else None
    tier = limits_for_role(role)
    usage = await RateLimitService(redis_client).get_usage(identifier, tier.requests, tier.period)
    return RateLimitUsage(tier=tier.name, **usage)


@router.get("/events", response_model=RateLimitEventSummary)
async def get_rate_limit_events(
    hours: int = Query(default=24, gt=0, le=720),
    limit: int = Query(default=50, gt=0, le=500),
    service: Optional[str] = Query(default=None, pattern=SERVICE_NAME_PATTERN, description="Monitored service"),
    as_user: Optional[str] = AsUserParam,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List recent rejected requests. Admins see every user; others see their own.

    With ``service`` the HTTP 429s that a monitored service (e.g. Esone)
    returned to its own callers are listed instead, for any role.
    """
    view = resolve_view_as(current_user, as_user)
    since = _utcnow() - timedelta(hours=hours)
    is_admin = current_user.get("role") == "admin"
    user_id = int(current_user.get("sub"))

    totals_query = select(
        func.count(APILog.id),
        func.sum(case((APILog.status_code == 429, 1), else_=0)),
    ).where(APILog.created_at >= since)
    events_query = (
        select(APILog)
        .where(APILog.created_at >= since, APILog.status_code == 429)
        .order_by(APILog.created_at.desc())
        .limit(limit)
    )
    if view is not None:
        owner = APILog.end_user == view.end_user if view.end_user is not None else APILog.user_id == view.user_id
        totals_query = totals_query.where(owner)
        events_query = events_query.where(owner)
    elif service:
        totals_query = totals_query.where(APILog.service == service)
        events_query = events_query.where(APILog.service == service)
    elif not is_admin:
        totals_query = totals_query.where(APILog.user_id == user_id)
        events_query = events_query.where(APILog.user_id == user_id)

    total, rejected = (await session.execute(totals_query)).one()
    total = int(total or 0)
    rejected = int(rejected or 0)
    rows = (await session.execute(events_query)).scalars().all()

    return RateLimitEventSummary(
        hours=hours,
        total_requests=total,
        rate_limited_requests=rejected,
        rate_limited_percent=round(rejected / total * 100, 2) if total else 0.0,
        scope="user" if view is not None else "service" if service else "all" if is_admin else "own",
        events=[
            RateLimitEvent(
                id=row.id,
                created_at=row.created_at,
                method=row.method,
                endpoint=row.endpoint,
                client_ip=row.client_ip,
                user_id=row.user_id,
                correlation_id=row.correlation_id,
            )
            for row in rows
        ],
    )
