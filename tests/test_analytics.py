"""
Analytics calculations against known, seeded request logs.

Rows are inserted directly so every expected number can be computed by hand:
percentiles use the nearest-rank definition ceil(N * p / 100).
"""
import uuid
from datetime import timedelta

from app.database.db import async_session_maker
from app.models import APILog
from app.services.analytics import AnalyticsService, _utcnow

ADMIN_ID = 1


async def _seed_logs():
    """10 requests on /fast (10..100 ms), 4 on /slow (400..700 ms, one 429, one 500)."""
    now = _utcnow()
    rows = []
    for index in range(10):
        rows.append(
            APILog(
                user_id=ADMIN_ID,
                method="GET",
                endpoint="/fast",
                path="/fast",
                status_code=200,
                response_time_ms=float((index + 1) * 10),
                cache_hit=index % 2 == 0,
                client_ip="127.0.0.1",
                correlation_id=uuid.uuid4().hex[:36],
                created_at=now - timedelta(minutes=index),
                updated_at=now,
            )
        )
    for index, status in enumerate((200, 200, 429, 500)):
        rows.append(
            APILog(
                user_id=ADMIN_ID,
                method="POST",
                endpoint="/slow",
                path="/slow",
                status_code=status,
                response_time_ms=float(400 + index * 100),
                cache_hit=False,
                client_ip="127.0.0.1",
                correlation_id=uuid.uuid4().hex[:36],
                created_at=now - timedelta(minutes=index),
                updated_at=now,
            )
        )
    async with async_session_maker() as session:
        from sqlalchemy import delete

        await session.execute(delete(APILog).where(APILog.user_id == ADMIN_ID))
        session.add_all(rows)
        await session.commit()


async def test_summary_counts_percentiles_and_rate_limits():
    await _seed_logs()
    async with async_session_maker() as session:
        summary = await AnalyticsService(session).get_analytics_summary(user_id=ADMIN_ID, hours=24)

    assert summary.total_requests == 14
    assert summary.total_errors == 2  # 429 + 500
    assert summary.rate_limited_requests == 1
    assert round(summary.error_rate, 2) == round(2 / 14 * 100, 2)
    assert round(summary.cache_hit_rate, 2) == round(5 / 14 * 100, 2)

    # Sorted latencies: 10..100 (10 values) then 400,500,600,700 -> N=14
    # p50 -> rank ceil(7) = 7th -> 70 ; p95 -> rank 14 -> 700 ; p99 -> 700
    assert summary.overall_p50_response_time_ms == 70.0
    assert summary.overall_p95_response_time_ms == 700.0
    assert summary.overall_p99_response_time_ms == 700.0
    assert summary.slowest_endpoint == "/slow"
    assert summary.slowest_response_time_ms == 700.0


async def test_per_endpoint_percentiles_match_nearest_rank():
    await _seed_logs()
    async with async_session_maker() as session:
        summary = await AnalyticsService(session).get_analytics_summary(user_id=ADMIN_ID, hours=24)

    ranking = {item.endpoint: item for item in summary.slow_endpoint_ranking}
    assert list(ranking) == ["/slow", "/fast"]  # ordered by p95 descending

    fast = ranking["/fast"]
    assert fast.count == 10
    assert fast.p95_time == 100.0  # rank ceil(9.5)=10 -> 100
    assert fast.p99_time == 100.0
    assert fast.avg_time == 55.0
    assert fast.cache_hit_rate == 50.0
    assert fast.errors == 0

    slow = ranking["/slow"]
    assert slow.count == 4
    assert slow.p95_time == 700.0  # rank ceil(3.8)=4 -> 700
    assert slow.p99_time == 700.0
    assert slow.errors == 2
    assert slow.error_rate == 50.0


async def test_summary_endpoint_exposes_new_fields(client, admin_headers):
    await _seed_logs()
    res = await client.get("/api/v1/analytics/summary?hours=24", headers=admin_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["rate_limited_requests"] == 1
    assert body["overall_p50_response_time_ms"] == 70.0


async def test_empty_window_returns_zeroes():
    async with async_session_maker() as session:
        summary = await AnalyticsService(session).get_analytics_summary(user_id=999_999, hours=1)
    assert summary.total_requests == 0
    assert summary.rate_limited_requests == 0
    assert summary.overall_p50_response_time_ms == 0.0
    assert summary.slow_endpoint_ranking == []
