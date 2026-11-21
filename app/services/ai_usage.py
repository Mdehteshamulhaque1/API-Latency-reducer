"""
AI usage recording and reporting.

``record_*`` helpers write one ``AIRequestLog`` row per LLM call. They are
called from a background task after the HTTP response is sent, so the
database write never adds to the latency the caller observes, and a failed
write only produces a log line.

``summary`` aggregates with SQL (counts, sums, averages, GROUP BY model) so
the dashboard never loads individual rows.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.db import async_session_maker
from app.models import AIRequestLog
from app.schemas.ai_usage import (
    AIModelUsage,
    AIRequestLogItem,
    AIRequestLogPage,
    AIUsagePoint,
    AIUsageSummary,
)
from app.schemas.chat import ChatResponse

logger = logging.getLogger(__name__)

OUTCOME_SUCCESS = "success"
OUTCOME_CACHE_HIT = "cache_hit"
OUTCOME_ERROR = "error"


def _utcnow() -> datetime:
    """Naive UTC now, matching the timestamps SQLite hands back."""
    # Aware UTC: asyncpg reads timestamptz columns back as aware datetimes and
    # treats naive parameters as local time, so naive "now" values both shift
    # the window and fail in datetime arithmetic against fetched rows.
    return datetime.now(timezone.utc)


class AIUsageService:
    """Write and read ``ai_request_logs``."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(self, **fields) -> AIRequestLog:
        row = AIRequestLog(**fields)
        self.session.add(row)
        await self.session.commit()
        return row

    async def summary(
        self,
        *,
        hours: int,
        user_id: Optional[int],
        scope: str,
    ) -> AIUsageSummary:
        since = _utcnow() - timedelta(hours=hours)
        filters = [AIRequestLog.created_at >= since]
        if user_id is not None:
            filters.append(AIRequestLog.user_id == user_id)

        totals = (
            await self.session.execute(
                select(
                    func.count(AIRequestLog.id),
                    func.sum(case((AIRequestLog.outcome == OUTCOME_SUCCESS, 1), else_=0)),
                    func.sum(case((AIRequestLog.outcome == OUTCOME_CACHE_HIT, 1), else_=0)),
                    func.sum(case((AIRequestLog.outcome == OUTCOME_ERROR, 1), else_=0)),
                    func.sum(case((AIRequestLog.fallback_used.is_(True), 1), else_=0)),
                    func.sum(AIRequestLog.prompt_tokens),
                    func.sum(AIRequestLog.completion_tokens),
                    func.sum(AIRequestLog.total_tokens),
                    func.avg(AIRequestLog.latency_ms),
                    func.sum(AIRequestLog.estimated_cost_usd),
                ).where(*filters)
            )
        ).one()
        requests = int(totals[0] or 0)
        successes = int(totals[1] or 0)
        cache_hits = int(totals[2] or 0)
        errors = int(totals[3] or 0)
        fallbacks = int(totals[4] or 0)

        by_model_rows = (
            await self.session.execute(
                select(
                    AIRequestLog.served_model,
                    func.count(AIRequestLog.id),
                    func.sum(case((AIRequestLog.outcome == OUTCOME_SUCCESS, 1), else_=0)),
                    func.sum(case((AIRequestLog.outcome == OUTCOME_CACHE_HIT, 1), else_=0)),
                    func.sum(case((AIRequestLog.outcome == OUTCOME_ERROR, 1), else_=0)),
                    func.sum(AIRequestLog.prompt_tokens),
                    func.sum(AIRequestLog.completion_tokens),
                    func.sum(AIRequestLog.total_tokens),
                    func.avg(AIRequestLog.latency_ms),
                    func.sum(AIRequestLog.estimated_cost_usd),
                )
                .where(*filters)
                .group_by(AIRequestLog.served_model)
                .order_by(desc(func.count(AIRequestLog.id)))
            )
        ).all()

        by_model = [
            AIModelUsage(
                served_model=row[0] or "unknown",
                requests=int(row[1] or 0),
                successes=int(row[2] or 0),
                cache_hits=int(row[3] or 0),
                errors=int(row[4] or 0),
                prompt_tokens=int(row[5] or 0),
                completion_tokens=int(row[6] or 0),
                total_tokens=int(row[7] or 0),
                avg_latency_ms=round(float(row[8] or 0.0), 2),
                estimated_cost_usd=round(float(row[9] or 0.0), 6),
            )
            for row in by_model_rows
        ]

        series = await self._series(filters, since, hours)

        return AIUsageSummary(
            hours=hours,
            scope=scope,
            requests=requests,
            successes=successes,
            cache_hits=cache_hits,
            errors=errors,
            fallbacks=fallbacks,
            error_rate=round(errors / requests * 100, 2) if requests else 0.0,
            cache_hit_rate=round(cache_hits / requests * 100, 2) if requests else 0.0,
            prompt_tokens=int(totals[5] or 0),
            completion_tokens=int(totals[6] or 0),
            total_tokens=int(totals[7] or 0),
            avg_latency_ms=round(float(totals[8] or 0.0), 2),
            estimated_cost_usd=round(float(totals[9] or 0.0), 6),
            by_model=by_model,
            series=series,
        )

    async def _series(self, filters: list, since: datetime, hours: int) -> List[AIUsagePoint]:
        """Bucket calls into at most 24 evenly sized time slots."""
        bucket_count = max(1, min(24, hours))
        bucket = timedelta(minutes=max(5, int(hours * 60 / bucket_count)))

        rows = (
            await self.session.execute(
                select(
                    AIRequestLog.created_at,
                    AIRequestLog.outcome,
                    AIRequestLog.total_tokens,
                    AIRequestLog.estimated_cost_usd,
                ).where(*filters)
            )
        ).all()
        if not rows:
            return []

        buckets: Dict[str, Dict[str, float]] = {}
        for created_at, outcome, tokens, cost in rows:
            if created_at.tzinfo is None:  # SQLite returns naive UTC
                created_at = created_at.replace(tzinfo=timezone.utc)
            index = int((created_at - since).total_seconds() // bucket.total_seconds())
            key = (since + bucket * max(index, 0)).isoformat(timespec="seconds")
            entry = buckets.setdefault(key, {"requests": 0, "errors": 0, "tokens": 0, "cost": 0.0})
            entry["requests"] += 1
            entry["errors"] += 1 if outcome == OUTCOME_ERROR else 0
            entry["tokens"] += int(tokens or 0)
            entry["cost"] += float(cost or 0.0)

        return [
            AIUsagePoint(
                timestamp=key,
                requests=int(entry["requests"]),
                errors=int(entry["errors"]),
                total_tokens=int(entry["tokens"]),
                estimated_cost_usd=round(entry["cost"], 6),
            )
            for key, entry in sorted(buckets.items())
        ]

    async def recent(
        self,
        *,
        hours: int,
        user_id: Optional[int],
        scope: str,
        limit: int,
    ) -> AIRequestLogPage:
        since = _utcnow() - timedelta(hours=hours)
        query = select(AIRequestLog).where(AIRequestLog.created_at >= since)
        if user_id is not None:
            query = query.where(AIRequestLog.user_id == user_id)
        query = query.order_by(desc(AIRequestLog.created_at)).limit(limit)
        rows = (await self.session.execute(query)).scalars().all()
        return AIRequestLogPage(
            hours=hours,
            scope=scope,
            items=[AIRequestLogItem.model_validate(row, from_attributes=True) for row in rows],
        )


# ---------------------------------------------------------------------------
# Background-task entry points used by the chat route
# ---------------------------------------------------------------------------

def _safe_reason(details: Optional[dict]) -> Optional[str]:
    """Pick a short, non-sensitive reason code from an error's details."""
    if not details:
        return None
    reason = details.get("reason")
    if isinstance(reason, str) and reason:
        return reason[:60]
    status = details.get("status_code")
    if status is not None:
        return f"http_{status}"
    return None


async def record_chat_result(
    response: ChatResponse,
    *,
    requested_model: Optional[str],
    user_id: Optional[int],
    correlation_id: Optional[str],
    feature: str = "chat",
) -> None:
    """Persist a successful or cached chat completion."""
    try:
        async with async_session_maker() as session:
            await AIUsageService(session).record(
                user_id=user_id,
                correlation_id=correlation_id,
                feature=feature,
                provider=settings.llm_provider,
                requested_model=requested_model,
                served_model=response.served_model or response.model,
                outcome=OUTCOME_CACHE_HIT if response.cached else OUTCOME_SUCCESS,
                fallback_used=response.fallback_used,
                error_code=None,
                prompt_tokens=0 if response.cached else response.usage.prompt_tokens,
                completion_tokens=0 if response.cached else response.usage.completion_tokens,
                total_tokens=0 if response.cached else response.usage.total_tokens,
                latency_ms=response.latency_ms,
                estimated_cost_usd=0.0 if response.cached else response.estimated_cost_usd,
            )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to record AI usage: %s", exc)


async def record_chat_error(
    *,
    requested_model: Optional[str],
    user_id: Optional[int],
    correlation_id: Optional[str],
    latency_ms: float,
    details: Optional[dict],
    feature: str = "chat",
) -> None:
    """Persist a failed chat completion (no tokens, no cost)."""
    try:
        async with async_session_maker() as session:
            await AIUsageService(session).record(
                user_id=user_id,
                correlation_id=correlation_id,
                feature=feature,
                provider=settings.llm_provider,
                requested_model=requested_model,
                served_model=None,
                outcome=OUTCOME_ERROR,
                fallback_used=bool(details and details.get("fallback_model")),
                error_code=_safe_reason(details) or "provider_error",
                latency_ms=latency_ms,
            )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to record AI usage error: %s", exc)
