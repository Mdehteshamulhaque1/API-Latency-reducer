"""
Answer history: what was asked, what was answered, by whom, how, and at what cost.

Two data layers:

* The shared answer cache (Redis, ``app.ai.answers.semantic_cache``) holds
  one reusable answer per question with the model that generated it and its
  original cost.
* ``answer_logs`` holds one row per request per caller: the gateway account
  (``user_id``), the end user a monitored service passed (``end_user``),
  the question, the answer that caller received, the cache status (exact
  hit, semantic hit, miss, bypassed) and cache key, every latency component
  (cache lookup, embedding, crawl, model), tokens split into prompt,
  completion and embedding, the LLM and embedding cost of THIS request, the
  estimated cost a hit saved, and errors. A shared cache hit still writes
  its own row, so User A and User B both have their records while the
  cached answer is stored once.

``record`` runs as a background task after the HTTP response and also
pushes the row onto the Redis list ``answers:recent`` (newest first,
capped, expiring after ``ANSWERS_RECENT_TTL``). ``record_error`` writes a
row for blocked or failed requests.

Reads (``recent``, ``stats``, ``top``, ``costs``, ``users``, ``cache_overview``)
take the caller scope decided by the route plus optional ``end_user`` and
``cache_status`` filters, so ownership is enforced in the query, never in
the frontend. Redis fails open: when it is unavailable every read falls
back to SQL.
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import String, case, cast, desc, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.answers.semantic_cache import SemanticCache, question_key
from app.config import settings
from app.database.db import async_session_maker
from app.models import AnswerLog
from app.schemas.answers import (
    AnswerLogItem,
    AnswerLogPage,
    AnswerSource,
    AnswerStats,
    CacheOverview,
    CostAnalytics,
    SourceCount,
    TopQuestion,
    TopQuestionsPage,
    UserQueryStats,
    UserQueryStatsPage,
)
from app.services.answers import CACHE_BYPASSED, CACHE_EXACT_HIT, CACHE_MISS, CACHE_SEMANTIC_HIT, AnswerResult
from app.utils.redis_client import RedisClient, redis_client

logger = logging.getLogger(__name__)

RECENT_KEY = "answers:recent"
# Longest answer text kept in the Redis list entries (the database keeps all of it).
RECENT_ANSWER_CHARS = 4000
# Rows sampled for the latency percentiles.
PERCENTILE_SAMPLE = 5000

STATUS_OK = "ok"
STATUS_ERROR = "error"
STATUS_BLOCKED = "blocked"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    """SQLite hands back naive timestamps; treat them as UTC."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _hash(question: str) -> str:
    return question_key(question).rsplit(":", 1)[-1]


def _parse_sources(raw: object) -> List[AnswerSource]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            raw = []
    items: List[AnswerSource] = []
    for entry in raw if isinstance(raw, list) else []:
        if isinstance(entry, dict) and isinstance(entry.get("title"), str) and isinstance(entry.get("url"), str):
            source = entry.get("source")
            items.append(AnswerSource(title=entry["title"], url=entry["url"], source=source if isinstance(source, str) else None))
    return items


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((pct / 100) * (len(ordered) - 1))))
    return round(ordered[index], 2)


def _f(value) -> float:
    return float(value or 0.0)


def _i(value) -> int:
    return int(value or 0)


def _item_from_row(row: AnswerLog) -> AnswerLogItem:
    return AnswerLogItem(
        id=row.id,
        created_at=_aware(row.created_at),
        user_id=row.user_id,
        end_user=row.end_user,
        correlation_id=row.correlation_id,
        question=row.question,
        answer=row.answer,
        status=row.status or STATUS_OK,
        error_code=row.error_code,
        answered_by=row.answered_by,
        found=bool(row.found),
        cache_status=row.cache_status or CACHE_MISS,
        match_method=row.match_method,
        similarity=row.similarity,
        compose_method=row.compose_method,
        primary_source=row.primary_source,
        sources=_parse_sources(row.sources),
        cache_key=row.cache_key,
        latency_ms=_f(row.latency_ms),
        cache_lookup_ms=_f(row.cache_lookup_ms),
        embedding_ms=_f(row.embedding_ms),
        crawl_ms=row.crawl_ms,
        llm_ms=_f(row.llm_ms),
        prompt_tokens=_i(row.prompt_tokens),
        completion_tokens=_i(row.completion_tokens),
        embedding_tokens=_i(row.embedding_tokens),
        total_tokens=_i(row.total_tokens),
        llm_cost_usd=_f(row.llm_cost_usd),
        embedding_cost_usd=_f(row.embedding_cost_usd),
        total_cost_usd=_f(row.total_cost_usd),
        estimated_cost_usd=_f(row.estimated_cost_usd),
        saved_cost_usd=_f(row.saved_cost_usd),
        billable_tokens=_i(row.billable_tokens),
        cost_inr=_f(row.cost_inr),
        served_model=row.served_model,
        waited_for_generation=bool(row.waited_for_generation),
    )


def _item_from_redis(raw: object) -> Optional[AnswerLogItem]:
    if not isinstance(raw, dict):
        return None
    try:
        return AnswerLogItem(
            id=int(raw["id"]),
            created_at=datetime.fromisoformat(raw["created_at"]),
            user_id=raw.get("user_id"),
            end_user=raw.get("end_user"),
            correlation_id=raw.get("correlation_id"),
            question=str(raw["question"]),
            answer=str(raw["answer"]),
            status=str(raw.get("status") or STATUS_OK),
            error_code=raw.get("error_code"),
            answered_by=str(raw["answered_by"]),
            found=bool(raw.get("found", True)),
            cache_status=str(raw.get("cache_status") or CACHE_MISS),
            match_method=raw.get("match_method"),
            similarity=raw.get("similarity"),
            compose_method=raw.get("compose_method"),
            primary_source=raw.get("primary_source"),
            sources=_parse_sources(raw.get("sources")),
            cache_key=raw.get("cache_key"),
            latency_ms=_f(raw.get("latency_ms")),
            cache_lookup_ms=_f(raw.get("cache_lookup_ms")),
            embedding_ms=_f(raw.get("embedding_ms")),
            crawl_ms=raw.get("crawl_ms"),
            llm_ms=_f(raw.get("llm_ms")),
            prompt_tokens=_i(raw.get("prompt_tokens")),
            completion_tokens=_i(raw.get("completion_tokens")),
            embedding_tokens=_i(raw.get("embedding_tokens")),
            total_tokens=_i(raw.get("total_tokens")),
            llm_cost_usd=_f(raw.get("llm_cost_usd")),
            embedding_cost_usd=_f(raw.get("embedding_cost_usd")),
            total_cost_usd=_f(raw.get("total_cost_usd")),
            estimated_cost_usd=_f(raw.get("estimated_cost_usd")),
            saved_cost_usd=_f(raw.get("saved_cost_usd")),
            billable_tokens=_i(raw.get("billable_tokens")),
            cost_inr=_f(raw.get("cost_inr")),
            served_model=raw.get("served_model"),
            waited_for_generation=bool(raw.get("waited_for_generation", False)),
        )
    except (KeyError, TypeError, ValueError):
        return None


class AnswerHistoryService:
    def __init__(self, session: AsyncSession, redis: Optional[RedisClient] = None):
        self.session = session
        self._redis = redis or redis_client

    # ----------------------------------------------------------------- write

    async def _persist(self, row: AnswerLog, sources: List[dict]) -> AnswerLog:
        self.session.add(row)
        await self.session.commit()
        entry = {
            "id": row.id,
            "created_at": _aware(row.created_at).isoformat(),
            "user_id": row.user_id,
            "end_user": row.end_user,
            "correlation_id": row.correlation_id,
            "question": row.question,
            "answer": row.answer[:RECENT_ANSWER_CHARS],
            "status": row.status,
            "error_code": row.error_code,
            "answered_by": row.answered_by,
            "found": row.found,
            "cache_status": row.cache_status,
            "match_method": row.match_method,
            "similarity": row.similarity,
            "compose_method": row.compose_method,
            "primary_source": row.primary_source,
            "sources": sources,
            "cache_key": row.cache_key,
            "latency_ms": row.latency_ms,
            "cache_lookup_ms": row.cache_lookup_ms,
            "embedding_ms": row.embedding_ms,
            "crawl_ms": row.crawl_ms,
            "llm_ms": row.llm_ms,
            "prompt_tokens": row.prompt_tokens,
            "completion_tokens": row.completion_tokens,
            "embedding_tokens": row.embedding_tokens,
            "total_tokens": row.total_tokens,
            "llm_cost_usd": row.llm_cost_usd,
            "embedding_cost_usd": row.embedding_cost_usd,
            "total_cost_usd": row.total_cost_usd,
            "estimated_cost_usd": row.estimated_cost_usd,
            "saved_cost_usd": row.saved_cost_usd,
            "billable_tokens": row.billable_tokens,
            "cost_inr": row.cost_inr,
            "served_model": row.served_model,
            "waited_for_generation": row.waited_for_generation,
        }
        await self._redis.push_capped(
            RECENT_KEY, entry, max_len=settings.answers_recent_max, ttl=settings.answers_recent_ttl
        )
        return row

    async def record(
        self,
        result: AnswerResult,
        *,
        user_id: Optional[int],
        end_user: Optional[str],
        correlation_id: Optional[str],
    ) -> AnswerLog:
        now = _utcnow()
        sources = [
            {"title": s.get("title"), "url": s.get("url"), "source": s.get("source")}
            for s in result.sources
            if isinstance(s, dict)
        ]
        row = AnswerLog(
            user_id=user_id,
            end_user=end_user,
            correlation_id=correlation_id,
            question=result.question[:2000],
            question_hash=_hash(result.question),
            answer=result.answer,
            status=STATUS_OK,
            answered_by=result.answered_by,
            found=result.found,
            cache_status=result.cache_status,
            match_method=result.match_method,
            similarity=result.similarity,
            compose_method=result.compose_method,
            primary_source=result.primary_source,
            sources=json.dumps(sources),
            source_count=len(sources),
            cache_key=result.cache_key,
            latency_ms=float(result.latency_ms),
            cache_lookup_ms=float(result.cache_lookup_ms),
            embedding_ms=float(result.embedding_ms),
            crawl_ms=result.crawl_ms,
            llm_ms=float(result.llm_ms),
            prompt_tokens=int(result.prompt_tokens),
            completion_tokens=int(result.completion_tokens),
            embedding_tokens=int(result.embedding_tokens),
            total_tokens=int(result.total_tokens),
            llm_cost_usd=float(result.llm_cost_usd),
            embedding_cost_usd=float(result.embedding_cost_usd),
            total_cost_usd=float(result.total_cost_usd),
            estimated_cost_usd=float(result.total_cost_usd),
            saved_cost_usd=float(result.saved_cost_usd),
            billable_tokens=int(result.billable_tokens),
            cost_inr=float(result.cost_inr),
            served_model=result.served_model,
            waited_for_generation=bool(result.waited_for_generation),
            created_at=now,
            updated_at=now,
        )
        return await self._persist(row, sources)

    async def record_error(
        self,
        question: str,
        *,
        user_id: Optional[int],
        end_user: Optional[str],
        correlation_id: Optional[str],
        status: str,
        error_code: str,
        latency_ms: float,
    ) -> AnswerLog:
        """A blocked or failed request: no answer, but the caller's record still exists."""
        now = _utcnow()
        row = AnswerLog(
            user_id=user_id,
            end_user=end_user,
            correlation_id=correlation_id,
            question=" ".join(question.split())[:2000],
            question_hash=_hash(question),
            answer="",
            status=status,
            error_code=error_code[:60],
            answered_by="none",
            found=False,
            cache_status=CACHE_MISS,
            sources="[]",
            source_count=0,
            latency_ms=float(latency_ms),
            created_at=now,
            updated_at=now,
        )
        return await self._persist(row, [])

    # ------------------------------------------------------------------ reads

    def _filters(
        self, since: datetime, user_id: Optional[int], end_user: Optional[str], cache_status: Optional[str] = None
    ) -> list:
        filters = [AnswerLog.created_at >= since]
        if user_id is not None:
            filters.append(AnswerLog.user_id == user_id)
        if end_user:
            filters.append(AnswerLog.end_user == end_user)
        if cache_status:
            filters.append(AnswerLog.cache_status == cache_status)
        return filters

    async def recent(
        self,
        *,
        hours: int,
        user_id: Optional[int],
        scope: str,
        limit: int,
        offset: int = 0,
        end_user: Optional[str] = None,
        cache_status: Optional[str] = None,
    ) -> AnswerLogPage:
        since = _utcnow() - timedelta(hours=hours)
        if hours * 3600 <= settings.answers_recent_ttl and offset == 0 and not cache_status:
            items = await self._recent_from_redis(since=since, user_id=user_id, end_user=end_user, limit=limit)
            if items is not None:
                return AnswerLogPage(
                    hours=hours, scope=scope, end_user=end_user, cache_status=cache_status, served_from="redis",
                    offset=0, limit=limit, total=len(items), items=items,
                )

        filters = self._filters(since, user_id, end_user, cache_status)
        total = int((await self.session.execute(select(func.count(AnswerLog.id)).where(*filters))).scalar() or 0)
        query = (
            select(AnswerLog)
            .where(*filters)
            .order_by(desc(AnswerLog.created_at), desc(AnswerLog.id))
            .offset(offset)
            .limit(limit)
        )
        rows = (await self.session.execute(query)).scalars().all()
        return AnswerLogPage(
            hours=hours, scope=scope, end_user=end_user, cache_status=cache_status, served_from="database",
            offset=offset, limit=limit, total=total, items=[_item_from_row(r) for r in rows],
        )

    async def _recent_from_redis(
        self, *, since: datetime, user_id: Optional[int], end_user: Optional[str], limit: int
    ) -> Optional[List[AnswerLogItem]]:
        raw = await self._redis.list_range(RECENT_KEY, 0, settings.answers_recent_max - 1)
        if not raw:
            return None  # empty or unavailable: let the database answer
        items: List[AnswerLogItem] = []
        for entry in raw:
            item = _item_from_redis(entry)
            if item is None or item.created_at < since:
                continue
            if user_id is not None and item.user_id != user_id:
                continue
            if end_user and item.end_user != end_user:
                continue
            items.append(item)
            if len(items) >= limit:
                break
        return items

    async def _totals(self, filters: list):
        ok = AnswerLog.status == STATUS_OK
        hit = AnswerLog.cache_status.in_([CACHE_EXACT_HIT, CACHE_SEMANTIC_HIT])
        return (
            await self.session.execute(
                select(
                    func.count(AnswerLog.id),                                                        # 0 rows
                    func.count(func.distinct(AnswerLog.question_hash)),                             # 1 unique
                    func.count(func.distinct(AnswerLog.end_user)),                                  # 2 end users
                    func.sum(case((AnswerLog.cache_status == CACHE_EXACT_HIT, 1), else_=0)),         # 3 exact
                    func.sum(case((AnswerLog.cache_status == CACHE_SEMANTIC_HIT, 1), else_=0)),      # 4 semantic
                    func.sum(case((ok & (AnswerLog.cache_status == CACHE_MISS), 1), else_=0)),       # 5 miss
                    func.sum(case((ok & (AnswerLog.cache_status == CACHE_BYPASSED), 1), else_=0)),   # 6 bypassed
                    func.sum(case((ok & AnswerLog.found.is_(False), 1), else_=0)),                   # 7 not found
                    func.sum(case((AnswerLog.status == STATUS_ERROR, 1), else_=0)),                  # 8 errors
                    func.sum(case((AnswerLog.status == STATUS_BLOCKED, 1), else_=0)),                # 9 blocked
                    func.avg(case((ok, AnswerLog.latency_ms))),                                      # 10 avg latency
                    func.avg(case((hit, AnswerLog.latency_ms))),                                     # 11 avg hit latency
                    func.avg(case((ok & hit.is_(False), AnswerLog.latency_ms))),                     # 12 avg miss latency
                    func.avg(case((ok, AnswerLog.cache_lookup_ms))),                                 # 13 avg lookup
                    func.sum(AnswerLog.prompt_tokens),                                               # 14
                    func.sum(AnswerLog.completion_tokens),                                           # 15
                    func.sum(AnswerLog.embedding_tokens),                                            # 16
                    func.sum(AnswerLog.total_tokens),                                                # 17
                    func.sum(AnswerLog.llm_cost_usd),                                                # 18
                    func.sum(AnswerLog.embedding_cost_usd),                                          # 19
                    func.sum(AnswerLog.total_cost_usd),                                              # 20
                    func.sum(AnswerLog.saved_cost_usd),                                              # 21
                    func.sum(case((AnswerLog.llm_ms > 0, 1), else_=0)),                              # 22 llm calls
                    func.sum(case((hit, AnswerLog.total_cost_usd), else_=0.0)),                      # 23 hit cost
                    func.sum(case((ok & hit.is_(False), AnswerLog.total_cost_usd), else_=0.0)),      # 24 miss cost
                ).where(*filters)
            )
        ).one()

    async def _grouped(self, filters: list, column) -> List[SourceCount]:
        rows = (
            await self.session.execute(
                select(column, func.count(AnswerLog.id))
                .where(*filters, column.is_not(None))
                .group_by(column)
                .order_by(desc(func.count(AnswerLog.id)))
            )
        ).all()
        return [SourceCount(name=str(name), count=int(count)) for name, count in rows]

    async def stats(
        self, *, hours: int, user_id: Optional[int], scope: str, end_user: Optional[str] = None
    ) -> AnswerStats:
        since = _utcnow() - timedelta(hours=hours)
        filters = self._filters(since, user_id, end_user)
        t = await self._totals(filters)
        questions = _i(t[0])
        exact, semantic = _i(t[3]), _i(t[4])
        cache_hits = exact + semantic
        errors, blocked = _i(t[8]), _i(t[9])
        answered = questions - errors - blocked

        latencies = [
            float(v)
            for v in (
                await self.session.execute(
                    select(AnswerLog.latency_ms)
                    .where(*filters, AnswerLog.status == STATUS_OK)
                    .order_by(desc(AnswerLog.id))
                    .limit(PERCENTILE_SAMPLE)
                )
            ).scalars()
        ]
        return AnswerStats(
            hours=hours,
            scope=scope,
            end_user=end_user,
            questions=questions,
            unique_questions=_i(t[1]),
            end_users=_i(t[2]),
            cache_hits=cache_hits,
            exact_hits=exact,
            semantic_hits=semantic,
            crawled=max(0, answered - cache_hits),
            not_found=_i(t[7]),
            errors=errors,
            blocked=blocked,
            bypassed=_i(t[6]),
            cache_hit_rate=round(cache_hits / answered * 100, 2) if answered else 0.0,
            avg_latency_ms=round(_f(t[10]), 2),
            avg_latency_cached_ms=round(_f(t[11]), 2),
            avg_latency_crawled_ms=round(_f(t[12]), 2),
            avg_cache_lookup_ms=round(_f(t[13]), 2),
            p50_latency_ms=_percentile(latencies, 50),
            p95_latency_ms=_percentile(latencies, 95),
            p99_latency_ms=_percentile(latencies, 99),
            total_tokens=_i(t[17]),
            prompt_tokens=_i(t[14]),
            completion_tokens=_i(t[15]),
            embedding_tokens=_i(t[16]),
            llm_cost_usd=round(_f(t[18]), 8),
            embedding_cost_usd=round(_f(t[19]), 8),
            total_cost_usd=round(_f(t[20]), 8),
            estimated_cost_usd=round(_f(t[20]), 8),
            saved_cost_usd=round(_f(t[21]), 8),
            cache_ttl_seconds=settings.answers_cache_ttl,
            recent_window_seconds=settings.answers_recent_ttl,
            by_source=await self._grouped(filters, AnswerLog.primary_source),
            by_match=await self._grouped(filters, AnswerLog.match_method),
            by_model=await self._grouped(filters, AnswerLog.served_model),
        )

    async def costs(
        self, *, hours: int, user_id: Optional[int], scope: str, end_user: Optional[str] = None
    ) -> CostAnalytics:
        since = _utcnow() - timedelta(hours=hours)
        filters = self._filters(since, user_id, end_user)
        t = await self._totals(filters)
        hits = _i(t[3]) + _i(t[4])
        misses = _i(t[5]) + _i(t[6])
        return CostAnalytics(
            hours=hours,
            scope=scope,
            end_user=end_user,
            currency=settings.pricing_currency,
            pricing_effective_date=settings.pricing_effective_date,
            llm_cost_usd=round(_f(t[18]), 8),
            embedding_cost_usd=round(_f(t[19]), 8),
            total_cost_usd=round(_f(t[20]), 8),
            saved_cost_usd=round(_f(t[21]), 8),
            prompt_tokens=_i(t[14]),
            completion_tokens=_i(t[15]),
            embedding_tokens=_i(t[16]),
            total_tokens=_i(t[17]) + _i(t[16]),
            llm_calls_made=_i(t[22]),
            llm_calls_avoided=hits,
            requests=_i(t[0]),
            hits=hits,
            misses=misses,
            avg_cost_per_hit_usd=round(_f(t[23]) / hits, 8) if hits else 0.0,
            avg_cost_per_miss_usd=round(_f(t[24]) / misses, 8) if misses else 0.0,
            avg_latency_hit_ms=round(_f(t[11]), 2),
            avg_latency_miss_ms=round(_f(t[12]), 2),
            by_model=await self._grouped(filters, AnswerLog.served_model),
        )

    async def cache_overview(
        self, *, hours: int, user_id: Optional[int], scope: str, end_user: Optional[str] = None
    ) -> CacheOverview:
        since = _utcnow() - timedelta(hours=hours)
        t = await self._totals(self._filters(since, user_id, end_user))
        cache = SemanticCache(self._redis)
        available = await cache.available()
        live = await cache.stats() if available else None
        exact, semantic, misses, bypassed = _i(t[3]), _i(t[4]), _i(t[5]), _i(t[6])
        looked_up = exact + semantic + misses
        return CacheOverview(
            hours=hours,
            scope=scope,
            redis_available=available,
            active_entries=live.active_entries if live else 0,
            stored_total=live.stored_total if live else 0,
            expired_estimate=live.expired_estimate if live else 0,
            bytes_used=live.bytes_used if live else 0,
            entries_scanned=live.scanned if live else 0,
            total_entry_hits=live.total_hits if live else 0,
            oldest_entry_at=datetime.fromtimestamp(live.oldest_created_at, tz=timezone.utc) if live and live.oldest_created_at else None,
            ttl_seconds=settings.answers_cache_ttl,
            volatile_ttl_seconds=settings.answers_volatile_ttl,
            similarity_threshold=settings.answers_similarity_threshold,
            exact_hits=exact,
            semantic_hits=semantic,
            misses=misses,
            bypassed=bypassed,
            cache_hit_rate=round((exact + semantic) / looked_up * 100, 2) if looked_up else 0.0,
            avg_cache_lookup_ms=round(_f(t[13]), 2),
            avg_latency_hit_ms=round(_f(t[11]), 2),
            avg_latency_miss_ms=round(_f(t[12]), 2),
        )

    async def users(
        self,
        *,
        hours: int,
        user_id: Optional[int],
        scope: str,
        limit: int,
        offset: int = 0,
        end_user: Optional[str] = None,
    ) -> UserQueryStatsPage:
        """Per-caller totals: grouped by end user when present, else by gateway account."""
        since = _utcnow() - timedelta(hours=hours)
        filters = self._filters(since, user_id, end_user)
        # "||" on both SQLite and PostgreSQL: SQLAlchemy renders String + String as concatenation.
        caller = func.coalesce(AnswerLog.end_user, literal("account:") + cast(AnswerLog.user_id, String))
        ok = AnswerLog.status == STATUS_OK
        base = select(caller.label("caller")).where(*filters).group_by(caller)
        total = int((await self.session.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0)
        rows = (
            await self.session.execute(
                select(
                    caller.label("caller"),
                    func.max(AnswerLog.user_id),
                    func.max(AnswerLog.end_user),
                    func.count(AnswerLog.id),
                    func.sum(case((AnswerLog.cache_status == CACHE_EXACT_HIT, 1), else_=0)),
                    func.sum(case((AnswerLog.cache_status == CACHE_SEMANTIC_HIT, 1), else_=0)),
                    func.sum(case((ok & (AnswerLog.cache_status == CACHE_MISS), 1), else_=0)),
                    func.sum(case((ok & (AnswerLog.cache_status == CACHE_BYPASSED), 1), else_=0)),
                    func.sum(case((AnswerLog.status != STATUS_OK, 1), else_=0)),
                    func.sum(case((AnswerLog.llm_ms > 0, 1), else_=0)),
                    func.sum(AnswerLog.total_tokens),
                    func.sum(AnswerLog.embedding_tokens),
                    func.sum(AnswerLog.total_cost_usd),
                    func.sum(AnswerLog.saved_cost_usd),
                    func.avg(case((ok, AnswerLog.latency_ms))),
                    func.max(AnswerLog.created_at),
                )
                .where(*filters)
                .group_by(caller)
                .order_by(desc(func.count(AnswerLog.id)))
                .offset(offset)
                .limit(limit)
            )
        ).all()
        items = [
            UserQueryStats(
                user=str(r[0]),
                user_id=r[1],
                end_user=r[2],
                queries=_i(r[3]),
                exact_hits=_i(r[4]),
                semantic_hits=_i(r[5]),
                misses=_i(r[6]),
                bypassed=_i(r[7]),
                errors=_i(r[8]),
                llm_calls=_i(r[9]),
                total_tokens=_i(r[10]),
                embedding_tokens=_i(r[11]),
                total_cost_usd=round(_f(r[12]), 8),
                saved_cost_usd=round(_f(r[13]), 8),
                avg_latency_ms=round(_f(r[14]), 2),
                last_seen=_aware(r[15]) if isinstance(r[15], datetime) else _utcnow(),
            )
            for r in rows
        ]
        return UserQueryStatsPage(hours=hours, scope=scope, offset=offset, limit=limit, total=total, items=items)

    async def top(
        self, *, hours: int, user_id: Optional[int], scope: str, limit: int, end_user: Optional[str] = None
    ) -> TopQuestionsPage:
        since = _utcnow() - timedelta(hours=hours)
        filters = self._filters(since, user_id, end_user) + [AnswerLog.status == STATUS_OK]

        asked = func.count(AnswerLog.id)
        grouped = (
            await self.session.execute(
                select(
                    AnswerLog.question_hash,
                    asked,
                    func.sum(case((AnswerLog.answered_by == "cache", 1), else_=0)),
                    func.avg(AnswerLog.latency_ms),
                    func.max(AnswerLog.created_at),
                    func.max(AnswerLog.id),
                )
                .where(*filters)
                .group_by(AnswerLog.question_hash)
                .order_by(desc(asked), desc(func.max(AnswerLog.created_at)))
                .limit(limit)
            )
        ).all()
        if not grouped:
            return TopQuestionsPage(hours=hours, scope=scope, end_user=end_user, items=[])

        latest_ids = [int(row[5]) for row in grouped]
        latest_rows = (await self.session.execute(select(AnswerLog).where(AnswerLog.id.in_(latest_ids)))).scalars().all()
        latest = {row.id: row for row in latest_rows}

        items: List[TopQuestion] = []
        for question_hash, count, hits, avg_latency, last_asked, last_id in grouped:
            row = latest.get(int(last_id))
            if row is None:
                continue
            items.append(
                TopQuestion(
                    question=row.question,
                    question_hash=question_hash,
                    asked=_i(count),
                    cache_hits=_i(hits),
                    avg_latency_ms=round(_f(avg_latency), 2),
                    last_asked=_aware(last_asked) if isinstance(last_asked, datetime) else _aware(row.created_at),
                    last_answer=row.answer,
                )
            )
        return TopQuestionsPage(hours=hours, scope=scope, end_user=end_user, items=items)


# ---------------------------------------------------------------------------
# Background-task entry points used by the answers route
# ---------------------------------------------------------------------------

async def record_answer(
    result: AnswerResult, *, user_id: Optional[int], end_user: Optional[str], correlation_id: Optional[str]
) -> None:
    """Persist one answered question; a failure only produces a log line."""
    try:
        async with async_session_maker() as session:
            await AnswerHistoryService(session).record(
                result, user_id=user_id, end_user=end_user, correlation_id=correlation_id
            )
    except Exception as exc:  # noqa: BLE001 - never let bookkeeping break the request
        logger.warning("Failed to record answer history: %s", type(exc).__name__)


async def record_answer_error(
    question: str,
    *,
    user_id: Optional[int],
    end_user: Optional[str],
    correlation_id: Optional[str],
    status: str,
    error_code: str,
    latency_ms: float,
) -> None:
    """Persist a blocked or failed question; a failure only produces a log line."""
    try:
        async with async_session_maker() as session:
            await AnswerHistoryService(session).record_error(
                question,
                user_id=user_id,
                end_user=end_user,
                correlation_id=correlation_id,
                status=status,
                error_code=error_code,
                latency_ms=latency_ms,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to record answer error: %s", type(exc).__name__)
