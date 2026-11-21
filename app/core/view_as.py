"""
"View as user": lets an admin see every dashboard read scoped to one user.

Read endpoints accept ``as_user``: ``account:<id>`` for a gateway account or
an end-user reference such as ``esone:7``. Only admins may pass it; anyone
else gets 403. When present it overrides ``service``: the response covers
that one user, never a whole service and never everyone.

End users of a monitored service are matched by the reference the service
tags their rows with: request logs (``api_logs.end_user``), searches, tokens
and charges. Their AI calls and guardrail events are recorded under the
service's account, so those reads are scoped to :data:`NOBODY` and come back
empty instead of falling back to "all".
"""
from dataclasses import dataclass
from typing import Optional

from fastapi import Query

from app.core.exceptions import AuthorizationError

ACCOUNT_PREFIX = "account:"
#: A user id no row carries: an empty result instead of everyone's data.
NOBODY = -1
SCOPE_USER = "user"

AsUserParam = Query(
    default=None,
    min_length=3,
    max_length=100,
    pattern=r"^[A-Za-z0-9][A-Za-z0-9:_.@-]*$",
    description="Admin only: show one user's data (account:<id> or an end-user reference such as esone:7)",
)


@dataclass(frozen=True)
class ViewAs:
    key: str
    #: Gateway account id, or None for an end user.
    account_id: Optional[int]
    #: End-user reference, or None for an account.
    end_user: Optional[str]

    @property
    def user_id(self) -> int:
        """Filter for tables keyed by gateway account (api_logs, ai_request_logs, guardrail_events)."""
        return self.account_id if self.account_id is not None else NOBODY


def resolve_view_as(current_user: dict, as_user: Optional[str]) -> Optional[ViewAs]:
    """The user an admin asked to view as, or None. Raises 403 for non-admins."""
    if not as_user:
        return None
    if current_user.get("role") != "admin":
        raise AuthorizationError("Only administrators can view another user's data")
    if as_user.startswith(ACCOUNT_PREFIX):
        try:
            return ViewAs(key=as_user, account_id=int(as_user[len(ACCOUNT_PREFIX):]), end_user=None)
        except ValueError:
            return ViewAs(key=as_user, account_id=NOBODY, end_user=None)
    return ViewAs(key=as_user, account_id=None, end_user=as_user)
