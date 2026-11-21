"""
Question answering: shared semantic cache, then generation.

    identify caller (gateway account + optional end-user reference)
      -> guardrails screen (injection scan, PII masking)
      -> AnswerService (shared Redis cache -> model knowledge -> Wikipedia -> other sources)
      -> response with cache status / similarity / source / token / cost metadata
      -> background: per-caller answer_logs row + Redis recent list

Every request gets its own record, including shared cache hits, blocked
requests and crawler failures. Questions where personal data was masked
are answered but never written to the shared cache.

Reads for dashboards:
    GET /answers/recent  asked questions with their answers (Redis for the
                         last hour, database for longer windows; paginated,
                         filter by end user and cache status)
    GET /answers/top     most asked questions in the window
    GET /answers/stats   hit rate, latencies, sources, tokens and cost
    GET /answers/cache   what the shared cache holds now and how it performed
    GET /answers/costs   LLM vs embedding spend and estimated savings
    GET /answers/users   per end-user / account totals, paginated

Admins see every user's questions; other roles see their own. With
``service`` the questions a monitored service's gateway account asked
(e.g. Esone's) are shown instead, for any role. ``end_user`` narrows any
read to one end user of that service. Ownership is enforced in the query.
"""
import time
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.guardrails import screen_messages
from app.ai.guardrails.events import record_events
from app.core.exceptions import APIException
from app.core.security import get_current_user
from app.core.view_as import AsUserParam, resolve_view_as
from app.database.db import get_session
from app.schemas.answers import (
    END_USER_PATTERN,
    AnswerLogPage,
    AnswerRequest,
    AnswerResponse,
    AnswerStats,
    CacheOverview,
    CostAnalytics,
    TopQuestionsPage,
    UserQueryStatsPage,
)
from app.schemas.chat import ChatMessage
from app.schemas.ingest import SERVICE_NAME_PATTERN
from app.services.analytics import AnalyticsService
from app.services.answer_history import (
    STATUS_BLOCKED,
    STATUS_ERROR,
    AnswerHistoryService,
    record_answer,
    record_answer_error,
)
from app.services.answers import get_answer_service
from app.services.users import upsert_end_user

router = APIRouter(prefix="/answers", tags=["Answers"])

ServiceParam = Query(default=None, pattern=SERVICE_NAME_PATTERN, description="Monitored service name")
EndUserParam = Query(default=None, pattern=END_USER_PATTERN, description="End-user reference, e.g. esone:42")
CacheStatusParam = Query(default=None, pattern=r"^(exact_hit|semantic_hit|miss|bypassed)$")
HoursParam = Query(default=24, gt=0, le=720)


async def _scope(
    current_user: dict, service: Optional[str], session: AsyncSession, as_user: Optional[str] = None
) -> tuple[str, int | None, Optional[str]]:
    """(scope, user_id, end_user). An admin viewing as an end user gets their rows by reference only."""
    view = resolve_view_as(current_user, as_user)
    if view is not None:
        if view.end_user is not None:
            return "user", None, view.end_user
        return "user", view.account_id, None
    scope, user_id = await _base_scope(current_user, service, session)
    return scope, user_id, None


async def _base_scope(current_user: dict, service: Optional[str], session: AsyncSession) -> tuple[str, int | None]:
    if service:
        account = await AnalyticsService(session).service_account_id(service)
        # No account yet: an id no row can carry, so the result is empty rather than everyone's.
        return "service", account if account is not None else -1
    if current_user.get("role") == "admin":
        return "all", None
    return "own", int(current_user.get("sub"))


@router.post("", response_model=AnswerResponse)
async def answer_question(
    payload: AnswerRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
) -> AnswerResponse:
    """Answer a question from the shared semantic cache or, on a miss, by generating it."""
    started = time.perf_counter()
    user_id = None
    try:
        user_id = int(current_user.get("sub"))
    except (TypeError, ValueError):
        pass
    end_user = payload.user_ref
    correlation_id = getattr(request.state, "correlation_id", None)
    if end_user:
        background_tasks.add_task(upsert_end_user, end_user, name=payload.user_name, email=payload.user_email)

    screen = screen_messages(
        [ChatMessage(role="user", content=payload.question)],
        feature="answers",
        user_id=user_id,
        correlation_id=correlation_id,
    )
    if screen.blocked:
        await record_events(screen.events)
        # Background tasks do not run when the handler raises, so record now.
        await record_answer_error(
            payload.question,
            user_id=user_id,
            end_user=end_user,
            correlation_id=correlation_id,
            status=STATUS_BLOCKED,
            error_code="GUARDRAIL_BLOCKED",
            latency_ms=(time.perf_counter() - started) * 1000,
        )
        raise APIException(
            message=screen.block_reason or "Request blocked by guardrails",
            status_code=400,
            error_code="GUARDRAIL_BLOCKED",
            details={"rules": screen.injection_rules},
        )
    if screen.events:
        await record_events(screen.events)

    # A question that carried personal data is answered for this caller only.
    cacheable = not bool(screen.pii_counts)
    question = screen.messages[0].content
    try:
        result = await get_answer_service().answer(
            question, user_id=user_id, correlation_id=correlation_id, cacheable=cacheable
        )
    except APIException as exc:
        await record_answer_error(
            question,
            user_id=user_id,
            end_user=end_user,
            correlation_id=correlation_id,
            status=STATUS_ERROR,
            error_code=str((exc.details or {}).get("reason") or exc.error_code or "error"),
            latency_ms=(time.perf_counter() - started) * 1000,
        )
        raise

    request.state.cache_hit = result.cached
    background_tasks.add_task(
        record_answer, result, user_id=user_id, end_user=end_user, correlation_id=correlation_id
    )
    return AnswerResponse(
        question=result.question,
        answer=result.answer,
        answered_by=result.answered_by,
        cached=result.cached,
        cache_status=result.cache_status,
        cache_id=result.cache_id,
        similarity=result.similarity,
        matched_question=result.matched_question,
        match_method=result.match_method,
        sources=result.sources,
        latency_ms=result.latency_ms,
        crawl_ms=result.crawl_ms,
        compose_method=result.compose_method,
        embedding_used=result.embedding_used,
        cache_lookup_ms=result.cache_lookup_ms,
        embedding_ms=result.embedding_ms,
        embedding_tokens=result.embedding_tokens,
        embedding_tokens_estimated=result.embedding_tokens_estimated,
        llm_ms=result.llm_ms,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        total_tokens=result.total_tokens,
        served_model=result.served_model,
        llm_cost_usd=result.llm_cost_usd,
        embedding_cost_usd=result.embedding_cost_usd,
        total_cost_usd=result.total_cost_usd,
        estimated_cost_usd=result.total_cost_usd,
        saved_cost_usd=result.saved_cost_usd,
        billable_tokens=result.billable_tokens,
        cost_inr=result.cost_inr,
        waited_for_generation=result.waited_for_generation,
        cacheable=result.cacheable,
    )


@router.get("/recent", response_model=AnswerLogPage)
async def recent_answers(
    hours: int = Query(default=1, gt=0, le=720),
    limit: int = Query(default=50, gt=0, le=500),
    offset: int = Query(default=0, ge=0),
    service: Optional[str] = ServiceParam,
    end_user: Optional[str] = EndUserParam,
    cache_status: Optional[str] = CacheStatusParam,
    as_user: Optional[str] = AsUserParam,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AnswerLogPage:
    """Asked questions with their answers, newest first."""
    scope, user_id, viewed_end_user = await _scope(current_user, service, session, as_user)
    return await AnswerHistoryService(session).recent(
        hours=hours, user_id=user_id, scope=scope, limit=limit, offset=offset,
        end_user=viewed_end_user or end_user, cache_status=cache_status,
    )


@router.get("/top", response_model=TopQuestionsPage)
async def top_questions(
    hours: int = HoursParam,
    limit: int = Query(default=10, gt=0, le=100),
    service: Optional[str] = ServiceParam,
    end_user: Optional[str] = EndUserParam,
    as_user: Optional[str] = AsUserParam,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TopQuestionsPage:
    """Most asked questions in the window, with their latest answer."""
    scope, user_id, viewed_end_user = await _scope(current_user, service, session, as_user)
    return await AnswerHistoryService(session).top(
        hours=hours, user_id=user_id, scope=scope, limit=limit, end_user=viewed_end_user or end_user
    )


@router.get("/stats", response_model=AnswerStats)
async def answer_stats(
    hours: int = HoursParam,
    service: Optional[str] = ServiceParam,
    end_user: Optional[str] = EndUserParam,
    as_user: Optional[str] = AsUserParam,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AnswerStats:
    """Cache hit rate, latencies, sources, tokens and cost over the window."""
    scope, user_id, viewed_end_user = await _scope(current_user, service, session, as_user)
    return await AnswerHistoryService(session).stats(hours=hours, user_id=user_id, scope=scope, end_user=viewed_end_user or end_user)


@router.get("/cache", response_model=CacheOverview)
async def cache_overview(
    hours: int = HoursParam,
    service: Optional[str] = ServiceParam,
    as_user: Optional[str] = AsUserParam,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CacheOverview:
    """What the shared answer cache holds right now, and its hit/miss record in the window."""
    scope, user_id, viewed_end_user = await _scope(current_user, service, session, as_user)
    return await AnswerHistoryService(session).cache_overview(hours=hours, user_id=user_id, scope=scope, end_user=viewed_end_user)


@router.get("/costs", response_model=CostAnalytics)
async def cost_analytics(
    hours: int = HoursParam,
    service: Optional[str] = ServiceParam,
    end_user: Optional[str] = EndUserParam,
    as_user: Optional[str] = AsUserParam,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CostAnalytics:
    """LLM versus embedding spend, tokens, calls avoided and estimated savings (estimates, not billing)."""
    scope, user_id, viewed_end_user = await _scope(current_user, service, session, as_user)
    return await AnswerHistoryService(session).costs(hours=hours, user_id=user_id, scope=scope, end_user=viewed_end_user or end_user)


@router.get("/users", response_model=UserQueryStatsPage)
async def user_query_stats(
    hours: int = HoursParam,
    limit: int = Query(default=50, gt=0, le=500),
    offset: int = Query(default=0, ge=0),
    service: Optional[str] = ServiceParam,
    as_user: Optional[str] = AsUserParam,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserQueryStatsPage:
    """Per-caller totals (end users of a monitored service, or gateway accounts), most active first."""
    scope, user_id, viewed_end_user = await _scope(current_user, service, session, as_user)
    return await AnswerHistoryService(session).users(
        hours=hours, user_id=user_id, scope=scope, limit=limit, offset=offset, end_user=viewed_end_user
    )
