"""
Analytics API routes.
"""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.database.db import get_session
from app.schemas.analytics import AnalyticsSummary
from app.services.analytics import AnalyticsService
from app.tasks.reports import persist_benchmark_report

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    hours: int = Query(default=24, gt=0, le=720),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get analytics summary for the current user."""
    try:
        analytics_service = AnalyticsService(session)
        return await analytics_service.get_analytics_summary(
            user_id=int(current_user.get("sub")),
            hours=hours,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/endpoints")
@router.get("/endpoints/{endpoint_path}")
async def get_endpoint_analytics(
    endpoint_path: Optional[str] = None,
    endpoint_pattern: Optional[str] = None,
    hours: int = Query(default=24, gt=0, le=720),
    limit: int = Query(default=100, gt=0, le=500),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get analytics for a specific endpoint."""
    try:
        analytics_service = AnalyticsService(session)
        pattern = endpoint_path or endpoint_pattern or ""
        logs = await analytics_service.get_endpoint_logs(
            endpoint_pattern=pattern,
            user_id=int(current_user.get("sub")),
            limit=limit,
            hours=hours,
        )
        return [log.to_dict() for log in logs]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/benchmark")
async def get_benchmark_report(
    hours: int = Query(default=24, gt=0, le=720),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get a simple before/after latency benchmark report."""
    analytics_service = AnalyticsService(session)
    return await analytics_service.get_endpoint_benchmark(
        user_id=int(current_user.get("sub")),
        hours=hours,
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
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Return heuristic optimization recommendations."""
    analytics_service = AnalyticsService(session)
    return await analytics_service.get_optimization_suggestions(
        user_id=int(current_user.get("sub")),
        hours=hours,
    )
