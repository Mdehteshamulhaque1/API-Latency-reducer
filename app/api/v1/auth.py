"""
Authentication API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_session
from app.schemas.auth import UserCreate, UserLogin, UserResponse, TokenResponse, TokenRefresh
from app.services.auth import AuthService
from app.core.exceptions import APIException

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session),
):
    """Register a new user."""
    try:
        auth_service = AuthService(session)
        user = await auth_service.register_user(user_data)
        return UserResponse.from_orm(user)
    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    session: AsyncSession = Depends(get_session),
):
    """Login and get access token."""
    try:
        auth_service = AuthService(session)
        user = await auth_service.authenticate_user(credentials.username, credentials.password)
        tokens = auth_service.create_tokens(user)
        return tokens
    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    token_data: TokenRefresh,
    session: AsyncSession = Depends(get_session),
):
    """Refresh access token."""
    try:
        auth_service = AuthService(session)
        tokens = await auth_service.refresh_access_token(token_data.refresh_token)
        return tokens
    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
