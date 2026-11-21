"""
Guardrail audit events.

Every time a guardrail fires, one ``guardrail_events`` row records WHAT
happened (category, severity, which feature, whether the request was
blocked) and a short non-sensitive detail such as matched rule names or
"email=2 phone=1". Prompts, documents, and secrets are never stored.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import async_session_maker
from app.models import GuardrailEvent

logger = logging.getLogger(__name__)

CATEGORY_INJECTION_DETECTED = "injection_detected"
CATEGORY_INJECTION_BLOCKED = "injection_blocked"
CATEGORY_PII_MASKED = "pii_masked"
CATEGORY_OUTPUT_INVALID = "output_invalid"
CATEGORY_LOW_GROUNDING = "low_grounding"
CATEGORY_RETRIEVAL_FAILED = "retrieval_failed"
CATEGORY_AI_REQUEST_FAILED = "ai_request_failed"
CATEGORY_DOCUMENT_FLAGGED = "document_flagged"
CATEGORY_UPLOAD_REJECTED = "upload_rejected"

ALL_CATEGORIES = [
    CATEGORY_INJECTION_DETECTED,
    CATEGORY_INJECTION_BLOCKED,
    CATEGORY_PII_MASKED,
    CATEGORY_OUTPUT_INVALID,
    CATEGORY_LOW_GROUNDING,
    CATEGORY_RETRIEVAL_FAILED,
    CATEGORY_AI_REQUEST_FAILED,
    CATEGORY_DOCUMENT_FLAGGED,
    CATEGORY_UPLOAD_REJECTED,
]


def _utcnow() -> datetime:
    # Aware UTC: asyncpg reads timestamptz columns back as aware datetimes and
    # treats naive parameters as local time, so naive "now" values both shift
    # the window and fail in datetime arithmetic against fetched rows.
    return datetime.now(timezone.utc)


async def record_event(
    *,
    category: str,
    severity: str,
    feature: str,
    detail: str = "",
    blocked: bool = False,
    user_id: Optional[int] = None,
    correlation_id: Optional[str] = None,
) -> None:
    """Persist one event. Safe to call from a background task; never raises."""
    try:
        async with async_session_maker() as session:
            session.add(
                GuardrailEvent(
                    category=category,
                    severity=severity,
                    feature=feature,
                    detail=detail[:255],
                    blocked=blocked,
                    user_id=user_id,
                    correlation_id=correlation_id,
                )
            )
            await session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to record guardrail event %s: %s", category, exc)


async def record_events(events: List[dict]) -> None:
    for event in events:
        await record_event(**event)


class GuardrailEventService:
    """Read side for the security dashboard."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def summary(self, *, hours: int, user_id: Optional[int]) -> dict:
        since = _utcnow() - timedelta(hours=hours)
        filters = [GuardrailEvent.created_at >= since]
        if user_id is not None:
            filters.append(GuardrailEvent.user_id == user_id)

        totals = (
            await self.session.execute(
                select(
                    func.count(GuardrailEvent.id),
                    func.sum(case((GuardrailEvent.blocked.is_(True), 1), else_=0)),
                    func.sum(case((GuardrailEvent.severity == "high", 1), else_=0)),
                ).where(*filters)
            )
        ).one()

        by_category_rows = (
            await self.session.execute(
                select(GuardrailEvent.category, func.count(GuardrailEvent.id))
                .where(*filters)
                .group_by(GuardrailEvent.category)
            )
        ).all()
        by_category = {category: 0 for category in ALL_CATEGORIES}
        for category, count in by_category_rows:
            by_category[category] = int(count or 0)

        by_feature_rows = (
            await self.session.execute(
                select(GuardrailEvent.feature, func.count(GuardrailEvent.id))
                .where(*filters)
                .group_by(GuardrailEvent.feature)
                .order_by(desc(func.count(GuardrailEvent.id)))
            )
        ).all()

        return {
            "hours": hours,
            "total_events": int(totals[0] or 0),
            "blocked_requests": int(totals[1] or 0),
            "high_severity": int(totals[2] or 0),
            "by_category": by_category,
            "by_feature": {feature: int(count or 0) for feature, count in by_feature_rows},
        }

    async def recent(self, *, hours: int, user_id: Optional[int], limit: int) -> List[GuardrailEvent]:
        since = _utcnow() - timedelta(hours=hours)
        query = select(GuardrailEvent).where(GuardrailEvent.created_at >= since)
        if user_id is not None:
            query = query.where(GuardrailEvent.user_id == user_id)
        query = query.order_by(desc(GuardrailEvent.created_at)).limit(limit)
        return (await self.session.execute(query)).scalars().all()
