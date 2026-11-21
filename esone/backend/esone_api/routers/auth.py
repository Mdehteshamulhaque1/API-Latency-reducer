"""Register, login, refresh and logout."""
from fastapi import APIRouter, Response, status

from esone_api import services, telemetry
from esone_api.deps import SessionDep
from esone_api.schemas import TokenRefresh, TokenResponse, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, session: SessionDep):
    """Create a viewer account. Sign in afterwards to obtain tokens."""
    return await services.register_user(session, data)


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, session: SessionDep):
    user = await services.authenticate(session, data.username, data.password)
    telemetry.mark_end_user(user.id)
    return await services.issue_tokens(session, user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: TokenRefresh, session: SessionDep):
    """Exchange a refresh token for a new pair. The old refresh token is revoked."""
    return await services.rotate_refresh_token(session, data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: TokenRefresh, session: SessionDep):
    await services.logout(session, data.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
