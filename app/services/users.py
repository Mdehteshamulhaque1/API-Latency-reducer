"""
Admin user directory: every user, and everything the gateway knows about one.

The list joins gateway accounts (``users``) with the end users of monitored
services (``end_users``, plus any end-user reference seen in ``answer_logs``
before that table existed) and adds activity totals in a few grouped
queries. The detail view reuses the same services as the overall dashboard
(analytics, rate limits, answer history, AI usage, guardrails), each scoped
to that one user, so per-user numbers are calculated exactly like the
overall ones.

End users of a monitored service have a profile, searches, tokens and
charges. Their HTTP traffic is recorded under the service's own account,
and their AI calls and guardrail events likewise, so those sections are
reported as unavailable rather than guessed.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.guardrails.events import GuardrailEventService
from app.config import settings
from app.database.db import async_session_maker
from app.models import AnswerLog, APILog, EndUser, User
from app.schemas.guardrails import GuardrailEventItem, GuardrailSummary
from app.schemas.rate_limits import RateLimitUsage
from app.schemas.users import UserBilling, UserDetail, UserListItem, UserListPage, UserProfile
from app.services.ai_usage import AIUsageService
from app.services.analytics import AnalyticsService
from app.services.answer_history import STATUS_OK, AnswerHistoryService
from app.services.answers import CACHE_EXACT_HIT, CACHE_SEMANTIC_HIT
from app.services.rate_limit import RateLimitService, limits_for_role
from app.utils.redis_client import redis_client

logger = logging.getLogger(__name__)

ACCOUNT_PREFIX = "account:"
RECENT_LIMIT = 25
NOTE_END_USER = (
    "This person uses {service}. API activity covers the requests they made while signed in; their AI calls "
    "and guardrail events are recorded under {service}'s service account."
)


def _latest(*moments: Optional[datetime]) -> Optional[datetime]:
    """The most recent of several optional timestamps (timezone-aware)."""
    aware = [_aware(moment) for moment in moments if moment is not None]
    return max(aware) if aware else None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _service_of(ref: str) -> Optional[str]:
    return ref.split(":", 1)[0] if ":" in ref else None


class UserDirectoryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ---------------------------------------------------------------- list

    async def list_users(
        self, *, hours: int, search: Optional[str], kind: Optional[str], limit: int, offset: int
    ) -> UserListPage:
        since = _utcnow() - timedelta(hours=hours)
        needle = (search or "").strip().lower()
        ok = AnswerLog.status == STATUS_OK
        hit = AnswerLog.cache_status.in_([CACHE_EXACT_HIT, CACHE_SEMANTIC_HIT])

        items: List[UserListItem] = []

        if kind in (None, "account"):
            accounts = (await self.session.execute(select(User))).scalars().all()
            requests = dict(
                (
                    await self.session.execute(
                        select(APILog.user_id, func.count(APILog.id))
                        .where(APILog.created_at >= since, APILog.user_id.is_not(None))
                        .group_by(APILog.user_id)
                    )
                ).all()
            )
            last_request = dict(
                (
                    await self.session.execute(
                        select(APILog.user_id, func.max(APILog.created_at))
                        .where(APILog.user_id.is_not(None))
                        .group_by(APILog.user_id)
                    )
                ).all()
            )
            # Searches made by the account itself (not on behalf of an end user).
            own = {
                row[0]: row[1:]
                for row in (
                    await self.session.execute(
                        select(
                            AnswerLog.user_id,
                            func.count(AnswerLog.id),
                            func.sum(case((hit, 1), else_=0)),
                            func.sum(AnswerLog.total_tokens),
                            func.sum(AnswerLog.billable_tokens),
                            func.sum(AnswerLog.cost_inr),
                        )
                        .where(AnswerLog.created_at >= since, AnswerLog.end_user.is_(None), ok)
                        .group_by(AnswerLog.user_id)
                    )
                ).all()
            }
            for user in accounts:
                totals = own.get(user.id, (0, 0, 0, 0, 0.0))
                items.append(
                    UserListItem(
                        key=f"{ACCOUNT_PREFIX}{user.id}",
                        kind="account",
                        user_id=user.id,
                        username=user.username,
                        email=user.email,
                        role=user.role,
                        is_active=user.is_active,
                        created_at=_aware(user.created_at),
                        last_seen_at=_aware(last_request.get(user.id)),
                        api_requests=int(requests.get(user.id, 0) or 0),
                        searches=int(totals[0] or 0),
                        cache_hits=int(totals[1] or 0),
                        total_tokens=int(totals[2] or 0),
                        billable_tokens=int(totals[3] or 0),
                        cost_inr=round(float(totals[4] or 0.0), 2),
                    )
                )

        if kind in (None, "end_user"):
            known = {row.ref: row for row in (await self.session.execute(select(EndUser))).scalars().all()}
            activity = {
                row[0]: row[1:]
                for row in (
                    await self.session.execute(
                        select(
                            AnswerLog.end_user,
                            func.count(AnswerLog.id),
                            func.sum(case((hit, 1), else_=0)),
                            func.sum(AnswerLog.total_tokens),
                            func.sum(AnswerLog.billable_tokens),
                            func.sum(AnswerLog.cost_inr),
                            func.max(AnswerLog.created_at),
                        )
                        .where(AnswerLog.end_user.is_not(None), ok, AnswerLog.created_at >= since)
                        .group_by(AnswerLog.end_user)
                    )
                ).all()
            }
            seen_ever = {
                row[0]: row[1]
                for row in (
                    await self.session.execute(
                        select(AnswerLog.end_user, func.max(AnswerLog.created_at))
                        .where(AnswerLog.end_user.is_not(None))
                        .group_by(AnswerLog.end_user)
                    )
                ).all()
            }
            # Requests the service tagged with the person (api_logs.end_user).
            end_user_requests = dict(
                (
                    await self.session.execute(
                        select(APILog.end_user, func.count(APILog.id))
                        .where(APILog.created_at >= since, APILog.end_user.is_not(None))
                        .group_by(APILog.end_user)
                    )
                ).all()
            )
            for ref, last in (
                await self.session.execute(
                    select(APILog.end_user, func.max(APILog.created_at))
                    .where(APILog.end_user.is_not(None))
                    .group_by(APILog.end_user)
                )
            ).all():
                seen_ever[ref] = _latest(seen_ever.get(ref), last)
            for ref in sorted(set(known) | set(seen_ever)):
                profile = known.get(ref)
                totals = activity.get(ref, (0, 0, 0, 0, 0.0, None))
                items.append(
                    UserListItem(
                        key=ref,
                        kind="end_user",
                        end_user=ref,
                        service=profile.service if profile else _service_of(ref),
                        username=profile.display_name if profile else None,
                        email=profile.email if profile else None,
                        created_at=_aware(profile.created_at) if profile else None,
                        last_seen_at=_latest(profile.last_seen_at if profile else None, seen_ever.get(ref)),
                        api_requests=int(end_user_requests.get(ref, 0) or 0),
                        searches=int(totals[0] or 0),
                        cache_hits=int(totals[1] or 0),
                        total_tokens=int(totals[2] or 0),
                        billable_tokens=int(totals[3] or 0),
                        cost_inr=round(float(totals[4] or 0.0), 2),
                    )
                )

        if needle:
            items = [
                item
                for item in items
                if any(needle in (value or "").lower() for value in (item.key, item.username, item.email, item.role, item.service))
            ]
        epoch = datetime.min.replace(tzinfo=timezone.utc)
        items.sort(key=lambda item: (item.last_seen_at or epoch, item.searches + item.api_requests), reverse=True)
        return UserListPage(hours=hours, total=len(items), offset=offset, limit=limit, items=items[offset : offset + limit])

    # -------------------------------------------------------------- detail

    async def detail(self, key: str, *, hours: int) -> Optional[UserDetail]:
        if key.startswith(ACCOUNT_PREFIX):
            try:
                user_id = int(key[len(ACCOUNT_PREFIX):])
            except ValueError:
                return None
            return await self._account_detail(user_id, hours)
        return await self._end_user_detail(key, hours)

    async def _billing(self, filters: list) -> UserBilling:
        row = (
            await self.session.execute(
                select(
                    func.sum(AnswerLog.billable_tokens),
                    func.sum(AnswerLog.cost_inr),
                    func.sum(case((AnswerLog.cost_inr > 0, 1), else_=0)),
                    func.sum(case((AnswerLog.cost_inr > 0, 0), else_=1)),
                ).where(*filters, AnswerLog.status == STATUS_OK)
            )
        ).one()
        return UserBilling(
            rate_per_token=settings.answers_inr_per_token,
            billable_tokens=int(row[0] or 0),
            cost_inr=round(float(row[1] or 0.0), 2),
            paid_answers=int(row[2] or 0),
            free_answers=int(row[3] or 0),
        )

    async def _account_detail(self, user_id: int, hours: int) -> Optional[UserDetail]:
        user = await self.session.get(User, user_id)
        if user is None:
            return None
        since = _utcnow() - timedelta(hours=hours)
        last_seen = (
            await self.session.execute(select(func.max(APILog.created_at)).where(APILog.user_id == user_id))
        ).scalar()

        traffic = await AnalyticsService(self.session).get_analytics_summary(user_id=user_id, hours=hours)
        tier = limits_for_role(user.role)
        bucket = await RateLimitService(redis_client).get_usage(f"user:{user_id}", tier.requests, tier.period)
        history = AnswerHistoryService(self.session)
        answers = await history.stats(hours=hours, user_id=user_id, scope="user")
        recent = await history.recent(hours=hours, user_id=user_id, scope="user", limit=RECENT_LIMIT)
        usage = AIUsageService(self.session)
        ai_summary = await usage.summary(hours=hours, user_id=user_id, scope="user")
        ai_calls = await usage.recent(hours=hours, user_id=user_id, scope="user", limit=RECENT_LIMIT)
        events = GuardrailEventService(self.session)
        guard = await events.summary(hours=hours, user_id=user_id)
        guard_rows = await events.recent(hours=hours, user_id=user_id, limit=RECENT_LIMIT)

        notes: List[str] = []
        if await self._is_service_account(user_id):
            notes.append(
                "This is a service account: its traffic and searches include everything the service forwards "
                "for its own users, who are listed separately."
            )
        return UserDetail(
            hours=hours,
            profile=UserProfile(
                key=f"{ACCOUNT_PREFIX}{user_id}",
                kind="account",
                user_id=user_id,
                username=user.username,
                email=user.email,
                role=user.role,
                is_active=user.is_active,
                created_at=_aware(user.created_at),
                last_seen_at=_aware(last_seen),
            ),
            notes=notes,
            traffic=traffic,
            rate_limit=RateLimitUsage(tier=tier.name, **bucket),
            answers=answers,
            recent_answers=recent.items,
            billing=await self._billing([AnswerLog.user_id == user_id, AnswerLog.created_at >= since]),
            ai_usage=ai_summary,
            ai_calls=ai_calls.items,
            guardrails=GuardrailSummary(
                scope="user",
                injection_blocking_enabled=settings.guardrails_block_injection,
                pii_masking_enabled=settings.guardrails_mask_pii,
                **guard,
            ),
            guardrail_events=[GuardrailEventItem.model_validate(row, from_attributes=True) for row in guard_rows],
        )

    async def _is_service_account(self, user_id: int) -> bool:
        return bool(
            (
                await self.session.execute(
                    select(func.count(AnswerLog.id)).where(AnswerLog.user_id == user_id, AnswerLog.end_user.is_not(None))
                )
            ).scalar()
        )

    async def _end_user_detail(self, ref: str, hours: int) -> Optional[UserDetail]:
        profile = (await self.session.execute(select(EndUser).where(EndUser.ref == ref))).scalar_one_or_none()
        seen = (
            await self.session.execute(
                select(func.min(AnswerLog.created_at), func.max(AnswerLog.created_at)).where(AnswerLog.end_user == ref)
            )
        ).one()
        last_request = (
            await self.session.execute(select(func.max(APILog.created_at)).where(APILog.end_user == ref))
        ).scalar()
        if profile is None and seen[1] is None and last_request is None:
            return None
        since = _utcnow() - timedelta(hours=hours)
        service = profile.service if profile else _service_of(ref)
        history = AnswerHistoryService(self.session)
        return UserDetail(
            hours=hours,
            profile=UserProfile(
                key=ref,
                kind="end_user",
                end_user=ref,
                service=service,
                username=profile.display_name if profile else None,
                email=profile.email if profile else None,
                created_at=_aware(profile.created_at if profile else seen[0]),
                last_seen_at=_latest(profile.last_seen_at if profile else seen[1], last_request),
            ),
            notes=[NOTE_END_USER.format(service=service or "the service")],
            traffic=await AnalyticsService(self.session, end_user=ref).get_analytics_summary(hours=hours),
            answers=await history.stats(hours=hours, user_id=None, scope="end_user", end_user=ref),
            recent_answers=(
                await history.recent(hours=hours, user_id=None, scope="end_user", limit=RECENT_LIMIT, end_user=ref)
            ).items,
            billing=await self._billing([AnswerLog.end_user == ref, AnswerLog.created_at >= since]),
        )


# ---------------------------------------------------------------------------
# End-user profiles, written as questions arrive
# ---------------------------------------------------------------------------

async def upsert_end_user(ref: str, *, name: Optional[str], email: Optional[str]) -> None:
    """Remember who an end-user reference belongs to. Best effort; never breaks a request."""
    try:
        async with async_session_maker() as session:
            row = (await session.execute(select(EndUser).where(EndUser.ref == ref))).scalar_one_or_none()
            now = _utcnow()
            if row is None:
                session.add(
                    EndUser(ref=ref, service=_service_of(ref), display_name=name, email=email, last_seen_at=now)
                )
            else:
                row.last_seen_at = now
                if name:
                    row.display_name = name
                if email:
                    row.email = email
            await session.commit()
    except Exception as exc:  # noqa: BLE001 - bookkeeping only
        logger.warning("Failed to record end user: %s", type(exc).__name__)

