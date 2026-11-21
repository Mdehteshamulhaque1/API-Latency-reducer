"""Chat: signed-in Esone users ask questions; the API Optimizer answers them.

The browser never sees the Optimizer. Esone authenticates the user, forwards
the question with its own service account plus an opaque end-user reference
(``esone:<user id>``) so the Optimizer can keep per-user records while its
answer cache stays shared, and returns the answer with its cache, source,
latency and cost metadata.

Every request, successful or not, is written to ``chat_messages`` for the
user who made it. That table is the user's private query log: it feeds
their history and their "My activity" page, and every query filters on the
signed-in user's id, never on anything the browser sends.
"""
import json
import time
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import delete, func, select

from esone_api.deps import CurrentUser, SessionDep
from esone_api.models import ChatMessage
from esone_api.optimizer import NOT_CONFIGURED, get_optimizer
from esone_api.schemas import (
    AnswerResponse,
    AskRequest,
    ChatHistory,
    ChatHistoryCleared,
    ChatHistoryItem,
    ChatLatencyPoint,
    ChatStats,
    ChatStatus,
    NameCount,
)
from esone_api.telemetry import current_correlation_id, end_user_ref, mark_cache_hit

router = APIRouter(prefix="/chat", tags=["chat"])

HISTORY_DEFAULT = 50
HISTORY_MAX = 200
STATS_RECENT = 10
STATS_SERIES = 40
STATS_SAMPLE = 2000
STATUS_OK = "ok"
STATUS_ERROR = "error"


def _sources(row: ChatMessage) -> list[dict]:
    try:
        raw = json.loads(row.sources or "[]")
    except ValueError:
        return []
    return [s for s in raw if isinstance(s, dict)]


def _history_item(row: ChatMessage) -> ChatHistoryItem:
    return ChatHistoryItem(
        id=row.id,
        created_at=row.created_at,
        question=row.question,
        answer=row.answer,
        status=row.status or STATUS_OK,
        error_message=row.error_message,
        answered_by=row.answered_by if row.answered_by in ("cache", "model") else "crawler",
        cached=row.cached,
        cache_type=row.cache_type or ("miss" if row.status == STATUS_OK else "none"),
        match_method=row.match_method,
        similarity=row.similarity,
        compose_method=row.compose_method,
        sources=_sources(row),
        sources_count=row.sources_count or 0,
        latency_ms=row.latency_ms,
        cache_lookup_ms=row.cache_lookup_ms or 0.0,
        crawl_ms=row.crawl_ms,
        llm_ms=row.llm_ms or 0.0,
        total_tokens=row.total_tokens or 0,
        estimated_cost_usd=row.estimated_cost_usd or 0.0,
        served_model=row.served_model,
        correlation_id=row.correlation_id,
        cache_status=row.cache_status or ("miss" if row.status == STATUS_OK else "none"),
        embedding_tokens=row.embedding_tokens or 0,
        prompt_tokens=row.prompt_tokens or 0,
        completion_tokens=row.completion_tokens or 0,
        llm_cost_usd=row.llm_cost_usd or 0.0,
        embedding_cost_usd=row.embedding_cost_usd or 0.0,
        total_cost_usd=row.total_cost_usd or 0.0,
        saved_cost_usd=row.saved_cost_usd or 0.0,
        billable_tokens=row.billable_tokens or 0,
        cost_inr=row.cost_inr or 0.0,
    )


def _cache_type(answer: AnswerResponse) -> str:
    if not answer.cached:
        return "miss"
    return "exact" if answer.match_method == "exact" else "semantic"


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round(pct / 100 * (len(ordered) - 1))))
    return round(ordered[index], 2)


@router.get("/status", response_model=ChatStatus)
async def chat_status(_: CurrentUser):
    """Whether this server has an Optimizer configured (no request is made)."""
    return ChatStatus(configured=get_optimizer() is not None)


@router.post("", response_model=AnswerResponse)
async def ask(data: AskRequest, user: CurrentUser, session: SessionDep):
    client = get_optimizer()
    if client is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=NOT_CONFIGURED)
    started = time.perf_counter()
    correlation_id = current_correlation_id.get() or None
    try:
        result = await client.ask(
            data.question, user_ref=end_user_ref(user.id), user_name=user.username, user_email=user.email
        )
    except HTTPException as exc:
        # The user's record exists even when the Optimizer said no.
        session.add(
            ChatMessage(
                user_id=user.id,
                question=" ".join(data.question.split()),
                answer="",
                status=STATUS_ERROR,
                error_message=str(exc.detail)[:255],
                answered_by="none",
                cached=False,
                cache_type="none",
                cache_status="none",
                sources="[]",
                sources_count=0,
                latency_ms=(time.perf_counter() - started) * 1000,
                correlation_id=correlation_id,
            )
        )
        await session.commit()
        raise
    # Telemetry: a cached answer counts as a cache hit for this request.
    mark_cache_hit(bool(result.get("cached")))
    answer = AnswerResponse.model_validate(result)

    session.add(
        ChatMessage(
            user_id=user.id,
            question=answer.question,
            answer=answer.answer,
            status=STATUS_OK,
            answered_by=answer.answered_by,
            cached=answer.cached,
            cache_type=_cache_type(answer),
            match_method=answer.match_method,
            similarity=answer.similarity,
            compose_method=answer.compose_method,
            sources=json.dumps([s.model_dump() for s in answer.sources]),
            sources_count=len(answer.sources),
            latency_ms=answer.latency_ms,
            cache_lookup_ms=answer.cache_lookup_ms,
            crawl_ms=answer.crawl_ms,
            llm_ms=answer.llm_ms,
            total_tokens=answer.total_tokens,
            estimated_cost_usd=answer.total_cost_usd or answer.estimated_cost_usd,
            served_model=answer.served_model,
            correlation_id=correlation_id,
            cache_status=answer.cache_status,
            embedding_tokens=answer.embedding_tokens,
            prompt_tokens=answer.prompt_tokens,
            completion_tokens=answer.completion_tokens,
            llm_cost_usd=answer.llm_cost_usd,
            embedding_cost_usd=answer.embedding_cost_usd,
            total_cost_usd=answer.total_cost_usd or answer.estimated_cost_usd,
            saved_cost_usd=answer.saved_cost_usd,
            billable_tokens=answer.billable_tokens,
            cost_inr=answer.cost_inr,
        )
    )
    await session.commit()
    return answer


@router.get("/history", response_model=ChatHistory)
async def history(
    user: CurrentUser,
    session: SessionDep,
    limit: int = Query(default=HISTORY_DEFAULT, ge=1, le=HISTORY_MAX),
):
    """The signed-in user's answered questions, oldest first (so they read like a conversation)."""
    own = (ChatMessage.user_id == user.id, ChatMessage.status == STATUS_OK)
    total = await session.scalar(select(func.count(ChatMessage.id)).where(*own))
    rows = (
        await session.execute(
            select(ChatMessage).where(*own).order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc()).limit(limit)
        )
    ).scalars().all()
    return ChatHistory(items=[_history_item(row) for row in reversed(rows)], total=int(total or 0))


@router.delete("/history", response_model=ChatHistoryCleared)
async def clear_history(user: CurrentUser, session: SessionDep):
    """Forget the signed-in user's chat history (answers and failed requests)."""
    result = await session.execute(delete(ChatMessage).where(ChatMessage.user_id == user.id))
    await session.commit()
    return ChatHistoryCleared(deleted=int(result.rowcount or 0))


@router.get("/stats", response_model=ChatStats)
async def stats(
    user: CurrentUser,
    session: SessionDep,
    hours: int = Query(default=24 * 30, ge=1, le=24 * 365),
):
    """The signed-in user's own activity: counts, cache outcomes, latency, cost, sources and errors."""
    since = datetime.now(UTC) - timedelta(hours=hours)
    rows = (
        await session.execute(
            select(ChatMessage)
            .where(ChatMessage.user_id == user.id, ChatMessage.created_at >= since)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(STATS_SAMPLE)
        )
    ).scalars().all()

    ok = [r for r in rows if (r.status or STATUS_OK) == STATUS_OK]
    errors = [r for r in rows if (r.status or STATUS_OK) != STATUS_OK]
    hits = [r for r in ok if r.cached]
    misses = [r for r in ok if not r.cached]
    exact = sum(1 for r in hits if (r.cache_type or "") == "exact" or r.match_method == "exact")
    latencies = [float(r.latency_ms or 0.0) for r in ok]

    def avg(values: list[float]) -> float:
        return round(sum(values) / len(values), 2) if values else 0.0

    by_source: dict[str, int] = {}
    for r in misses:
        if r.answered_by == "model":
            by_source["gemini"] = by_source.get("gemini", 0) + 1
        for s in _sources(r):
            name = str(s.get("source") or "web")
            by_source[name] = by_source.get(name, 0) + 1
    by_model: dict[str, int] = {}
    for r in ok:
        if r.served_model:
            by_model[r.served_model] = by_model.get(r.served_model, 0) + 1
    by_error: dict[str, int] = {}
    for r in errors:
        key = (r.error_message or "error")[:60]
        by_error[key] = by_error.get(key, 0) + 1

    series = [
        ChatLatencyPoint(at=r.created_at, latency_ms=float(r.latency_ms or 0.0), cached=bool(r.cached))
        for r in reversed(ok[:STATS_SERIES])
    ]
    return ChatStats(
        hours=hours,
        total_queries=len(rows),
        answered=len(ok),
        errors=len(errors),
        cache_hits=len(hits),
        exact_hits=exact,
        semantic_hits=len(hits) - exact,
        misses=len(misses),
        cache_hit_rate=round(len(hits) / len(ok) * 100, 2) if ok else 0.0,
        avg_latency_ms=avg(latencies),
        avg_latency_cached_ms=avg([float(r.latency_ms or 0.0) for r in hits]),
        avg_latency_crawled_ms=avg([float(r.latency_ms or 0.0) for r in misses]),
        p50_latency_ms=_percentile(latencies, 50),
        p95_latency_ms=_percentile(latencies, 95),
        p99_latency_ms=_percentile(latencies, 99),
        total_tokens=sum(int(r.total_tokens or 0) for r in ok),
        estimated_cost_usd=round(sum(float(r.estimated_cost_usd or 0.0) for r in ok), 6),
        embedding_tokens=sum(int(r.embedding_tokens or 0) for r in ok),
        llm_cost_usd=round(sum(float(r.llm_cost_usd or 0.0) for r in ok), 8),
        embedding_cost_usd=round(sum(float(r.embedding_cost_usd or 0.0) for r in ok), 8),
        total_cost_usd=round(sum(float(r.total_cost_usd or 0.0) for r in ok), 8),
        saved_cost_usd=round(sum(float(r.saved_cost_usd or 0.0) for r in ok), 8),
        billable_tokens=sum(int(r.billable_tokens or 0) for r in ok),
        cost_inr=round(sum(float(r.cost_inr or 0.0) for r in ok), 2),
        bypassed=sum(1 for r in ok if (r.cache_status or "") == "bypassed"),
        sources_used=sum(int(r.sources_count or 0) for r in misses),
        by_source=[NameCount(name=k, count=v) for k, v in sorted(by_source.items(), key=lambda kv: -kv[1])],
        by_model=[NameCount(name=k, count=v) for k, v in sorted(by_model.items(), key=lambda kv: -kv[1])],
        by_error=[NameCount(name=k, count=v) for k, v in sorted(by_error.items(), key=lambda kv: -kv[1])],
        latency_series=series,
        recent=[_history_item(r) for r in rows[:STATS_RECENT]],
        recent_errors=[_history_item(r) for r in errors[:STATS_RECENT]],
    )
