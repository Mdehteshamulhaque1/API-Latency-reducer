#!/usr/bin/env python3
"""
Demo data seeder — fills the database with users, cache rules, and a
realistic 24-hour history of API traffic so the analytics dashboards
light up immediately.

Run with:
    python seed_demo.py          # idempotent: skips existing users/rules, adds traffic
    python seed_demo.py --reset  # wipes existing logs/analytics first, then re-seeds
"""
import argparse
import asyncio
import math
import os
import random
import sys
import uuid
from datetime import datetime, timezone, timedelta

import bcrypt

# Add app to path (works on Windows and POSIX)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Ensure emoji output works on Windows consoles (cp1252 by default)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from app.database.base import Base
from app.database.db import engine, async_session_maker
from app.models import User, CacheRule, APILog, Analytics
from app.core.constants import UserRole
from app.config import settings

# ---------------------------------------------------------------------------
# Demo configuration
# ---------------------------------------------------------------------------
DEMO_PASSWORD = "demo-pass-123"  # used for operator/viewer demo accounts

# (endpoint, weight, base_latency_ms, spread, cache_hit_rate, error_rate)
ENDPOINTS = [
    ("/api/v1/analytics/summary",       0.22, 142, 60,   0.86, 0.012),
    ("/api/v1/rules",                   0.16,  96, 40,   0.91, 0.005),
    ("/api/v1/auth/login",              0.12, 180, 90,   0.00, 0.020),
    ("/api/v1/auth/refresh",            0.12,  74, 30,   0.00, 0.008),
    ("/api/v1/cache/status",            0.10, 120, 55,   0.75, 0.003),
    ("/api/v1/health",                  0.09,  12,  8,   0.00, 0.000),
    ("/api/v1/users",                   0.08,  95, 45,   0.60, 0.010),
    ("/api/v1/analytics/slow-endpoints",0.06, 402, 180,  0.44, 0.014),
    ("/api/v1/analytics/benchmark",     0.05, 310, 150,  0.58, 0.010),
]

CLIENT_IPS = [
    "10.0.0.12", "10.0.0.27", "10.0.2.101", "10.0.3.44",
    "10.0.1.200", "10.0.5.8", "172.16.4.21", "192.168.1.66",
]

ERROR_CODES = [404, 429, 500, 502]

TOTAL_REQUESTS = 22_000
HOURS = 24


def _hash_password(password: str) -> str:
    """Hash a password with bcrypt (passlib is incompatible with bcrypt 5.x)."""
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def _utcnow() -> datetime:
    """Naive UTC now — matches the values read back from the database."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _pick_endpoint(rng: random.Random):
    """Weighted random endpoint selection."""
    total = sum(ep[1] for ep in ENDPOINTS)
    roll = rng.uniform(0, total)
    upto = 0.0
    for ep in ENDPOINTS:
        upto += ep[1]
        if roll <= upto:
            return ep
    return ENDPOINTS[0]


async def seed_users(session) -> dict:
    """Create demo users (admin, operator, viewer) if missing."""
    from sqlalchemy.future import select

    users = {}

    # Admin from .env (matching migrate_db.py behaviour)
    admin_email = settings.admin_email or "admin@example.com"
    admin_password = settings.admin_password or "change-me-in-production"
    admin = (await session.execute(
        select(User).where(User.email == admin_email)
    )).scalar_one_or_none()
    if admin is None:
        admin = User(
            username="admin",
            email=admin_email,
            hashed_password=_hash_password(admin_password),
            role=UserRole.ADMIN,
            is_active=True,
            is_superuser=True,
            api_quota=100000,
        )
        session.add(admin)
        await session.flush()
        print(f"✅ Created admin user: {admin_email}")
    else:
        print(f"✅ Admin user already exists: {admin_email}")
    users["admin"] = admin

    demo_accounts = [
        ("operator", "operator@example.com", UserRole.OPERATOR),
        ("viewer", "viewer@example.com", UserRole.VIEWER),
    ]
    for username, email, role in demo_accounts:
        user = (await session.execute(
            select(User).where(User.email == email)
        )).scalar_one_or_none()
        if user is None:
            user = User(
                username=username,
                email=email,
                hashed_password=_hash_password(DEMO_PASSWORD),
                role=role,
                is_active=True,
                is_superuser=False,
                api_quota=50000,
            )
            session.add(user)
            await session.flush()
            print(f"✅ Created demo user: {username} ({role}) / {DEMO_PASSWORD}")
        else:
            print(f"✅ Demo user already exists: {username}")
        users[username] = user

    return users


async def seed_cache_rules(session):
    """Create demo cache rules if none exist yet."""
    from sqlalchemy.future import select

    existing = (await session.execute(select(CacheRule.id).limit(1))).scalar_one_or_none()
    if existing is not None:
        print("✅ Cache rules already present — skipping")
        return

    rules = [
        CacheRule(endpoint_pattern="/api/v1/analytics", ttl=300, enabled=True,
                  cache_by_user=False, cache_by_query_params=True, cache_by_headers=False,
                  max_cache_size=1000, priority=10,
                  description="Hot analytics routes, short TTL"),
        CacheRule(endpoint_pattern="/api/v1/rules", ttl=600, enabled=True,
                  cache_by_user=False, cache_by_query_params=True, cache_by_headers=False,
                  max_cache_size=500, priority=8,
                  description="Rule listings are mostly static"),
        CacheRule(endpoint_pattern="/api/v1/health", ttl=30, enabled=True,
                  cache_by_user=False, cache_by_query_params=False, cache_by_headers=False,
                  max_cache_size=100, priority=20,
                  description="Fresh health signal"),
        CacheRule(endpoint_pattern="/api/v1/users", ttl=60, enabled=False,
                  cache_by_user=True, cache_by_query_params=True, cache_by_headers=False,
                  max_cache_size=1000, priority=5,
                  description="User-specific payloads, per-user cache"),
        CacheRule(endpoint_pattern="/api/v1/cache/status", ttl=120, enabled=True,
                  cache_by_user=False, cache_by_query_params=False, cache_by_headers=False,
                  max_cache_size=300, priority=12,
                  description="Operational status, short TTL"),
        CacheRule(endpoint_pattern="/api/v1/demo/latency", ttl=60, enabled=True,
                  cache_by_user=False, cache_by_query_params=False, cache_by_headers=False,
                  max_cache_size=1000, priority=15,
                  description="Load-test demo endpoint, short TTL"),
    ]
    session.add_all(rules)
    print(f"✅ Created {len(rules)} demo cache rules")


def _hour_volume(hour_of_day: int) -> float:
    """Traffic multiplier by hour — trough at 4am, peaks at 10am/2pm/8pm."""
    return 1.0 + 0.6 * math.cos((hour_of_day - 14) / 24 * 2 * math.pi)


async def generate_traffic(session, users: dict):
    """Generate a realistic 24h history of APILog + hourly Analytics rows."""

    now = _utcnow()
    start = now - timedelta(hours=HOURS)

    # Latency "before optimization" factor: earlier hours are slower, later
    # hours faster, so the benchmark report shows a believable improvement.
    def improvement_factor(elapsed_ratio: float) -> float:
        return 1.35 - 0.5 * elapsed_ratio  # 1.35 -> 0.85 across the window

    user_assignments = [
        (users["admin"], 0.80),
        (users["operator"], 0.10),
        (users["viewer"], 0.05),
        (None, 0.05),
    ]

    rng = random.Random(42)  # deterministic seed -> reproducible demo data

    logs: list[APILog] = []
    hourly: dict[tuple, dict] = {}

    for i in range(TOTAL_REQUESTS):
        elapsed_ratio = i / TOTAL_REQUESTS
        ts = start + timedelta(seconds=(i / TOTAL_REQUESTS) * HOURS * 3600)

        # Jitter the timestamp within the bucket for a more organic spread
        ts = ts + timedelta(seconds=rng.uniform(-45, 45))
        if ts > now:
            ts = now

        endpoint, _w, base_latency, spread, cache_rate, error_rate = _pick_endpoint(rng)
        hour_of_day = ts.hour

        # Skip ~40% of health checks outside business hours for realism
        if endpoint == "/api/v1/health" and hour_of_day < 8 and rng.random() < 0.4:
            continue

        # Latency: base * time-based improvement * noise
        latency = (
            base_latency
            * improvement_factor(elapsed_ratio)
            * rng.uniform(0.7, 1.4)
        )
        latency = round(max(2.0, latency), 2)

        # Status code
        is_error = rng.random() < error_rate
        if is_error:
            status_code = rng.choice(ERROR_CODES)
            if status_code == 429 and endpoint in ("/api/v1/auth/login", "/api/v1/auth/refresh"):
                pass
        else:
            status_code = 200

        cache_hit = (not is_error) and endpoint not in ("/api/v1/auth/login", "/api/v1/auth/refresh") \
            and rng.random() < cache_rate
        cache_key = f"apc:GET:{endpoint}:{uuid.uuid4().hex[:8]}" if cache_hit else None

        # Assign a user
        user_id = None
        roll = rng.random()
        acc = 0.0
        for user, weight in user_assignments:
            acc += weight
            if roll <= acc:
                user_id = user.id if user is not None else None
                break

        method = "GET"
        if endpoint in ("/api/v1/auth/login", "/api/v1/auth/refresh"):
            method = "POST"

        query_params = "hours=24" if endpoint.startswith("/api/v1/analytics") else None
        path = f"http://localhost:8000{endpoint}"
        if query_params:
            path += f"?{query_params}"

        logs.append(APILog(
            user_id=user_id,
            method=method,
            endpoint=endpoint,
            path=path,
            status_code=status_code,
            response_time_ms=latency,
            cache_hit=cache_hit,
            cache_key=cache_key,
            client_ip=rng.choice(CLIENT_IPS),
            correlation_id=str(uuid.uuid4()),
            request_size_bytes=rng.randint(200, 3000),
            response_size_bytes=rng.randint(500, 12000),
            query_params=query_params,
            error_message="Simulated demo error" if is_error else None,
            created_at=ts,
        ))

        # Hourly analytics aggregation (same period format as AnalyticsService)
        hour_key = ts.replace(minute=0, second=0, microsecond=0)
        period_key = f"hourly:{hour_key.isoformat(timespec='minutes')}"
        agg_key = (period_key, user_id)
        if agg_key not in hourly:
            hourly[agg_key] = {
                "period": period_key,
                "user_id": user_id,
                "total": 0,
                "errors": 0,
                "hits": 0,
                "misses": 0,
                "total_time": 0.0,
                "min": float("inf"),
                "max": 0.0,
                "bytes_in": 0,
                "bytes_out": 0,
            }
        agg = hourly[agg_key]
        agg["total"] += 1
        agg["errors"] += 1 if status_code >= 400 else 0
        if cache_hit:
            agg["hits"] += 1
        else:
            agg["misses"] += 1
        agg["total_time"] += latency
        agg["min"] = min(agg["min"], latency)
        agg["max"] = max(agg["max"], latency)
        agg["bytes_in"] += rng.randint(200, 3000)
        agg["bytes_out"] += rng.randint(500, 12000)

    # Bulk insert logs
    session.add_all(logs)
    await session.flush()
    print(f"✅ Inserted {len(logs)} API log entries")

    # Insert hourly aggregates for a fully consistent dataset
    analytics_rows = []
    for agg in hourly.values():
        total = max(agg["total"], 1)
        analytics_rows.append(Analytics(
            user_id=agg["user_id"],
            period=agg["period"],
            total_requests=agg["total"],
            total_errors=agg["errors"],
            cache_hits=agg["hits"],
            cache_misses=agg["misses"],
            avg_response_time_ms=round(agg["total_time"] / total, 2),
            min_response_time_ms=round(agg["min"], 2),
            max_response_time_ms=round(agg["max"], 2),
            total_bytes_sent=agg["bytes_out"],
            total_bytes_received=agg["bytes_in"],
        ))
    session.add_all(analytics_rows)
    print(f"✅ Inserted {len(analytics_rows)} hourly analytics aggregates")


async def verify(session):
    """Print a quick summary of the seeded data."""
    from sqlalchemy import func
    from sqlalchemy.future import select

    total_logs = (await session.execute(select(func.count(APILog.id)))).scalar()
    total_users = (await session.execute(select(func.count(User.id)))).scalar()
    total_rules = (await session.execute(select(func.count(CacheRule.id)))).scalar()
    print("\n📊 Seeded data summary")
    print(f"   users:       {total_users}")
    print(f"   cache rules: {total_rules}")
    print(f"   api logs:    {total_logs}")


async def seed_demo(reset: bool):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tables ready")

    async with async_session_maker() as session:
        if reset:
            from sqlalchemy import text
            for table in ("analytics", "api_logs"):
                await session.execute(text(f"DELETE FROM {table}"))
            print(f"🧹 Wiped existing logs/analytics ({reset})")
            await session.commit()

        users = await seed_users(session)
        await seed_cache_rules(session)
        await generate_traffic(session, users)
        await session.commit()

        await verify(session)

    print("\n✅ Demo data seeded successfully!")
    print(f"   Demo logins: admin (from .env), operator/viewer (password: {DEMO_PASSWORD})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo data for API Optimizer")
    parser.add_argument("--reset", action="store_true",
                        help="Wipe existing logs/analytics before seeding")
    args = parser.parse_args()

    asyncio.run(seed_demo(reset=args.reset))
