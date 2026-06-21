"""
Analytics service for tracking and computing API metrics.

OPTIMIZATIONS:
- Uses SQL aggregations (GROUP BY, COUNT, AVG, SUM) for most computations
- Loads minimal data from database for percentile calculations
- Significantly reduces memory usage for large datasets
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import (
    func,
    desc,
    case,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import APILog, Analytics
from app.schemas.analytics import (
    AnalyticsSummary,
    BenchmarkReport,
    LatencyPoint,
    LatencyDistributionPoint,
    OptimizationSuggestion,
    RecentRequest,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Tracks API requests and computes analytics for dashboards.
    Uses database-side aggregations to minimize memory usage.
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
        await self._update_hourly_analytics(
            status_code=status_code,
            response_time_ms=response_time_ms,
            cache_hit=cache_hit,
            request_size_bytes=request_size_bytes,
            response_size_bytes=response_size_bytes,
        )
        await self.session.commit()

        await self.session.refresh(api_log)
        return api_log

    async def _update_hourly_analytics(
        self,
        status_code: int,
        response_time_ms: float,
        cache_hit: bool,
        request_size_bytes: int,
        response_size_bytes: int,
    ) -> None:
        """Update or create an hourly analytics aggregate record."""
        current_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        period_key = f"hourly:{current_hour.isoformat(timespec='minutes')}"

        result = await self.session.execute(
            select(Analytics).where(Analytics.period == period_key)
        )
        analytics = result.scalar_one_or_none()

        if not analytics:
            analytics = Analytics(
                period=period_key,
                total_requests=0,
                total_errors=0,
                cache_hits=0,
                cache_misses=0,
                avg_response_time_ms=0.0,
                min_response_time_ms=0.0,
                max_response_time_ms=0.0,
                total_bytes_sent=0,
                total_bytes_received=0,
            )
            self.session.add(analytics)
            await self.session.flush()

        previous_requests = analytics.total_requests
        analytics.total_requests += 1
        analytics.total_errors += 1 if status_code >= 400 else 0
        if cache_hit:
            analytics.cache_hits += 1
        else:
            analytics.cache_misses += 1

        if previous_requests == 0:
            analytics.avg_response_time_ms = response_time_ms
            analytics.min_response_time_ms = response_time_ms
            analytics.max_response_time_ms = response_time_ms
        else:
            analytics.avg_response_time_ms = (
                (analytics.avg_response_time_ms * previous_requests) + response_time_ms
            ) / analytics.total_requests
            analytics.min_response_time_ms = min(analytics.min_response_time_ms, response_time_ms)
            analytics.max_response_time_ms = max(analytics.max_response_time_ms, response_time_ms)

        analytics.total_bytes_received += request_size_bytes
        analytics.total_bytes_sent += response_size_bytes

    async def get_analytics_summary(
        self,
        user_id: Optional[int] = None,
        hours: int = 24,
    ) -> AnalyticsSummary:
        """
        Get aggregated analytics summary using database-side aggregations.
        Significantly reduces memory usage compared to loading all logs.
        """
        since = datetime.utcnow() - timedelta(hours=hours)

        # Fetch aggregate statistics using SQL
        # This computes: total requests, total errors, total cache hits
        agg_query = select(
            func.count(APILog.id).label("total_requests"),
            func.sum(
                case((APILog.status_code >= 400, 1), else_=0)
            ).label("total_errors"),
            func.sum(
                case((APILog.cache_hit == True, 1), else_=0)
            ).label("total_cache_hits"),
            func.avg(APILog.response_time_ms).label("avg_response_time"),
            func.max(APILog.response_time_ms).label("max_response_time"),
            func.min(APILog.response_time_ms).label("min_response_time"),
        ).where(APILog.created_at >= since)
        
        if user_id is not None:
            agg_query = agg_query.where(APILog.user_id == user_id)

        agg_result = await self.session.execute(agg_query)
        agg_row = agg_result.one_or_none()

        # Extract aggregate values
        total_requests = agg_row[0] or 0
        total_errors = agg_row[1] or 0
        total_cache_hits = agg_row[2] or 0
        avg_response_time = float(agg_row[3] or 0.0)
        max_response_time = float(agg_row[4] or 0.0)
        min_response_time = float(agg_row[5] or 0.0)

        if total_requests == 0:
            return self._empty_analytics_summary()

        total_cache_misses = total_requests - total_cache_hits
        cache_hit_rate = (total_cache_hits / total_requests) * 100

        # Fetch top endpoints by request count with aggregated stats
        top_endpoints = await self._get_top_endpoints_by_count(user_id, since, limit=10)

        # Get top slow endpoints (by p95 latency)
        slow_endpoint_ranking = await self._get_top_slow_endpoints_optimized(user_id, since, limit=10)

        # Fetch recent requests (last 10 for dashboard)
        recent_requests = await self._get_recent_requests(user_id, since, limit=10)

        # Compute overall percentiles using the database when available
        overall_p95 = await self._get_percentile(user_id, since, 95)
        overall_p99 = await self._get_percentile(user_id, since, 99)

        # Find slowest endpoint
        slowest_endpoint = await self._get_slowest_endpoint(user_id, since)

        # Build series and distribution data
        latency_series = await self._build_latency_series_optimized(user_id, since, hours)
        latency_distribution = await self._build_latency_distribution_optimized(user_id, since, hours)

        # Determine slow endpoints
        slow_endpoints = [
            ep for ep in top_endpoints
            if ep["avg_time"] >= 300 or ep["errors"] > 0
        ]
        if not slow_endpoints and top_endpoints:
            slow_endpoints = top_endpoints[:3]

        # Build optimization suggestions
        optimization_suggestions = self._build_suggestions(
            total_requests=total_requests,
            total_errors=total_errors,
            cache_hit_rate=cache_hit_rate,
            avg_response_time_ms=avg_response_time,
            slowest_response_time_ms=max_response_time,
            slow_endpoints=slow_endpoints,
            slow_endpoint_ranking=slow_endpoint_ranking,
        )

        # Build benchmark report
        benchmark = await self._build_benchmark_report_optimized(user_id, since)

        return AnalyticsSummary(
            total_requests=total_requests,
            total_errors=total_errors,
            cache_hit_rate=cache_hit_rate,
            avg_response_time_ms=avg_response_time,
            slowest_endpoint=slowest_endpoint["endpoint"] if slowest_endpoint else None,
            slowest_response_time_ms=max_response_time,
            top_endpoints=top_endpoints,
            slow_endpoint_ranking=slow_endpoint_ranking,
            overall_p95_response_time_ms=overall_p95,
            overall_p99_response_time_ms=overall_p99,
            error_rate=(total_errors / total_requests * 100) if total_requests else 0.0,
            request_rate_per_minute=round(total_requests / max(hours * 60, 1), 2),
            cache_miss_rate=(total_cache_misses / total_requests * 100) if total_requests else 0.0,
            recent_requests=recent_requests,
            latency_series=latency_series,
            latency_distribution=latency_distribution,
            slow_endpoints=slow_endpoints,
            optimization_suggestions=optimization_suggestions,
            benchmark=benchmark,
        )

    async def _get_top_endpoints_by_count(
        self,
        user_id: Optional[int] = None,
        since: Optional[datetime] = None,
        limit: int = 10,
    ) -> List[dict]:
        """
        Get top endpoints by request count with aggregated stats using SQL.
        Much more efficient than loading all logs.
        """
        query = select(
            APILog.endpoint,
            func.count(APILog.id).label("count"),
            func.avg(APILog.response_time_ms).label("avg_time"),
            func.sum(
                case((APILog.status_code >= 400, 1), else_=0)
            ).label("errors"),
            func.sum(
                case((APILog.cache_hit == True, 1), else_=0)
            ).label("cache_hits"),
        )

        if since:
            query = query.where(APILog.created_at >= since)
        if user_id is not None:
            query = query.where(APILog.user_id == user_id)

        query = (
            query.group_by(APILog.endpoint)
            .order_by(desc("count"))
            .limit(limit)
        )

        result = await self.session.execute(query)
        rows = result.all()

        top_endpoints = []
        for row in rows:
            endpoint, count, avg_time, errors, cache_hits = row
            count = int(count or 0)
            errors = int(errors or 0)
            cache_hits = int(cache_hits or 0)
            avg_time = float(avg_time or 0.0)

            top_endpoints.append(
                {
                    "endpoint": endpoint,
                    "count": count,
                    "avg_time": round(avg_time, 2),
                    "errors": errors,
                    "cache_hit_rate": round((cache_hits / count * 100) if count > 0 else 0.0, 2),
                }
            )

        return top_endpoints

    async def _get_top_slow_endpoints_optimized(
        self,
        user_id: Optional[int] = None,
        since: Optional[datetime] = None,
        limit: int = 10,
    ) -> List[dict]:
        """
        Get top endpoints ranked by p95 latency.
        Fetches response times per endpoint for percentile calculation.
        """
        # First, get endpoints with their basic aggregates
        query = select(
            APILog.endpoint,
            func.count(APILog.id).label("count"),
            func.avg(APILog.response_time_ms).label("avg_time"),
            func.sum(
                case((APILog.status_code >= 400, 1), else_=0)
            ).label("errors"),
            func.sum(
                case((APILog.cache_hit == True, 1), else_=0)
            ).label("cache_hits"),
        )

        if since:
            query = query.where(APILog.created_at >= since)
        if user_id is not None:
            query = query.where(APILog.user_id == user_id)

        query = (
            query.group_by(APILog.endpoint)
            .order_by(desc("count"))
            .limit(limit * 2)  # Get extra endpoints to rank by p95
        )

        result = await self.session.execute(query)
        endpoint_rows = result.all()

        # For each endpoint, fetch response times to compute percentiles
        ranking = []
        for row in endpoint_rows:
            endpoint, count, avg_time, errors, cache_hits = row
            count = int(count or 0)
            errors = int(errors or 0)
            cache_hits = int(cache_hits or 0)
            avg_time = float(avg_time or 0.0)

            p95 = await self._get_percentile_for_endpoint(endpoint, user_id, since, 95)
            p99 = await self._get_percentile_for_endpoint(endpoint, user_id, since, 99)

            ranking.append(
                {
                    "endpoint": endpoint,
                    "count": count,
                    "avg_time": round(avg_time, 2),
                    "p95_time": p95,
                    "p99_time": p99,
                    "errors": errors,
                    "cache_hit_rate": round((cache_hits / count * 100) if count > 0 else 0.0, 2),
                    "error_rate": round((errors / count * 100) if count > 0 else 0.0, 2),
                }
            )

        # Sort by p95 time descending and limit
        return sorted(ranking, key=lambda x: x["p95_time"], reverse=True)[:limit]

    async def _get_recent_requests(
        self,
        user_id: Optional[int] = None,
        since: Optional[datetime] = None,
        limit: int = 10,
    ) -> List[RecentRequest]:
        """Get recent requests for display on dashboard."""
        query = select(APILog).where(APILog.created_at >= (since or datetime.utcnow() - timedelta(hours=24)))
        if user_id is not None:
            query = query.where(APILog.user_id == user_id)

        query = query.order_by(desc(APILog.created_at)).limit(limit)

        result = await self.session.execute(query)
        logs = result.scalars().all()

        return [
            RecentRequest(
                endpoint=log.endpoint,
                method=log.method,
                status_code=log.status_code,
                response_time_ms=log.response_time_ms,
                cache_hit=log.cache_hit,
                created_at=log.created_at,
            )
            for log in logs
        ]

    async def _fetch_response_times(
        self,
        user_id: Optional[int] = None,
        since: Optional[datetime] = None,
    ) -> List[float]:
        """
        Fetch only response_time_ms values (minimal data) for percentile calculations.
        Much more efficient than loading entire APILog objects.
        """
        query = select(APILog.response_time_ms).where(
            APILog.created_at >= (since or datetime.utcnow() - timedelta(hours=24))
        )
        if user_id is not None:
            query = query.where(APILog.user_id == user_id)

        result = await self.session.execute(query)
        return [float(row[0]) for row in result.all()]

    async def _get_slowest_endpoint(
        self,
        user_id: Optional[int] = None,
        since: Optional[datetime] = None,
    ) -> Optional[dict]:
        """Get the endpoint with the slowest response time."""
        query = select(
            APILog.endpoint,
            APILog.response_time_ms,
        ).where(
            APILog.created_at >= (since or datetime.utcnow() - timedelta(hours=24))
        )
        if user_id is not None:
            query = query.where(APILog.user_id == user_id)

        query = query.order_by(desc(APILog.response_time_ms)).limit(1)

        result = await self.session.execute(query)
        row = result.one_or_none()

        if row:
            return {"endpoint": row[0], "response_time_ms": float(row[1])}
        return None

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

    async def get_endpoint_benchmark(
        self, user_id: Optional[int] = None, hours: int = 24
    ) -> BenchmarkReport:
        """Return a lightweight before/after benchmark report."""
        return await self._build_benchmark_report_optimized(user_id, datetime.utcnow() - timedelta(hours=hours))

    async def get_top_slow_endpoints(
        self, user_id: Optional[int] = None, hours: int = 24, limit: int = 10
    ) -> List[dict]:
        """Return the top slow endpoints sorted by p95 latency."""
        since = datetime.utcnow() - timedelta(hours=hours)
        return await self._get_top_slow_endpoints_optimized(user_id, since, limit=limit)

    async def get_optimization_suggestions(
        self, user_id: Optional[int] = None, hours: int = 24
    ) -> List[OptimizationSuggestion]:
        """Return optimization hints derived from request patterns."""
        summary = await self.get_analytics_summary(user_id=user_id, hours=hours)
        return summary.optimization_suggestions

    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile from a list of values."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = (len(sorted_values) - 1) * (percentile / 100)
        lower = int(index)
        upper = min(lower + 1, len(sorted_values) - 1)
        weight = index - lower
        if lower == upper:
            return round(sorted_values[lower], 2)
        return round(
            sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight, 2
        )

    async def _build_latency_series_optimized(
        self,
        user_id: Optional[int] = None,
        since: Optional[datetime] = None,
        hours: int = 24,
    ) -> List[LatencyPoint]:
        """
        Build latency time series using SQL-based aggregation.
        Groups logs by time bucket and computes stats per bucket.
        """
        bucket_count = max(1, min(12, hours))
        bucket_minutes = max(5, int((hours * 60) / bucket_count))
        bucket_size = timedelta(minutes=bucket_minutes)

        if not since:
            since = datetime.utcnow() - timedelta(hours=hours)

        # Query all logs in range (minimal columns)
        query = select(
            APILog.created_at,
            APILog.response_time_ms,
            APILog.status_code,
        ).where(APILog.created_at >= since)
        
        if user_id is not None:
            query = query.where(APILog.user_id == user_id)

        result = await self.session.execute(query)
        logs = result.all()

        if not logs:
            return []

        first_timestamp = min(log[0] for log in logs)
        buckets: dict[str, dict[str, int | float]] = {}

        for created_at, response_time, status_code in logs:
            elapsed = created_at - first_timestamp
            bucket_index = int(elapsed.total_seconds() // bucket_size.total_seconds())
            bucket_start = first_timestamp + bucket_size * bucket_index
            bucket_key = bucket_start.isoformat(timespec="seconds")

            if bucket_key not in buckets:
                buckets[bucket_key] = {"count": 0, "errors": 0, "total_time": 0.0}

            buckets[bucket_key]["count"] += 1
            buckets[bucket_key]["total_time"] += response_time
            if status_code >= 400:
                buckets[bucket_key]["errors"] += 1

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

    async def _build_latency_distribution_optimized(
        self,
        user_id: Optional[int] = None,
        since: Optional[datetime] = None,
        hours: int = 24,
    ) -> List[LatencyDistributionPoint]:
        """
        Build latency distribution time series with percentiles.
        Groups by time bucket and computes p95/p99 per bucket.
        """
        bucket_count = max(1, min(12, hours))
        bucket_minutes = max(5, int((hours * 60) / bucket_count))
        bucket_size = timedelta(minutes=bucket_minutes)

        if not since:
            since = datetime.utcnow() - timedelta(hours=hours)

        # Fetch logs with response times
        query = select(
            APILog.created_at,
            APILog.response_time_ms,
            APILog.status_code,
        ).where(APILog.created_at >= since)
        
        if user_id is not None:
            query = query.where(APILog.user_id == user_id)

        result = await self.session.execute(query)
        logs = result.all()

        if not logs:
            return []

        first_timestamp = min(log[0] for log in logs)
        buckets: dict[str, dict] = {}

        for created_at, response_time, status_code in logs:
            elapsed = created_at - first_timestamp
            bucket_index = int(elapsed.total_seconds() // bucket_size.total_seconds())
            bucket_start = first_timestamp + bucket_size * bucket_index
            bucket_key = bucket_start.isoformat(timespec="seconds")

            if bucket_key not in buckets:
                buckets[bucket_key] = {
                    "count": 0,
                    "errors": 0,
                    "times": [],
                    "total_time": 0.0,
                }

            buckets[bucket_key]["count"] += 1
            buckets[bucket_key]["total_time"] += response_time
            buckets[bucket_key]["times"].append(response_time)
            if status_code >= 400:
                buckets[bucket_key]["errors"] += 1

        distribution: List[LatencyDistributionPoint] = []
        for timestamp, stats in sorted(buckets.items()):
            count = max(int(stats["count"]), 1)
            distribution.append(
                LatencyDistributionPoint(
                    timestamp=timestamp,
                    avg_response_time_ms=round(float(stats["total_time"]) / count, 2),
                    p95_response_time_ms=self._percentile(stats["times"], 95),
                    p99_response_time_ms=self._percentile(stats["times"], 99),
                    request_count=int(stats["count"]),
                    error_count=int(stats["errors"]),
                )
            )
        return distribution

    async def _build_benchmark_report_optimized(
        self,
        user_id: Optional[int] = None,
        since: Optional[datetime] = None,
    ) -> BenchmarkReport:
        """Build benchmark report using minimal data fetch."""
        if not since:
            since = datetime.utcnow() - timedelta(hours=24)

        # Fetch response times with created_at (minimal columns)
        query = select(
            APILog.created_at,
            APILog.response_time_ms,
        ).where(APILog.created_at >= since)
        
        if user_id is not None:
            query = query.where(APILog.user_id == user_id)

        query = query.order_by(APILog.created_at.asc())

        result = await self.session.execute(query)
        logs = result.all()

        if not logs:
            return BenchmarkReport(
                baseline_avg_response_time_ms=0.0,
                optimized_avg_response_time_ms=0.0,
                improvement_percent=0.0,
                sample_size=0,
                before_window=since.isoformat(timespec="seconds"),
                after_window=since.isoformat(timespec="seconds"),
            )

        # Split into baseline and optimized periods
        midpoint = max(1, len(logs) // 2)
        baseline_times = [float(row[1]) for row in logs[:midpoint]]
        optimized_times = [float(row[1]) for row in logs[midpoint:]] or baseline_times

        baseline_avg = sum(baseline_times) / len(baseline_times) if baseline_times else 0.0
        optimized_avg = sum(optimized_times) / len(optimized_times) if optimized_times else 0.0
        improvement = (
            ((baseline_avg - optimized_avg) / baseline_avg * 100) if baseline_avg > 0 else 0.0
        )

        return BenchmarkReport(
            baseline_avg_response_time_ms=round(baseline_avg, 2),
            optimized_avg_response_time_ms=round(optimized_avg, 2),
            improvement_percent=round(improvement, 2),
            sample_size=len(logs),
            before_window=f"{since.isoformat(timespec='seconds')} -> {logs[midpoint - 1][0].isoformat(timespec='seconds')}",
            after_window=f"{logs[midpoint][0].isoformat(timespec='seconds')} -> {logs[-1][0].isoformat(timespec='seconds')}",
        )

    def _build_suggestions(
        self,
        total_requests: int,
        total_errors: int,
        cache_hit_rate: float,
        avg_response_time_ms: float,
        slowest_response_time_ms: float,
        slow_endpoints: List[dict],
        slow_endpoint_ranking: Optional[List[dict]] = None,
    ) -> List[OptimizationSuggestion]:
        """Build optimization suggestions based on metrics."""
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

        if slow_endpoint_ranking:
            hottest_cache_issues = [
                endpoint
                for endpoint in slow_endpoint_ranking
                if endpoint["cache_hit_rate"] < 40 and endpoint["p95_time"] > 300
            ]
            if hottest_cache_issues:
                suggestions.append(
                    OptimizationSuggestion(
                        title="Cache slow responses",
                        severity="high",
                        endpoint=hottest_cache_issues[0]["endpoint"],
                        reason=(
                            f"{hottest_cache_issues[0]['endpoint']} has a p95 latency of "
                            f"{hottest_cache_issues[0]['p95_time']:.0f}ms and low cache hit rate."
                        ),
                        action="Cache repeated GET responses and apply a tighter caching policy for the slowest endpoints.",
                    )
                )

            repeated_expensive = [
                endpoint
                for endpoint in slow_endpoint_ranking
                if endpoint["count"] > 50 and endpoint["avg_time"] > 400
            ]
            if repeated_expensive:
                suggestions.append(
                    OptimizationSuggestion(
                        title="Reduce repeated expensive work",
                        severity="medium",
                        endpoint=repeated_expensive[0]["endpoint"],
                        reason=(
                            f"{repeated_expensive[0]['endpoint']} sees {repeated_expensive[0]['count']} requests "
                            f"with average latency {repeated_expensive[0]['avg_time']:.0f}ms."
                        ),
                        action="Use memoization, background jobs, or incremental caching for the hottest slow routes.",
                    )
                )

        error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0.0
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

    def _empty_analytics_summary(self) -> AnalyticsSummary:
        """Return an empty analytics summary."""
        return AnalyticsSummary(
            total_requests=0,
            total_errors=0,
            cache_hit_rate=0.0,
            avg_response_time_ms=0.0,
            slowest_endpoint=None,
            slowest_response_time_ms=None,
            top_endpoints=[],
            slow_endpoint_ranking=[],
            overall_p95_response_time_ms=0.0,
            overall_p99_response_time_ms=0.0,
            error_rate=0.0,
            request_rate_per_minute=0.0,
            cache_miss_rate=0.0,
            recent_requests=[],
            latency_series=[],
            latency_distribution=[],
            slow_endpoints=[],
            optimization_suggestions=[
                OptimizationSuggestion(
                    title="No data available",
                    severity="low",
                    reason="No requests recorded in the specified time period.",
                    action="Make some API requests and check back later.",
                )
            ],
            benchmark=None,
        )
