"""
Schemas for the admin user directory (GET /api/v1/users, GET /api/v1/users/detail).

Two kinds of user appear:

* ``account``  a gateway account from the ``users`` table (admin, operator,
               viewer, service accounts such as esone-bot).
* ``end_user`` a person using a monitored service (for example ``esone:7``),
               known to the gateway through the questions that service
               forwards. Their profile is what the service sent with those
               questions; their raw API traffic is recorded under the
               service's own account and is not split per person.
"""
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.ai_usage import AIRequestLogItem, AIUsageSummary
from app.schemas.analytics import AnalyticsSummary
from app.schemas.answers import AnswerLogItem, AnswerStats
from app.schemas.guardrails import GuardrailEventItem, GuardrailSummary
from app.schemas.rate_limits import RateLimitUsage

UserKind = Literal["account", "end_user"]


class UserListItem(BaseModel):
    #: "account:<id>" or the end-user reference (e.g. "esone:7"); pass it to /users/detail.
    key: str
    kind: UserKind
    user_id: Optional[int] = None
    end_user: Optional[str] = None
    service: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    api_requests: int = 0
    searches: int = 0
    cache_hits: int = 0
    total_tokens: int = 0
    billable_tokens: int = 0
    cost_inr: float = 0.0


class UserListPage(BaseModel):
    hours: int
    total: int
    offset: int
    limit: int
    items: List[UserListItem] = Field(default_factory=list)


class UserProfile(BaseModel):
    key: str
    kind: UserKind
    user_id: Optional[int] = None
    end_user: Optional[str] = None
    service: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None


class UserBilling(BaseModel):
    currency: str = "INR"
    rate_per_token: float
    billable_tokens: int
    cost_inr: float
    paid_answers: int
    free_answers: int


class UserDetail(BaseModel):
    hours: int
    profile: UserProfile
    #: What is not available for this kind of user, in plain words (empty for accounts).
    notes: List[str] = Field(default_factory=list)
    traffic: Optional[AnalyticsSummary] = None
    rate_limit: Optional[RateLimitUsage] = None
    answers: AnswerStats
    recent_answers: List[AnswerLogItem] = Field(default_factory=list)
    billing: UserBilling
    ai_usage: Optional[AIUsageSummary] = None
    ai_calls: List[AIRequestLogItem] = Field(default_factory=list)
    guardrails: Optional[GuardrailSummary] = None
    guardrail_events: List[GuardrailEventItem] = Field(default_factory=list)
