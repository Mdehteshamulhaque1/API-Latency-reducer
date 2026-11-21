from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.core.view_as import AsUserParam, resolve_view_as
from app.database.db import get_session
from app.schemas.pricing import PricingTableResponse, UserTokenUsageResponse
from app.services.pricing import get_pricing_table
from app.services.pricing import get_user_token_usage as get_user_token_usage_service

router = APIRouter(prefix="/pricing", tags=["Pricing"])


@router.get("", response_model=PricingTableResponse)
async def get_pricing(current_user: dict = Depends(get_current_user)) -> PricingTableResponse:
    return get_pricing_table()


@router.get("/users", response_model=UserTokenUsageResponse)
async def get_user_token_usage(
    as_user: Optional[str] = AsUserParam,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> UserTokenUsageResponse:
    """Token billing per caller. Admins see everyone (or one user with as_user); others see their own."""
    view = resolve_view_as(current_user, as_user)
    if view is not None:
        if view.end_user is not None:
            return await get_user_token_usage_service(session, end_user=view.end_user)
        return await get_user_token_usage_service(session, owner_id=view.user_id)
    if current_user.get("role") == "admin":
        return await get_user_token_usage_service(session)
    return await get_user_token_usage_service(session, owner_id=int(current_user.get("sub")))
