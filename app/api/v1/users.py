"""
Admin user directory.

GET /users          every gateway account and every end user of a monitored
                    service, with activity totals; search and kind filters
GET /users/detail   one user: profile, API traffic, rate-limit bucket,
                    searches, billing, AI usage and guardrail events

Admin only: these views expose every user's data.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIException
from app.core.security import verify_role
from app.database.db import get_session
from app.schemas.users import UserDetail, UserListPage
from app.services.users import UserDirectoryService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=UserListPage)
async def list_users(
    hours: int = Query(default=720, gt=0, le=720, description="Activity window for the totals"),
    search: Optional[str] = Query(default=None, max_length=100, description="Matches name, email, role or reference"),
    kind: Optional[str] = Query(default=None, pattern=r"^(account|end_user)$"),
    limit: int = Query(default=100, gt=0, le=500),
    offset: int = Query(default=0, ge=0),
    _: dict = Depends(verify_role(["admin"])),
    session: AsyncSession = Depends(get_session),
) -> UserListPage:
    return await UserDirectoryService(session).list_users(
        hours=hours, search=search, kind=kind, limit=limit, offset=offset
    )


@router.get("/detail", response_model=UserDetail)
async def user_detail(
    key: str = Query(..., min_length=3, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9:_.@-]*$"),
    hours: int = Query(default=720, gt=0, le=720),
    _: dict = Depends(verify_role(["admin"])),
    session: AsyncSession = Depends(get_session),
) -> UserDetail:
    detail = await UserDirectoryService(session).detail(key, hours=hours)
    if detail is None:
        raise APIException(message="User not found", status_code=404, error_code="NOT_FOUND")
    return detail
