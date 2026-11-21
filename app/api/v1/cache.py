"""
Cache management API routes.

GET  /cache/stats       -> hit/miss counters and live entry counts (any user)
POST /cache/invalidate  -> drop cached responses (admin or operator)
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import get_current_user, verify_role
from app.database.db import get_session
from app.models import CacheRule
from app.schemas.cache import CacheInvalidateRequest, CacheInvalidateResponse, CacheStats
from app.services.cache import CacheService
from app.utils.redis_client import redis_client

router = APIRouter(prefix="/cache", tags=["Cache"])
logger = logging.getLogger(__name__)


@router.get("/stats", response_model=CacheStats)
async def get_cache_stats(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Return cache counters from Redis plus rule coverage from the database."""
    stats = await CacheService(redis_client).get_cache_stats()

    result = await session.execute(
        select(
            func.count(CacheRule.id),
            func.sum(case((CacheRule.enabled.is_(True), 1), else_=0)),
        )
    )
    total_rules, enabled_rules = result.one()

    return CacheStats(
        **stats,
        default_ttl_seconds=settings.redis_cache_ttl,
        enabled_rules=int(enabled_rules or 0),
        total_rules=int(total_rules or 0),
    )


@router.post("/invalidate", response_model=CacheInvalidateResponse)
async def invalidate_cache(
    payload: CacheInvalidateRequest,
    current_user: dict = Depends(verify_role(["admin", "operator"])),
):
    """Drop cached responses so the next request goes to the upstream."""
    if redis_client.client is None:
        raise HTTPException(status_code=503, detail="Cache backend is unavailable")

    service = CacheService(redis_client)
    if payload.endpoint_pattern:
        deleted = await service.invalidate_route(payload.endpoint_pattern)
        scope = f"rule:{payload.endpoint_pattern}"
    else:
        deleted = await service.invalidate_all()
        scope = "all-responses"

    if payload.include_chat:
        deleted += await service.invalidate_chat()
        scope += "+chat"

    logger.info(
        "Cache invalidated",
        extra={"scope": scope, "deleted": deleted, "user_id": current_user.get("sub")},
    )
    return CacheInvalidateResponse(scope=scope, deleted=deleted)
