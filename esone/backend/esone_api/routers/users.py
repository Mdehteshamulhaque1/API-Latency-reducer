"""Endpoints for the signed-in user."""
from fastapi import APIRouter, Response, status

from esone_api import services
from esone_api.deps import CurrentUser, SessionDep
from esone_api.schemas import PasswordChange, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser):
    return user


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(data: PasswordChange, user: CurrentUser, session: SessionDep):
    """Change the password. Every refresh token for the account is revoked."""
    await services.change_password(session, user, data.current_password, data.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
