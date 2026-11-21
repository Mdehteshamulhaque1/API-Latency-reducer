"""
Analytics over the request log (``api_logs``).

Every number is computed with SQL aggregates over the rows in the window;
percentiles use the nearest-rank definition ceil(N * p / 100) through
window functions (supported by SQLite 3.25+, MySQL 8, PostgreSQL).
Time series are bucketed in Python from a minimal (timestamp, latency,
status) projection.
"""
import json
import logging
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from sqlalchemy import case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DIRECTION_INBOUND, DIRECTION_OUTBOUND, SELF_SERVICE
from app.models import APILog
from app.schemas.analytics import (
    AnalyticsSummary,
    BenchmarkReport,
    LatencyDistributionPoint,
    LatencyPoint,
    MonitoredService,
    OptimizationSuggestion,
    RecentRequest,
)
from app.schemas.ingest import IngestedRequest

logger = logging.getLogger(__name__)

BENCHMARK_REPORT_FILE = Path("logs") / "benchmark_reports" / "latest.json"


def _utcnow() -> datetime:
    """Timezone-aware UTC now.

    Must be aware: asyncpg interprets a naive datetime as *local* time when
    binding it to a ``timestamptz`` column or parameter, which would shift
    inserted rows and query windows by the server's UTC offset. SQLite
    stores the UTC wall-clock either way.
    """
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """Make a datetime aware (naive values are taken as UTC)."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _nearest_rank(values: List[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(len(ordered) * percentile / 100) - 1)], 2)


def _bucket_size(hours: int) -> timedelta:
    return timedelta(minutes=max(5, int(hours * 60 / max(1, min(12, hours)))))


class AnalyticsService:
    def __init__(self, session: AsyncSession, end_user: Optional[str] = None):
        self.session = session
        #: When set, every read covers only this end user's rows ("esone:7").
        self.end_user = end_user

    # ------------------------------------------------------------ writes

    async def log_request(self, **fields) -> APILog:
        """Insert one request row (called from the metrics background task)."""
        row = APILog(**fields)
        self.session.add(row)
        await self.session.commit()
        return row

    async def log_requests_batch(self, records: Sequence[IngestedRequest], user_id: Optional[int] = None) -> int:
        """Insert rows shipped by a monitored service (POST /ingest/requests).

        ``user_id`` is the service account that shipped the batch. It is kept
        so the service's LLM calls and guardrail events (recorded under that
        account) can be attributed to it; the rows themselves are analysed by
        every dashboard user through the ``service`` filter.
        """
        now = _utcnow()
        rows = []
        for record in records:
            occurred = _as_utc(record.occurred_at).astimezone(timezone.utc) if record.occurred_at else None
            rows.append(
                APILog(
                    user_id=user_id,
                    service=record.service,
                    direction=record.direction,
                    upstream_host=record.upstream_host,
                    end_user=record.end_user,
                    method=record.method,
                    endpoint=record.endpoint,
                    path=record.path or record.endpoint,
                    status_code=record.status_code,
                    response_time_ms=record.response_time_ms,
                    cache_hit=record.cache_hit,
                    client_ip=record.client_ip,
                    correlation_id=record.correlation_id,
                    request_size_bytes=record.request_size_bytes,
                    response_size_bytes=record.response_size_bytes,
                    query_params=record.query_params,
                    error_message=record.error_message,
                    created_at=occurred or now,
                    updated_at=occurred or now,
                )
            )
        self.session.add_all(rows)
        await self.session.commit()
        return len(rows)

    # ------------------------------------------------------------- reads

    def _filters(
        self,
        user_id: Optional[int],
        since: datetime,
        service: Optional[str] = None,
        direction: Optional[str] = None,
    ) -> list:
        """Row filters for a window.

        With ``service`` set, the rows of that application are analysed for
        everyone (they are shared telemetry); without it the caller's own
        requests are returned, as before.
        """
        filters = [APILog.created_at >= since]
        if self.end_user:
            filters.append(APILog.end_user == self.end_user)
        elif service:
            filters.append(APILog.service == service)
        elif user_id is not None:
            filters.append(APILog.user_id == user_id)
        if direction:
            filters.append(APILog.direction == direction)
        return filters

    async def service_account_id(self, service: str) -> Optional[int]:
        """The gateway account a monitored service ships its rows with (newest wins)."""
        if not service or service == SELF_SERVICE:
            return None
        return (
            await self.session.execute(
                select(APILog.user_id)
                .where(APILog.service == service, APILog.user_id.is_not(None))
                .order_by(desc(APILog.id))
                .limit(1)
            )
        ).scalar_one_or_none()

    async def get_services(self, hours: int = 24) -> List[MonitoredService]:
        """Every service with rows in the window, this one first."""
        since = _utcnow() - timedelta(hours=hours)
        rows = (
            await self.session.execute(
                select(
                    APILog.service,
                    func.count(APILog.id),
                    func.sum(case((APILog.direction == DIRECTION_INBOUND, 1), else_=0)),
                    func.sum(case((APILog.direction == DIRECTION_OUTBOUND, 1), else_=0)),
                    func.sum(case((APILog.status_code >= 400, 1), else_=0)),
                    func.avg(APILog.response_time_ms),
                    func.max(APILog.created_at),
                )
                .where(APILog.created_at >= since)
                .group_by(APILog.service)
            )
        ).all()
        services = []
        for name, total, inbound, outbound, errors, avg_ms, last_seen in rows:
            is_self = name == SELF_SERVICE
            services.append(
                MonitoredService(
                    service=name,
                    is_self=is_self,
                    requests=int(total or 0),
                    inbound=int(inbound or 0),
                    outbound=int(outbound or 0),
                    errors=int(errors or 0),
                    avg_response_time_ms=round(float(avg_ms or 0.0), 2),
                    last_seen=last_seen,
                    account_user_id=None if is_self else await self.service_account_id(name),
                )
            )
        return sorted(services, key=lambda item: (not item.is_self, item.service))

    async def get_analytics_summary(
        self,
        user_id: Optional[int] = None,
        hours: int = 24,
        service: Optional[str] = None,
        direction: Optional[str] = None,
    ) -> AnalyticsSummary:
        since = _utcnow() - timedelta(hours=hours)
        filters = self._filters(user_id, since, service, direction)

        totals = (
            await self.session.execute(
                select(
                    func.count(APILog.id),
                    func.sum(case((APILog.status_code >= 400, 1), else_=0)),
                    func.sum(case((APILog.cache_hit.is_(True), 1), else_=0)),
                    func.avg(APILog.response_time_ms),
                    func.max(APILog.response_time_ms),
                    func.sum(case((APILog.status_code == 429, 1), else_=0)),
                ).where(*filters)
            )
        ).one()
        total = int(totals[0] or 0)
        if total == 0:
            return self._empty_summary()
        errors = int(totals[1] or 0)
        hits = int(totals[2] or 0)
        avg_ms = float(totals[3] or 0.0)
        max_ms = float(totals[4] or 0.0)
        rate_limited = int(totals[5] or 0)

        top_endpoints = await self._top_endpoints(filters, limit=10)
        ranking = await self.get_top_slow_endpoints(
            user_id=user_id, hours=hours, limit=10, since=since, service=service, direction=direction
        )
        slowest = await self._slowest_endpoint(filters)
        p50, p95, p99 = await self._overall_percentiles(filters, (50, 95, 99))
        series, distribution = await self._time_series(filters, since, hours)

        slow_endpoints = [e for e in top_endpoints if e["avg_time"] >= 300 or e["errors"] > 0] or top_endpoints[:3]
        cache_hit_rate = hits / total * 100

        return AnalyticsSummary(
            total_requests=total,
            total_errors=errors,
            rate_limited_requests=rate_limited,
            cache_hit_rate=cache_hit_rate,
            cache_miss_rate=(total - hits) / total * 100,
            avg_response_time_ms=avg_ms,
            slowest_endpoint=slowest,
            slowest_response_time_ms=max_ms,
            top_endpoints=top_endpoints,
            slow_endpoint_ranking=ranking,
            overall_p50_response_time_ms=p50,
            overall_p95_response_time_ms=p95,
            overall_p99_response_time_ms=p99,
            error_rate=errors / total * 100,
            request_rate_per_minute=round(total / max(hours * 60, 1), 2),
            recent_requests=await self._recent_requests(filters, limit=10),
            latency_series=series,
            latency_distribution=distribution,
            slow_endpoints=slow_endpoints,
            optimization_suggestions=self._suggestions(total, errors, cache_hit_rate, avg_ms, max_ms, slow_endpoints, ranking),
            benchmark=await self.get_endpoint_benchmark(
                user_id=user_id, hours=hours, since=since, service=service, direction=direction
            ),
        )

    async def _top_endpoints(self, filters: list, limit: int) -> List[dict]:
        rows = (
            await self.session.execute(
                select(
                    APILog.endpoint,
                    func.count(APILog.id),
                    func.avg(APILog.response_time_ms),
                    func.sum(case((APILog.status_code >= 400, 1), else_=0)),
                    func.sum(case((APILog.cache_hit.is_(True), 1), else_=0)),
                )
                .where(*filters)
                .group_by(APILog.endpoint)
                .order_by(desc(func.count(APILog.id)))
                .limit(limit)
            )
        ).all()
        result = []
        for endpoint, count, avg_ms, errors, hits in rows:
            count = int(count or 0)
            result.append(
                {
                    "endpoint": endpoint,
                    "count": count,
                    "avg_time": round(float(avg_ms or 0.0), 2),
                    "errors": int(errors or 0),
                    "cache_hit_rate": round(int(hits or 0) / count * 100, 2) if count else 0.0,
                }
            )
        return result

    async def get_top_slow_endpoints(
        self,
        user_id: Optional[int] = None,
        hours: int = 24,
        limit: int = 10,
        since: Optional[datetime] = None,
        service: Optional[str] = None,
        direction: Optional[str] = None,
    ) -> List[dict]:
        """Endpoints ranked by p95 latency, with their p99, errors, and cache ratio."""
        since = since or _utcnow() - timedelta(hours=hours)
        filters = self._filters(user_id, since, service, direction)
        candidates = await self._top_endpoints(filters, limit=limit * 2)
        percentiles = await self._endpoint_percentiles(filters, [c["endpoint"] for c in candidates], (95, 99))
        ranking = [
            {
                **item,
                "p95_time": percentiles[item["endpoint"]][95],
                "p99_time": percentiles[item["endpoint"]][99],
                "error_rate": round(item["errors"] / item["count"] * 100, 2) if item["count"] else 0.0,
            }
            for item in candidates
        ]
        return sorted(ranking, key=lambda r: r["p95_time"], reverse=True)[:limit]

    async def _overall_percentiles(self, filters: list, percentiles: Iterable[int]) -> List[float]:
        wanted = list(percentiles)
        ranked = (
            select(
                APILog.response_time_ms,
                func.row_number().over(order_by=APILog.response_time_ms).label("rn"),
                func.count().over().label("total"),
            )
            .where(*filters)
            .subquery()
        )
        conditions = [ranked.c.rn == func.ceil(ranked.c.total * p / 100.0) for p in wanted]
        rows = (
            await self.session.execute(
                select(ranked.c.response_time_ms, ranked.c.rn, ranked.c.total).where(or_(*conditions))
            )
        ).all()
        results = {p: 0.0 for p in wanted}
        for latency, rank, total in rows:
            for p in wanted:
                if int(rank) == math.ceil(int(total) * p / 100.0):
                    results[p] = round(float(latency), 2)
        return [results[p] for p in wanted]

    async def _endpoint_percentiles(
        self, filters: list, endpoints: List[str], percentiles: Iterable[int]
    ) -> Dict[str, Dict[int, float]]:
        """Several percentiles for several endpoints in one windowed query."""
        wanted = list(percentiles)
        results = {endpoint: {p: 0.0 for p in wanted} for endpoint in endpoints}
        if not endpoints:
            return results
        ranked = (
            select(
                APILog.endpoint,
                APILog.response_time_ms,
                func.row_number().over(partition_by=APILog.endpoint, order_by=APILog.response_time_ms).label("rn"),
                func.count().over(partition_by=APILog.endpoint).label("total"),
            )
            .where(*filters, APILog.endpoint.in_(endpoints))
            .subquery()
        )
        conditions = [ranked.c.rn == func.ceil(ranked.c.total * p / 100.0) for p in wanted]
        rows = (
            await self.session.execute(
                select(ranked.c.endpoint, ranked.c.response_time_ms, ranked.c.rn, ranked.c.total).where(or_(*conditions))
            )
        ).all()
        for endpoint, latency, rank, total in rows:
            for p in wanted:
                if int(rank) == math.ceil(int(total) * p / 100.0):
                    results[endpoint][p] = round(float(latency), 2)
        return results

    async def _slowest_endpoint(self, filters: list) -> Optional[str]:
        row = (
            await self.session.execute(
                select(APILog.endpoint).where(*filters).order_by(desc(APILog.response_time_ms)).limit(1)
            )
        ).scalar_one_or_none()
        return row

    async def _recent_requests(self, filters: list, limit: int) -> List[RecentRequest]:
        rows = (
            await self.session.execute(
                select(APILog).where(*filters).order_by(desc(APILog.created_at)).limit(limit)
            )
        ).scalars().all()
        return [RecentRequest.model_validate(row, from_attributes=True) for row in rows]

    async def _time_series(
        self, filters: list, since: datetime, hours: int
    ) -> tuple[List[LatencyPoint], List[LatencyDistributionPoint]]:
        """Average, p95, p99, count, and errors per time bucket."""
        rows = (
            await self.session.execute(
                select(APILog.created_at, APILog.response_time_ms, APILog.status_code).where(*filters)
            )
        ).all()
        if not rows:
            return [], []
        size = _bucket_size(hours)
        first = min(row[0] for row in rows)
        buckets: Dict[str, dict] = {}
        for created_at, latency, status in rows:
            index = int((created_at - first).total_seconds() // size.total_seconds())
            key = (first + size * index).isoformat(timespec="seconds")
            bucket = buckets.setdefault(key, {"times": [], "errors": 0})
            bucket["times"].append(float(latency))
            bucket["errors"] += 1 if status >= 400 else 0

        series, distribution = [], []
        for key, bucket in sorted(buckets.items()):
            times = bucket["times"]
            avg = round(sum(times) / len(times), 2)
            series.append(LatencyPoint(timestamp=key, avg_response_time_ms=avg, request_count=len(times), error_count=bucket["errors"]))
            distribution.append(
                LatencyDistributionPoint(
                    timestamp=key,
                    avg_response_time_ms=avg,
                    p95_response_time_ms=_nearest_rank(times, 95),
                    p99_response_time_ms=_nearest_rank(times, 99),
                    request_count=len(times),
                    error_count=bucket["errors"],
                )
            )
        return series, distribution

    async def get_endpoint_logs(
        self,
        endpoint_pattern: str,
        user_id: Optional[int] = None,
        limit: int = 100,
        hours: Optional[int] = None,
        service: Optional[str] = None,
        direction: Optional[str] = None,
        method: Optional[str] = None,
    ) -> List[APILog]:
        """Raw rows whose endpoint contains ``endpoint_pattern`` (and match ``method``), newest first."""
        query = select(APILog).where(APILog.endpoint.like(f"%{endpoint_pattern}%"))
        if method:
            query = query.where(APILog.method == method.upper())
        if self.end_user:
            query = query.where(APILog.end_user == self.end_user)
        elif service:
            query = query.where(APILog.service == service)
        elif user_id is not None:
            query = query.where(APILog.user_id == user_id)
        if direction:
            query = query.where(APILog.direction == direction)
        if hours:
            query = query.where(APILog.created_at >= _utcnow() - timedelta(hours=hours))
        rows = await self.session.execute(query.order_by(desc(APILog.created_at)).limit(limit))
        return list(rows.scalars().all())

    async def get_endpoint_benchmark(
        self,
        user_id: Optional[int] = None,
        hours: int = 24,
        since: Optional[datetime] = None,
        service: Optional[str] = None,
        direction: Optional[str] = None,
    ) -> BenchmarkReport:
        """Average latency of the first half of the window versus the second half."""
        since = since or _utcnow() - timedelta(hours=hours)
        rows = (
            await self.session.execute(
                select(APILog.created_at, APILog.response_time_ms)
                .where(*self._filters(user_id, since, service, direction))
                .order_by(APILog.created_at.asc())
            )
        ).all()
        stamp = since.isoformat(timespec="seconds")
        if not rows:
            return BenchmarkReport(
                baseline_avg_response_time_ms=0.0, optimized_avg_response_time_ms=0.0,
                improvement_percent=0.0, sample_size=0, before_window=stamp, after_window=stamp,
            )
        midpoint = max(1, len(rows) // 2)
        before = [float(r[1]) for r in rows[:midpoint]]
        after = [float(r[1]) for r in rows[midpoint:]] or before
        baseline = sum(before) / len(before)
        optimized = sum(after) / len(after)
        after_start = rows[min(midpoint, len(rows) - 1)][0]
        return BenchmarkReport(
            baseline_avg_response_time_ms=round(baseline, 2),
            optimized_avg_response_time_ms=round(optimized, 2),
            improvement_percent=round((baseline - optimized) / baseline * 100, 2) if baseline > 0 else 0.0,
            sample_size=len(rows),
            before_window=f"{stamp} -> {rows[midpoint - 1][0].isoformat(timespec='seconds')}",
            after_window=f"{after_start.isoformat(timespec='seconds')} -> {rows[-1][0].isoformat(timespec='seconds')}",
        )

    async def get_optimization_suggestions(
        self, user_id: Optional[int] = None, hours: int = 24, service: Optional[str] = None
    ) -> List[OptimizationSuggestion]:
        return (await self.get_analytics_summary(user_id=user_id, hours=hours, service=service)).optimization_suggestions

    # ---------------------------------------------------------- heuristics

    @staticmethod
    def _suggestions(
        total: int, errors: int, cache_hit_rate: float, avg_ms: float, max_ms: float,
        slow_endpoints: List[dict], ranking: List[dict],
    ) -> List[OptimizationSuggestion]:
        """Fixed, explainable rules; the assistant turns these into narrative."""
        out: List[OptimizationSuggestion] = []
        if cache_hit_rate < 65:
            out.append(OptimizationSuggestion(
                title="Increase cache coverage", severity="high",
                reason=f"Cache hit rate is only {cache_hit_rate:.1f}% across {total} requests.",
                action="Add cache rules for high-traffic GET endpoints.",
            ))
        if avg_ms > 250:
            out.append(OptimizationSuggestion(
                title="Reduce average latency", severity="medium",
                reason=f"Average response time is {avg_ms:.0f}ms.",
                action="Move expensive work off the request path and cache repeated reads.",
            ))
        if max_ms > 750 and slow_endpoints:
            out.append(OptimizationSuggestion(
                title="Inspect slow endpoints", severity="high", endpoint=slow_endpoints[0]["endpoint"],
                reason=f"Slowest observed latency is {max_ms:.0f}ms.",
                action="Check query plans and indexes, then consider a cache rule.",
            ))
        hot = [e for e in ranking if e["cache_hit_rate"] < 40 and e["p95_time"] > 300]
        if hot:
            out.append(OptimizationSuggestion(
                title="Cache slow responses", severity="high", endpoint=hot[0]["endpoint"],
                reason=f"{hot[0]['endpoint']} has a p95 of {hot[0]['p95_time']:.0f}ms and a low cache hit rate.",
                action="Cache repeated GET responses for this endpoint.",
            ))
        busy = [e for e in ranking if e["count"] > 50 and e["avg_time"] > 400]
        if busy:
            out.append(OptimizationSuggestion(
                title="Reduce repeated expensive work", severity="medium", endpoint=busy[0]["endpoint"],
                reason=f"{busy[0]['endpoint']} sees {busy[0]['count']} requests at {busy[0]['avg_time']:.0f}ms average.",
                action="Memoise or cache the hottest slow route.",
            ))
        if total and errors / total * 100 > 2:
            out.append(OptimizationSuggestion(
                title="Harden error handling", severity="medium",
                reason=f"Error rate is {errors / total * 100:.2f}%.",
                action="Investigate the failing endpoints with the troubleshooting assistant.",
            ))
        if not out:
            out.append(OptimizationSuggestion(
                title="System is healthy", severity="low",
                reason="No major bottlenecks were detected in the sampled window.",
                action="Keep monitoring latency, cache hit rate, and slow endpoint drift.",
            ))
        return out[:4]

    @staticmethod
    def _empty_summary() -> AnalyticsSummary:
        return AnalyticsSummary(
            total_requests=0, total_errors=0, cache_hit_rate=0.0, avg_response_time_ms=0.0,
            slowest_endpoint=None, slowest_response_time_ms=None, top_endpoints=[], error_rate=0.0,
            optimization_suggestions=[
                OptimizationSuggestion(
                    title="No data available", severity="low",
                    reason="No requests recorded in the specified time period.",
                    action="Make some API requests and check back later.",
                )
            ],
        )


def persist_benchmark_report(report: dict) -> None:
    """Write the latest benchmark report to disk (background task)."""
    BENCHMARK_REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    BENCHMARK_REPORT_FILE.write_text(
        json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), "report": report}, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("Benchmark report persisted to %s", BENCHMARK_REPORT_FILE)
