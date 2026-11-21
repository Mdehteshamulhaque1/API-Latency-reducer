"""
Authentication service for user management and JWT handling.
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import PasswordHandler, JWTHandler
from app.core.exceptions import (
    APIException,
    AuthenticationError,
    ResourceNotFoundError,
    ResourceAlreadyExistsError,
)
from app.core.constants import UserRole
from app.config import settings
from app.models import User
from app.schemas.auth import UserCreate, TokenResponse
from app.services.token_denylist import TokenDenylist

logger = logging.getLogger(__name__)


class AuthService:
    """
    Authentication service for user registration, login, and token management.
    """

    def __init__(self, session: AsyncSession, denylist: Optional[TokenDenylist] = None):
        self.session = session
        self.denylist = denylist or TokenDenylist()

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

        # Hash password and create user.
        # Only non-privileged roles are allowed on self-registration so a
        # caller can never escalate to admin/operator via the public API.
        role = (
            user_data.role
            if user_data.role in {UserRole.VIEWER, UserRole.GUEST}
            else UserRole.VIEWER
        )
        hashed_password = PasswordHandler.hash_password(user_data.password)
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            role=role,
        )

        self.session.add(new_user)
        await self.session.commit()
        await self.session.refresh(new_user)

        logger.info(f"User registered: {new_user.username}")
        return new_user

    async def authenticate_user(
        self, username: str, password: str
    ) -> Optional[User]:
        """Authenticate user by username (or email) and password."""
        # Find user
        result = await self.session.execute(
            select(User).where((User.username == username) | (User.email == username))
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
            expires_in=settings.access_token_expire_minutes * 60,
        )

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Create new access token from refresh token."""
        try:
            payload = JWTHandler.decode_token(refresh_token)
            JWTHandler.verify_token_type(payload, "refresh")

            if await self.denylist.is_revoked(payload.get("jti")):
                raise AuthenticationError("Refresh token has been revoked")

            user_id = int(payload.get("sub"))
            user = await self.get_user(user_id)

            if not user.is_active:
                raise AuthenticationError("User account is inactive")

            # Create new tokens
            return self.create_tokens(user)
        except APIException:
            raise
        except Exception as e:
            raise AuthenticationError(f"Invalid refresh token: {str(e)}")

    async def logout(self, access_payload: dict, refresh_token: str) -> None:
        """Revoke the caller's access token and the presented refresh token.

        The refresh token must belong to the same user as the access token so
        one account cannot revoke another account's session.
        """
        try:
            refresh_payload = JWTHandler.decode_token(refresh_token)
            JWTHandler.verify_token_type(refresh_payload, "refresh")
        except APIException:
            raise
        except Exception as e:
            raise AuthenticationError(f"Invalid refresh token: {str(e)}")

        if refresh_payload.get("sub") != access_payload.get("sub"):
            raise AuthenticationError("Refresh token does not belong to this user")

        await self.denylist.revoke(refresh_payload.get("jti"), refresh_payload.get("exp"))
        await self.denylist.revoke(access_payload.get("jti"), access_payload.get("exp"))
        logger.info("User logged out", extra={"user_id": access_payload.get("sub")})
