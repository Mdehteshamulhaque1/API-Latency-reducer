"""
Analytics API routes.

Every read accepts ``service``: the name of a monitored application whose
rows were shipped to POST /ingest/requests (for example ``esone``). With it,
that service's traffic is analysed for any dashboard user; without it the
caller's own requests through this gateway are returned. ``direction``
narrows to the requests a service served ("inbound") or the calls it made
("outbound").
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DIRECTIONS
from app.core.security import get_current_user
from app.core.view_as import AsUserParam, resolve_view_as
from app.database.db import get_session
from app.schemas.analytics import AnalyticsSummary, MonitoredService, QueryBreakdown, SlowEndpointRankingItem
from app.schemas.ingest import SERVICE_NAME_PATTERN
from app.services.analytics import AnalyticsService, persist_benchmark_report
from app.services.query_breakdown import QueryBreakdownService

router = APIRouter(prefix="/analytics", tags=["Analytics"])
logger = logging.getLogger(__name__)

ServiceParam = Query(default=None, pattern=SERVICE_NAME_PATTERN, description="Monitored service name")
DirectionParam = Query(default=None, pattern="^(" + "|".join(DIRECTIONS) + ")$")


def _scoped(current_user: dict, as_user: Optional[str], service: Optional[str], direction: Optional[str] = None):
    """(user_id, service, direction, end_user) for a read.

    One user when an admin views as them (an account by id, an end user by the
    reference their service tags rows with), else as before.
    """
    view = resolve_view_as(current_user, as_user)
    if view is not None:
        if view.end_user is not None:
            return None, None, None, view.end_user
        return view.user_id, None, None, None
    return int(current_user.get("sub")), service, direction, None


@router.get("/services", response_model=List[MonitoredService])
async def list_services(
    hours: int = Query(default=24, gt=0, le=720),
    _: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Services with request rows in the window: this gateway and every monitored application."""
    return await AnalyticsService(session).get_services(hours=hours)


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    hours: int = Query(default=24, gt=0, le=720),
    service: Optional[str] = ServiceParam,
    direction: Optional[str] = DirectionParam,
    as_user: Optional[str] = AsUserParam,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Analytics summary for a monitored service, or for the current user's own requests."""
    user_id, service, direction, end_user = _scoped(current_user, as_user, service, direction)
    try:
        analytics_service = AnalyticsService(session, end_user=end_user)
        return await analytics_service.get_analytics_summary(
            user_id=user_id,
            hours=hours,
            service=service,
            direction=direction,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to build analytics summary: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/queries", response_model=QueryBreakdown)
async def get_query_breakdown(
    hours: int = Query(default=24, gt=0, le=720),
    service: Optional[str] = ServiceParam,
    as_user: Optional[str] = AsUserParam,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> QueryBreakdown:
    """Real queries (questions users asked) apart from sign-in, history and health traffic, with their cost."""
    user_id, service, _, end_user = _scoped(current_user, as_user, service)
    return await QueryBreakdownService(session).breakdown(
        hours=hours, user_id=user_id, service=service, end_user=end_user
    )


@router.get("/endpoints")
@router.get("/endpoints/{endpoint_path}")
async def get_endpoint_analytics(
    endpoint_path: Optional[str] = None,
    endpoint_pattern: Optional[str] = None,
    hours: int = Query(default=24, gt=0, le=720),
    limit: int = Query(default=100, gt=0, le=500),
    service: Optional[str] = ServiceParam,
    direction: Optional[str] = DirectionParam,
    method: Optional[str] = Query(default=None, pattern=r"^[A-Za-z]{3,10}$", description="HTTP method, e.g. POST"),
    as_user: Optional[str] = AsUserParam,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Raw request-log rows whose endpoint contains the pattern, optionally one HTTP method."""
    user_id, service, direction, end_user = _scoped(current_user, as_user, service, direction)
    try:
        analytics_service = AnalyticsService(session, end_user=end_user)
        pattern = endpoint_path or endpoint_pattern or ""
        logs = await analytics_service.get_endpoint_logs(
            endpoint_pattern=pattern,
            user_id=user_id,
            limit=limit,
            hours=hours,
            service=service,
            direction=direction,
            method=method,
        )
        return [log.to_dict() for log in logs]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch endpoint analytics: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/benchmark")
async def get_benchmark_report(
    hours: int = Query(default=24, gt=0, le=720),
    service: Optional[str] = ServiceParam,
    as_user: Optional[str] = AsUserParam,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get a simple before/after latency benchmark report."""
    user_id, service, _, end_user = _scoped(current_user, as_user, service)
    analytics_service = AnalyticsService(session, end_user=end_user)
    return await analytics_service.get_endpoint_benchmark(
        user_id=user_id,
        hours=hours,
        service=service,
    )


@router.get("/slow-endpoints", response_model=List[SlowEndpointRankingItem])
async def get_slow_endpoint_ranking(
    hours: int = Query(default=24, gt=0, le=720),
    limit: int = Query(default=10, gt=0, le=50),
    service: Optional[str] = ServiceParam,
    direction: Optional[str] = DirectionParam,
    as_user: Optional[str] = AsUserParam,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get the ranked list of slow endpoints by p95 latency."""
    user_id, service, direction, end_user = _scoped(current_user, as_user, service, direction)
    analytics_service = AnalyticsService(session, end_user=end_user)
    return await analytics_service.get_top_slow_endpoints(
        user_id=user_id,
        hours=hours,
        limit=limit,
        service=service,
        direction=direction,
    )


@router.post("/benchmark/run")
async def run_benchmark_job(
    background_tasks: BackgroundTasks,
    hours: int = Query(default=24, gt=0, le=720),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Schedule a background benchmark report generation."""
    analytics_service = AnalyticsService(session)
    report = await analytics_service.get_endpoint_benchmark(
        user_id=int(current_user.get("sub")),
        hours=hours,
    )
    background_tasks.add_task(persist_benchmark_report, report.model_dump())
    return {"status": "scheduled", "hours": hours, "report": report}


@router.get("/suggestions")
async def get_optimization_suggestions(
    hours: int = Query(default=24, gt=0, le=720),
    service: Optional[str] = ServiceParam,
    as_user: Optional[str] = AsUserParam,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Return heuristic optimization recommendations."""
    user_id, service, _, end_user = _scoped(current_user, as_user, service)
    analytics_service = AnalyticsService(session, end_user=end_user)
    return await analytics_service.get_optimization_suggestions(
        user_id=user_id,
        hours=hours,
        service=service,
    )
