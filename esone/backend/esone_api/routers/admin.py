"""Admin-only user management."""
from fastapi import APIRouter, Query

from esone_api import services
from esone_api.deps import AdminUser, SessionDep
from esone_api.schemas import AdminUserUpdate, UserListResponse, UserResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=UserListResponse)
async def list_users(
    _: AdminUser,
    session: SessionDep,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    items, total = await services.list_users(session, limit, offset)
    return UserListResponse(items=items, total=total, limit=limit, offset=offset)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, data: AdminUserUpdate, actor: AdminUser, session: SessionDep):
    """Change a user's role or active flag. Deactivating revokes their refresh tokens."""
    return await services.admin_update_user(session, actor, user_id, data.role, data.is_active)
