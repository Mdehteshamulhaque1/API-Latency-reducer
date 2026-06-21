"""
Authentication service for user management and JWT handling.
"""
import logging
from datetime import timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import PasswordHandler, JWTHandler
from app.core.exceptions import (
    AuthenticationError,
    ResourceNotFoundError,
    ResourceAlreadyExistsError,
)
from app.models import User
from app.schemas.auth import UserCreate, TokenResponse

logger = logging.getLogger(__name__)


class AuthService:
    """
    Authentication service for user registration, login, and token management.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_user(self, user_data: UserCreate) -> User:
        """Register a new user."""
        # Check if user already exists
        existing_user = await self.session.execute(
            select(User).where(User.email == user_data.email)
        )
        if existing_user.scalar_one_or_none():
            raise ResourceAlreadyExistsError("User", "email", user_data.email)
        
        existing_user = await self.session.execute(
            select(User).where(User.username == user_data.username)
        )
        if existing_user.scalar_one_or_none():
            raise ResourceAlreadyExistsError("User", "username", user_data.username)
        
        # Hash password and create user
        hashed_password = PasswordHandler.hash_password(user_data.password)
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            role=user_data.role or "viewer",
        )
        
        self.session.add(new_user)
        await self.session.commit()
        await self.session.refresh(new_user)
        
        logger.info(f"User registered: {new_user.username}")
        return new_user

    async def authenticate_user(
        self, username: str, password: str
    ) -> Optional[User]:
        """Authenticate user by username and password."""
        # Find user
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        
        if not user or not PasswordHandler.verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid username or password")
        
        if not user.is_active:
            raise AuthenticationError("User account is inactive")
        
        logger.info(f"User authenticated: {user.username}")
        return user

    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise ResourceNotFoundError("User", user_id)
        
        return user

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    def create_tokens(self, user: User) -> TokenResponse:
        """Create access and refresh tokens for user."""
        # Access token
        access_token = JWTHandler.create_access_token(
            data={"sub": str(user.id), "role": user.role}
        )
        
        # Refresh token
        refresh_token = JWTHandler.create_refresh_token(
            data={"sub": str(user.id), "role": user.role}
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=30 * 60,  # 30 minutes in seconds
        )

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Create new access token from refresh token."""
        try:
            payload = JWTHandler.decode_token(refresh_token)
            JWTHandler.verify_token_type(payload, "refresh")
            
            user_id = int(payload.get("sub"))
            user = await self.get_user(user_id)
            
            # Create new tokens
            return self.create_tokens(user)
        except Exception as e:
            raise AuthenticationError(f"Invalid refresh token: {str(e)}")
