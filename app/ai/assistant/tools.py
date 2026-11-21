"""
Controlled, read-only tools the assistant may call.

Each tool returns a small JSON-serialisable dict of measured values. The
model only ever sees these dicts, never SQL, never raw rows with user data.
Adding a tool means adding a function here and a keyword trigger in
``engine.py``; nothing else changes.
"""
from datetime import timedelta
from typing import Dict, List, Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.rag.retrieval import RetrievalService, RetrievedChunk
from app.config import settings
from app.models import APILog, CacheRule
from app.services.ai_usage import AIUsageService
from app.services.analytics import AnalyticsService, _utcnow
from app.services.cache import CacheService
from app.utils.redis_client import redis_client


async def get_performance_summary(
    session: AsyncSession, user_id: Optional[int], hours: int, service: Optional[str] = None
) -> Dict:
    summary = await AnalyticsService(session).get_analytics_summary(user_id=user_id, hours=hours, service=service)
    return {
        "window_hours": hours,
        "total_requests": summary.total_requests,
        "requests_per_minute": summary.request_rate_per_minute,
        "total_errors": summary.total_errors,
        "error_rate_percent": round(summary.error_rate, 2),
        "rate_limited_requests": summary.rate_limited_requests,
        "cache_hit_rate_percent": round(summary.cache_hit_rate, 2),
        "avg_latency_ms": round(summary.avg_response_time_ms, 2),
        "p50_latency_ms": summary.overall_p50_response_time_ms,
        "p95_latency_ms": summary.overall_p95_response_time_ms,
        "p99_latency_ms": summary.overall_p99_response_time_ms,
        "slowest_endpoint": summary.slowest_endpoint,
        "slowest_endpoint_max_latency_ms": summary.slowest_response_time_ms,
        "top_endpoints_by_requests": [
            {"endpoint": e["endpoint"], "requests": e["count"], "avg_latency_ms": e["avg_time"],
             "cache_hit_rate_percent": e["cache_hit_rate"], "errors": e["errors"]}
            for e in summary.top_endpoints[:5]
        ],
    }


async def get_slow_endpoints(
    session: AsyncSession, user_id: Optional[int], hours: int, service: Optional[str] = None
) -> Dict:
    ranking = await AnalyticsService(session).get_top_slow_endpoints(
        user_id=user_id, hours=hours, limit=5, service=service
    )
    return {
        "window_hours": hours,
        "ranked_by": "p95 latency",
        "endpoints": [
            {"endpoint": r["endpoint"], "requests": r["count"], "avg_latency_ms": r["avg_time"],
             "p95_latency_ms": r["p95_time"], "p99_latency_ms": r["p99_time"],
             "error_rate_percent": r["error_rate"], "cache_hit_rate_percent": r["cache_hit_rate"]}
            for r in ranking
        ],
    }


async def get_cache_stats(session: AsyncSession) -> Dict:
    stats = await CacheService(redis_client).get_cache_stats()
    rules = (await session.execute(select(CacheRule))).scalars().all()
    return {
        "redis_available": stats["available"],
        "cache_hits": stats["cache_hits"],
        "cache_misses": stats["cache_misses"],
        "cache_hit_rate_percent": stats["cache_hit_rate"],
        "cached_responses_now": stats["response_entries"],
        "cached_llm_responses_now": stats["chat_entries"],
        "default_ttl_seconds": settings.redis_cache_ttl,
        "rules": [
            {"pattern": r.endpoint_pattern, "ttl_seconds": r.ttl, "enabled": r.enabled,
             "keyed_by_user": r.cache_by_user, "keyed_by_query": r.cache_by_query_params}
            for r in rules[:20]
        ],
    }


async def get_rate_limit_events(
    session: AsyncSession, user_id: Optional[int], hours: int, service: Optional[str] = None
) -> Dict:
    since = _utcnow() - timedelta(hours=hours)
    query = (
        select(APILog.endpoint, func.count(APILog.id))
        .where(APILog.created_at >= since, APILog.status_code == 429)
        .group_by(APILog.endpoint)
        .order_by(desc(func.count(APILog.id)))
        .limit(5)
    )
    if service:
        query = query.where(APILog.service == service)
    elif user_id is not None:
        query = query.where(APILog.user_id == user_id)
    rows = (await session.execute(query)).all()
    return {
        "window_hours": hours,
        "limit_per_window": settings.rate_limit_default_requests,
        "window_seconds": settings.rate_limit_default_period,
        "rate_limited_requests": sum(int(c) for _, c in rows),
        "by_endpoint": [{"endpoint": e, "rejections": int(c)} for e, c in rows],
    }


async def get_ai_usage(
    session: AsyncSession, user_id: Optional[int], hours: int, service: Optional[str] = None
) -> Dict:
    if service:
        # A monitored service's LLM calls are the ones its gateway account made.
        account = await AnalyticsService(session).service_account_id(service)
        user_id = account if account is not None else -1
    usage = await AIUsageService(session).summary(hours=hours, user_id=user_id, scope="own" if user_id else "all")
    return {
        "window_hours": hours,
        "llm_requests": usage.requests,
        "cache_hits": usage.cache_hits,
        "errors": usage.errors,
        "total_tokens": usage.total_tokens,
        "avg_latency_ms": usage.avg_latency_ms,
        "estimated_cost_usd": usage.estimated_cost_usd,
        "cost_is_estimate": True,
        "by_model": [{"model": m.served_model, "requests": m.requests, "tokens": m.total_tokens} for m in usage.by_model[:5]],
    }


async def get_recent_errors(
    session: AsyncSession,
    user_id: Optional[int],
    hours: int,
    *,
    status_code: Optional[int] = None,
    endpoint: Optional[str] = None,
    limit: int = 8,
    service: Optional[str] = None,
) -> Dict:
    since = _utcnow() - timedelta(hours=hours)
    filters = [APILog.created_at >= since, APILog.status_code >= 400]
    if service:
        filters.append(APILog.service == service)
    elif user_id is not None:
        filters.append(APILog.user_id == user_id)
    if status_code is not None:
        filters.append(APILog.status_code == status_code)
    if endpoint:
        filters.append(APILog.endpoint.like(f"%{endpoint}%"))

    by_status = (
        await session.execute(
            select(APILog.status_code, func.count(APILog.id))
            .where(*filters)
            .group_by(APILog.status_code)
            .order_by(desc(func.count(APILog.id)))
        )
    ).all()
    by_endpoint = (
        await session.execute(
            select(APILog.endpoint, func.count(APILog.id))
            .where(*filters)
            .group_by(APILog.endpoint)
            .order_by(desc(func.count(APILog.id)))
            .limit(5)
        )
    ).all()
    samples = (
        await session.execute(
            select(APILog).where(*filters).order_by(desc(APILog.created_at)).limit(limit)
        )
    ).scalars().all()
    return {
        "window_hours": hours,
        "filters": {"status_code": status_code, "endpoint": endpoint},
        "total_errors": sum(int(c) for _, c in by_status),
        "by_status_code": [{"status_code": int(s), "count": int(c)} for s, c in by_status],
        "by_endpoint": [{"endpoint": e, "count": int(c)} for e, c in by_endpoint],
        "recent_samples": [
            {"time": s.created_at.isoformat(timespec="seconds"), "method": s.method, "endpoint": s.endpoint,
             "status_code": s.status_code, "latency_ms": round(s.response_time_ms, 1),
             "cache_hit": s.cache_hit, "correlation_id": s.correlation_id}
            for s in samples
        ],
    }


async def search_documentation(session: AsyncSession, query: str, top_k: int = 3) -> List[RetrievedChunk]:
    """Semantic search over uploaded documents; empty list when nothing is relevant."""
    return await RetrievalService(session).search(query, top_k=top_k)
