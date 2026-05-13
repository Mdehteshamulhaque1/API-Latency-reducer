"""
Analytics service for tracking and computing API metrics.
"""
from collections import defaultdict
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import APILog, Analytics
from app.schemas.analytics import (
    AnalyticsSummary,
    BenchmarkReport,
    LatencyPoint,
    OptimizationSuggestion,
    RecentRequest,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Tracks API requests and computes analytics for dashboards.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_request(
        self,
        method: str,
        endpoint: str,
        path: str,
        status_code: int,
        response_time_ms: float,
        client_ip: str,
        correlation_id: str,
        user_id: Optional[int] = None,
        cache_hit: bool = False,
        cache_key: Optional[str] = None,
        request_size_bytes: int = 0,
        response_size_bytes: int = 0,
        query_params: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> APILog:
        """Log an API request."""
        api_log = APILog(
            user_id=user_id,
            method=method,
            endpoint=endpoint,
            path=path,
            status_code=status_code,
            response_time_ms=response_time_ms,
            cache_hit=cache_hit,
            cache_key=cache_key,
            client_ip=client_ip,
            correlation_id=correlation_id,
            request_size_bytes=request_size_bytes,
            response_size_bytes=response_size_bytes,
            query_params=query_params,
            error_message=error_message,
        )

        self.session.add(api_log)
        await self.session.commit()

        return api_log

    async def get_analytics_summary(
        self,
        user_id: Optional[int] = None,
        hours: int = 24,
    ) -> AnalyticsSummary:
        """Get aggregated analytics summary."""
        since = datetime.utcnow() - timedelta(hours=hours)

        query = select(APILog).where(APILog.created_at >= since)
        if user_id is not None:
            query = query.where(APILog.user_id == user_id)

        result = await self.session.execute(query.order_by(APILog.created_at.asc()))
        logs = result.scalars().all()

        if not logs:
            return AnalyticsSummary(
                total_requests=0,
                total_errors=0,
                cache_hit_rate=0.0,
                avg_response_time_ms=0.0,
                slowest_endpoint=None,
                slowest_response_time_ms=None,
                top_endpoints=[],
                error_rate=0.0,
                request_rate_per_minute=0.0,
                cache_miss_rate=0.0,
                recent_requests=[],
                latency_series=[],
                slow_endpoints=[],
                optimization_suggestions=[],
                benchmark=None,
            )

        total_requests = len(logs)
        total_errors = sum(1 for log in logs if log.status_code >= 400)
        cache_hits = sum(1 for log in logs if log.cache_hit)
        cache_misses = total_requests - cache_hits
        avg_response_time = sum(log.response_time_ms for log in logs) / total_requests
        slowest_log = max(logs, key=lambda item: item.response_time_ms)

        endpoint_stats: dict[str, dict[str, float | int]] = {}
        for log in logs:
            stats = endpoint_stats.setdefault(
                log.endpoint,
                {"count": 0, "total_time": 0.0, "errors": 0, "cache_hits": 0},
            )
            stats["count"] += 1
            stats["total_time"] += log.response_time_ms
            if log.status_code >= 400:
                stats["errors"] += 1
            if log.cache_hit:
                stats["cache_hits"] += 1

        top_endpoints = []
        for endpoint, stats in sorted(
            endpoint_stats.items(),
            key=lambda item: item[1]["count"],
            reverse=True,
        )[:10]:
            count = max(int(stats["count"]), 1)
            total_time = float(stats["total_time"])
            top_endpoints.append(
                {
                    "endpoint": endpoint,
                    "count": int(stats["count"]),
                    "avg_time": round(total_time / count, 2),
                    "errors": int(stats["errors"]),
                    "cache_hit_rate": round((int(stats["cache_hits"]) / count) * 100, 2),
                }
            )

        recent_requests = [
            RecentRequest(
                endpoint=log.endpoint,
                method=log.method,
                status_code=log.status_code,
                response_time_ms=log.response_time_ms,
                cache_hit=log.cache_hit,
                created_at=log.created_at,
            )
            for log in sorted(logs, key=lambda item: item.created_at, reverse=True)[:10]
        ]

        latency_series = self._build_latency_series(logs, hours)
        slow_endpoints = self._build_slow_endpoints(top_endpoints)
        optimization_suggestions = self._build_suggestions(
            total_requests=total_requests,
            total_errors=total_errors,
            cache_hit_rate=(cache_hits / total_requests) * 100,
            avg_response_time_ms=avg_response_time,
            slowest_response_time_ms=slowest_log.response_time_ms,
            slow_endpoints=slow_endpoints,
        )
        benchmark = self._build_benchmark_report(logs, since)

        return AnalyticsSummary(
            total_requests=total_requests,
            total_errors=total_errors,
            cache_hit_rate=(cache_hits / total_requests * 100),
            avg_response_time_ms=avg_response_time,
            slowest_endpoint=slowest_log.endpoint,
            slowest_response_time_ms=slowest_log.response_time_ms,
            top_endpoints=top_endpoints,
            error_rate=(total_errors / total_requests * 100),
            request_rate_per_minute=round(total_requests / max(hours * 60, 1), 2),
            cache_miss_rate=(cache_misses / total_requests * 100),
            recent_requests=recent_requests,
            latency_series=latency_series,
            slow_endpoints=slow_endpoints,
            optimization_suggestions=optimization_suggestions,
            benchmark=benchmark,
        )

    async def get_endpoint_logs(
        self,
        endpoint_pattern: str,
        user_id: Optional[int] = None,
        limit: int = 100,
        hours: Optional[int] = None,
    ) -> List[APILog]:
        """Get API logs for a specific endpoint."""
        query = select(APILog).where(APILog.endpoint.like(f"%{endpoint_pattern}%"))

        if user_id is not None:
            query = query.where(APILog.user_id == user_id)

        if hours:
            since = datetime.utcnow() - timedelta(hours=hours)
            query = query.where(APILog.created_at >= since)

        query = query.order_by(desc(APILog.created_at)).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_endpoint_benchmark(self, user_id: Optional[int] = None, hours: int = 24) -> BenchmarkReport:
        """Return a lightweight before/after benchmark report."""
        since = datetime.utcnow() - timedelta(hours=hours)
        query = select(APILog).where(APILog.created_at >= since)
        if user_id is not None:
            query = query.where(APILog.user_id == user_id)

        result = await self.session.execute(query.order_by(APILog.created_at.asc()))
        logs = result.scalars().all()
        return self._build_benchmark_report(logs, since)

    async def get_optimization_suggestions(self, user_id: Optional[int] = None, hours: int = 24) -> List[OptimizationSuggestion]:
        """Return AI-style optimization hints derived from request patterns."""
        summary = await self.get_analytics_summary(user_id=user_id, hours=hours)
        return summary.optimization_suggestions

    def _build_latency_series(self, logs: List[APILog], hours: int) -> List[LatencyPoint]:
        bucket_count = max(1, min(12, hours))
        bucket_minutes = max(5, int((hours * 60) / bucket_count))
        bucket_size = timedelta(minutes=bucket_minutes)

        first_timestamp = min(log.created_at for log in logs)
        buckets: dict[str, dict[str, float | int]] = {}

        for log in logs:
            elapsed = log.created_at - first_timestamp
            bucket_index = int(elapsed.total_seconds() // bucket_size.total_seconds())
            bucket_start = first_timestamp + bucket_size * bucket_index
            bucket_key = bucket_start.isoformat(timespec="seconds")
            stats = buckets.setdefault(bucket_key, {"count": 0, "errors": 0, "total_time": 0.0})
            stats["count"] += 1
            stats["total_time"] += log.response_time_ms
            if log.status_code >= 400:
                stats["errors"] += 1

        series: List[LatencyPoint] = []
        for timestamp, stats in sorted(buckets.items()):
            count = max(int(stats["count"]), 1)
            series.append(
                LatencyPoint(
                    timestamp=timestamp,
                    avg_response_time_ms=round(float(stats["total_time"]) / count, 2),
                    request_count=int(stats["count"]),
                    error_count=int(stats["errors"]),
                )
            )
        return series

    def _build_slow_endpoints(self, top_endpoints: List[dict]) -> List[dict]:
        slow_endpoints = [
            endpoint
            for endpoint in top_endpoints
            if endpoint["avg_time"] >= 300 or endpoint["errors"] > 0
        ]
        if not slow_endpoints:
            slow_endpoints = top_endpoints[:3]
        return sorted(slow_endpoints, key=lambda item: item["avg_time"], reverse=True)

    def _build_suggestions(
        self,
        total_requests: int,
        total_errors: int,
        cache_hit_rate: float,
        avg_response_time_ms: float,
        slowest_response_time_ms: float,
        slow_endpoints: List[dict],
    ) -> List[OptimizationSuggestion]:
        suggestions: List[OptimizationSuggestion] = []

        if cache_hit_rate < 65:
            suggestions.append(
                OptimizationSuggestion(
                    title="Increase cache coverage",
                    severity="high",
                    reason=f"Cache hit rate is only {cache_hit_rate:.1f}% across {total_requests} requests.",
                    action="Apply route-wise caching to high-traffic GET endpoints and warm them on startup.",
                )
            )

        if avg_response_time_ms > 250:
            suggestions.append(
                OptimizationSuggestion(
                    title="Reduce average latency",
                    severity="medium",
                    reason=f"Average response time is {avg_response_time_ms:.0f}ms.",
                    action="Move expensive work to background tasks and reduce synchronous database work.",
                )
            )

        if slowest_response_time_ms > 750 and slow_endpoints:
            suggestions.append(
                OptimizationSuggestion(
                    title="Inspect slow endpoints",
                    severity="high",
                    endpoint=slow_endpoints[0]["endpoint"],
                    reason=f"Slowest observed latency is {slowest_response_time_ms:.0f}ms.",
                    action="Add query indexes, tighten select lists, and consider caching responses.",
                )
            )

        error_rate = (total_errors / total_requests * 100) if total_requests else 0.0
        if error_rate > 2:
            suggestions.append(
                OptimizationSuggestion(
                    title="Harden error handling",
                    severity="medium",
                    reason=f"Error rate is {error_rate:.2f}%.",
                    action="Add retries for transient upstream calls and normalize exception responses.",
                )
            )

        if not suggestions:
            suggestions.append(
                OptimizationSuggestion(
                    title="System is healthy",
                    severity="low",
                    reason="No major bottlenecks were detected in the sampled window.",
                    action="Keep monitoring latency, cache hit rate, and slow endpoint drift.",
                )
            )

        return suggestions[:4]

    def _build_benchmark_report(self, logs: List[APILog], since: datetime) -> BenchmarkReport:
        if not logs:
            return BenchmarkReport(
                baseline_avg_response_time_ms=0.0,
                optimized_avg_response_time_ms=0.0,
                improvement_percent=0.0,
                sample_size=0,
                before_window=since.isoformat(timespec="seconds"),
                after_window=since.isoformat(timespec="seconds"),
            )

        ordered_logs = sorted(logs, key=lambda item: item.created_at)
        midpoint = max(1, len(ordered_logs) // 2)
        baseline_logs = ordered_logs[:midpoint]
        optimized_logs = ordered_logs[midpoint:] or baseline_logs

        baseline_avg = sum(log.response_time_ms for log in baseline_logs) / len(baseline_logs)
        optimized_avg = sum(log.response_time_ms for log in optimized_logs) / len(optimized_logs)
        improvement = ((baseline_avg - optimized_avg) / baseline_avg * 100) if baseline_avg else 0.0

        return BenchmarkReport(
            baseline_avg_response_time_ms=round(baseline_avg, 2),
            optimized_avg_response_time_ms=round(optimized_avg, 2),
            improvement_percent=round(improvement, 2),
            sample_size=len(ordered_logs),
            before_window=f"{since.isoformat(timespec='seconds')} -> {baseline_logs[-1].created_at.isoformat(timespec='seconds')}",
            after_window=f"{optimized_logs[0].created_at.isoformat(timespec='seconds')} -> {ordered_logs[-1].created_at.isoformat(timespec='seconds')}",
        )
