"""
Real queries vs everything else.

The request counters on the dashboard count every HTTP call: sign-ins,
history loads, health checks and the calls a service makes on a user's
behalf. This module sorts request rows into categories so the dashboard can
show the "real" queries (questions users asked) apart from the supporting
traffic, and adds what those questions cost from ``answer_logs``.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.constants import DIRECTION_OUTBOUND
from app.models import AnswerLog, APILog
from app.schemas.analytics import QueryBreakdown, QueryCategory, QueryEndpoint, QuerySearchTotals
from app.services.analytics import AnalyticsService

GROUP_QUERY = "query"
GROUP_SUPPORTING = "supporting"
GROUP_OUTBOUND = "outbound"

#: key -> (label, group, what it is). Order is the display order.
CATEGORIES: dict[str, tuple[str, str, str]] = {
    "search": ("Search questions", GROUP_QUERY, "Questions users asked in search"),
    "chatbot": ("Chatbot messages", GROUP_QUERY, "Messages sent to the project chatbot"),
    "auth": ("Sign-in and tokens", GROUP_SUPPORTING, "Login, sign-up, logout and token refresh"),
    "account": ("History and account", GROUP_SUPPORTING, "Search history, usage and profile loads"),
    "health": ("Page loads and health checks", GROUP_SUPPORTING, "Home page hits, uptime and health probes"),
    "other": ("Other requests", GROUP_SUPPORTING, "Anything not listed above"),
    "ai_provider": ("AI model calls", GROUP_OUTBOUND, "Calls to the AI provider (Gemini)"),
    "gateway_calls": ("Calls to API Optimizer", GROUP_OUTBOUND, "Sign-in and answer requests to this gateway"),
    "outbound_other": ("Other outbound calls", GROUP_OUTBOUND, "Other calls the service made"),
}

_PROXY_PREFIX = re.compile(r"^/proxy/[a-z0-9-]+(?=/)")
_HEALTH_PATHS = {"/", "/health", "/healthz", "/api/v1/health", "/api/v1/ping"}
_ACCOUNT_PATHS = {"/api/v1/chat/history", "/api/v1/chat/stats"}
_AI_HOST_MARKERS = ("generativelanguage.googleapis.com", "api.openai.com", "/chat/completions", "/embeddings")
ENDPOINTS_PER_CATEGORY = 5


def classify(direction: str, method: str, endpoint: str) -> str:
    """Category key for one request row."""
    method = (method or "").upper()
    if direction == DIRECTION_OUTBOUND:
        if any(marker in endpoint for marker in _AI_HOST_MARKERS):
            return "ai_provider"
        if "/api/v1/" in endpoint:
            return "gateway_calls"
        return "outbound_other"
    path = _PROXY_PREFIX.sub("", endpoint.split("?", 1)[0]).rstrip("/") or "/"
    if method == "POST" and path in ("/api/v1/chat", "/api/v1/answers"):
        return "search"
    if path == "/api/v1/chatbot":
        return "chatbot"
    if path.startswith("/api/v1/auth/"):
        return "auth"
    if path in _ACCOUNT_PATHS or path.startswith("/api/v1/users/me"):
        return "account"
    if path in _HEALTH_PATHS:
        return "health"
    return "other"


class QueryBreakdownService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def breakdown(
        self,
        *,
        hours: int,
        user_id: Optional[int],
        service: Optional[str],
        end_user: Optional[str],
    ) -> QueryBreakdown:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        analytics = AnalyticsService(self.session, end_user=end_user)
        filters = analytics._filters(user_id, since, service)

        rows = (
            await self.session.execute(
                select(
                    APILog.direction,
                    APILog.method,
                    APILog.endpoint,
                    func.count(APILog.id),
                    func.sum(case((APILog.status_code >= 400, 1), else_=0)),
                    func.sum(APILog.response_time_ms),
                )
                .where(*filters)
                .group_by(APILog.direction, APILog.method, APILog.endpoint)
            )
        ).all()

        totals: dict[str, list[float]] = defaultdict(lambda: [0, 0, 0.0])
        endpoints: dict[str, list[QueryEndpoint]] = defaultdict(list)
        for direction, method, endpoint, count, errors, time_sum in rows:
            key = classify(direction, method, endpoint)
            bucket = totals[key]
            bucket[0] += int(count or 0)
            bucket[1] += int(errors or 0)
            bucket[2] += float(time_sum or 0.0)
            endpoints[key].append(QueryEndpoint(method=method, endpoint=endpoint, requests=int(count or 0)))

        categories = []
        for key, (label, group, description) in CATEGORIES.items():
            requests, errors, time_sum = totals.get(key, [0, 0, 0.0])
            categories.append(
                QueryCategory(
                    key=key,
                    label=label,
                    group=group,
                    description=description,
                    requests=int(requests),
                    errors=int(errors),
                    avg_response_time_ms=round(time_sum / requests, 2) if requests else 0.0,
                    endpoints=sorted(endpoints.get(key, []), key=lambda e: e.requests, reverse=True)[
                        :ENDPOINTS_PER_CATEGORY
                    ],
                )
            )

        def group_total(group: str) -> int:
            return sum(c.requests for c in categories if c.group == group)

        return QueryBreakdown(
            hours=hours,
            total_requests=sum(c.requests for c in categories),
            real_queries=group_total(GROUP_QUERY),
            supporting_requests=group_total(GROUP_SUPPORTING),
            outbound_calls=group_total(GROUP_OUTBOUND),
            categories=categories,
            searches=await self._search_totals(since, user_id=user_id, service=service, end_user=end_user),
        )

    async def _search_totals(
        self, since: datetime, *, user_id: Optional[int], service: Optional[str], end_user: Optional[str]
    ) -> QuerySearchTotals:
        filters = [AnswerLog.created_at >= since]
        if end_user:
            filters.append(AnswerLog.end_user == end_user)
        elif service:
            account = await AnalyticsService(self.session).service_account_id(service)
            filters.append(AnswerLog.user_id == (account if account is not None else -1))
        elif user_id is not None:
            filters.append(AnswerLog.user_id == user_id)
        hit = AnswerLog.cache_status.in_(("exact_hit", "semantic_hit"))
        row = (
            await self.session.execute(
                select(
                    func.count(AnswerLog.id),
                    func.sum(case((hit, 1), else_=0)),
                    func.sum(case((AnswerLog.status != "ok", 1), else_=0)),
                    func.avg(AnswerLog.latency_ms),
                    func.sum(AnswerLog.total_tokens),
                    func.sum(AnswerLog.billable_tokens),
                    func.sum(AnswerLog.cost_inr),
                ).where(*filters)
            )
        ).one()
        questions = int(row[0] or 0)
        cache_hits = int(row[1] or 0)
        errors = int(row[2] or 0)
        return QuerySearchTotals(
            questions=questions,
            cache_hits=cache_hits,
            fresh_answers=max(questions - cache_hits - errors, 0),
            errors=errors,
            avg_latency_ms=round(float(row[3] or 0.0), 2),
            total_tokens=int(row[4] or 0),
            billable_tokens=int(row[5] or 0),
            cost_inr=round(float(row[6] or 0.0), 2),
            rate_per_token_inr=settings.answers_inr_per_token,
        )
