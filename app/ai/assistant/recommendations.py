"""
Cache optimisation recommendations.

Two layers, kept separate on purpose:
1. ``analyse`` derives structured recommendations from measured traffic with
   plain, explainable rules (request volume, method mix, latency, hit rate,
   error rate, existing rules). This part never calls a model.
2. ``explain`` asks the model to narrate those recommendations in a short
   paragraph. It is optional, advisory, and cannot change anything: the
   platform never modifies a cache rule on its own.
"""
import logging
from dataclasses import asdict, dataclass, field
from datetime import timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import get_chat_service
from app.ai.guardrails.output import validate_answer
from app.config import settings
from app.core.exceptions import ExternalServiceError
from app.models import APILog, CacheRule
from app.schemas.chat import ChatMessage, ChatRequest
from app.services.analytics import _utcnow

logger = logging.getLogger(__name__)

MIN_REQUESTS = 20
NEVER_CACHE_PREFIXES = ("/api/v1/auth", "/api/v1/chat", "/v1/chat", "/api/v1/cache", "/api/v1/rules")


@dataclass
class Recommendation:
    endpoint: str
    kind: str  # "cache" | "tune" | "do_not_cache" | "keep"
    title: str
    reason: str
    suggested_ttl_seconds: Optional[Tuple[int, int]] = None
    evidence: Dict = field(default_factory=dict)
    advisory: bool = True


@dataclass
class RecommendationReport:
    hours: int
    analysed_endpoints: int
    recommendations: List[Recommendation]
    explanation: Optional[str] = None
    llm_available: bool = False
    note: str = (
        "Recommendations are advisory. Suggested TTL ranges assume the data changes "
        "slowly; verify with the owner of the endpoint before creating a rule."
    )


def _rule_for(endpoint: str, rules: List[CacheRule]) -> Optional[CacheRule]:
    for rule in sorted(rules, key=lambda r: r.priority, reverse=True):
        pattern = rule.endpoint_pattern
        if any(ch in pattern for ch in "*?["):
            import fnmatch

            if fnmatch.fnmatchcase(endpoint, pattern):
                return rule
        elif pattern in endpoint:
            return rule
    return None


def _suggest_ttl(requests: int, avg_ms: float) -> Tuple[int, int]:
    """Heuristic: the hotter and slower the endpoint, the more a short TTL already pays off."""
    if requests >= 500 or avg_ms >= 500:
        return (60, 300)
    if requests >= 100 or avg_ms >= 200:
        return (300, 900)
    return (600, 3600)


async def analyse(
    session: AsyncSession, *, user_id: Optional[int], hours: int, service: Optional[str] = None
) -> RecommendationReport:
    since = _utcnow() - timedelta(hours=hours)
    filters = [APILog.created_at >= since]
    if service:
        filters.append(APILog.service == service)
    elif user_id is not None:
        filters.append(APILog.user_id == user_id)

    rows = (
        await session.execute(
            select(
                APILog.endpoint,
                func.count(APILog.id),
                func.sum(case((APILog.method == "GET", 1), else_=0)),
                func.avg(APILog.response_time_ms),
                func.sum(case((APILog.cache_hit.is_(True), 1), else_=0)),
                func.sum(case((APILog.status_code >= 400, 1), else_=0)),
            )
            .where(*filters)
            .group_by(APILog.endpoint)
            .order_by(func.count(APILog.id).desc())
            .limit(30)
        )
    ).all()
    rules = (await session.execute(select(CacheRule))).scalars().all()

    recommendations: List[Recommendation] = []
    for endpoint, count, gets, avg_ms, hits, errors in rows:
        count = int(count or 0)
        gets = int(gets or 0)
        avg_ms = float(avg_ms or 0.0)
        hits = int(hits or 0)
        errors = int(errors or 0)
        get_share = gets / count if count else 0.0
        hit_rate = hits / count * 100 if count else 0.0
        error_rate = errors / count * 100 if count else 0.0
        evidence = {
            "requests": count, "get_share_percent": round(get_share * 100, 1),
            "avg_latency_ms": round(avg_ms, 1), "cache_hit_rate_percent": round(hit_rate, 1),
            "error_rate_percent": round(error_rate, 1),
        }
        rule = _rule_for(endpoint, rules)

        if endpoint.startswith(NEVER_CACHE_PREFIXES):
            if rule is not None and rule.enabled:
                recommendations.append(Recommendation(
                    endpoint, "do_not_cache", "Remove the cache rule",
                    "Authentication, cache-management, and LLM routes must never be served from the response cache.",
                    evidence=evidence,
                ))
            continue

        if count < MIN_REQUESTS:
            continue

        if get_share < 0.8:
            if rule is not None and rule.enabled:
                recommendations.append(Recommendation(
                    endpoint, "do_not_cache", "Reconsider caching a write-heavy route",
                    f"Only {get_share * 100:.0f}% of requests are GETs; responses to writes are never cached, "
                    "so the rule mostly adds lookups.",
                    evidence=evidence,
                ))
            continue

        if error_rate > 10:
            recommendations.append(Recommendation(
                endpoint, "do_not_cache", "Fix errors before caching",
                f"{error_rate:.0f}% of requests fail; only 200 responses are cached, so a rule would hide the problem "
                "behind the few successful responses.",
                evidence=evidence,
            ))
            continue

        if rule is None:
            if avg_ms >= 100 or count >= 100:
                ttl = _suggest_ttl(count, avg_ms)
                recommendations.append(Recommendation(
                    endpoint, "cache", "Cache candidate",
                    f"{count} GET requests with {avg_ms:.0f} ms average latency and no cache rule. "
                    "Repeated reads could be served from Redis.",
                    suggested_ttl_seconds=ttl, evidence=evidence,
                ))
            continue

        if not rule.enabled:
            recommendations.append(Recommendation(
                endpoint, "tune", "Rule exists but is disabled",
                f"A rule for '{rule.endpoint_pattern}' is paused while the route receives {count} requests.",
                evidence={**evidence, "rule": rule.endpoint_pattern},
            ))
        elif hit_rate < 20:
            recommendations.append(Recommendation(
                endpoint, "tune", "Low hit rate for an enabled rule",
                f"Hit rate is {hit_rate:.0f}% with TTL {rule.ttl}s. Hypothesis: the TTL is shorter than the "
                "time between repeated reads, or keying by query/user splits the cache too finely.",
                suggested_ttl_seconds=(max(rule.ttl * 2, 60), max(rule.ttl * 4, 300)),
                evidence={**evidence, "rule": rule.endpoint_pattern, "ttl_seconds": rule.ttl,
                          "keyed_by_query": rule.cache_by_query_params, "keyed_by_user": rule.cache_by_user},
            ))
        else:
            recommendations.append(Recommendation(
                endpoint, "keep", "Cache rule is working",
                f"Hit rate {hit_rate:.0f}% at TTL {rule.ttl}s.",
                evidence={**evidence, "rule": rule.endpoint_pattern, "ttl_seconds": rule.ttl},
            ))

    return RecommendationReport(hours=hours, analysed_endpoints=len(rows), recommendations=recommendations)


EXPLAIN_PROMPT = """You are helping a backend developer read cache recommendations produced by fixed rules.
Summarise the recommendations below in at most 120 words, in plain language, in priority order.
Only restate what the recommendations say; do not add endpoints or numbers that are not present.
Finish with one sentence reminding that nothing changes until a human creates or edits a rule.
"""


async def explain(report: RecommendationReport, *, user_id: Optional[int], correlation_id: Optional[str]) -> RecommendationReport:
    """Attach an advisory narrative; silently skip when no model is available."""
    if not report.recommendations:
        return report
    import json

    payload = json.dumps([asdict(r) for r in report.recommendations], default=str)
    request = ChatRequest(
        messages=[
            ChatMessage(role="system", content=EXPLAIN_PROMPT),
            ChatMessage(role="user", content=f"Recommendations:\n{payload}"),
        ],
        temperature=0.0,
        max_tokens=min(settings.assistant_max_tokens, 400),
    )
    try:
        response = await get_chat_service().create_chat_completion(
            request, user_id=user_id, correlation_id=correlation_id
        )
        report.explanation = validate_answer(response.content)
        report.llm_available = True
    except (ExternalServiceError, ValueError) as exc:
        logger.info("Recommendation narrative skipped: %s", exc)
    return report
