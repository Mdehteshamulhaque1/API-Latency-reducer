"""
Security utilities for JWT, password hashing, and authentication.
"""
from datetime import datetime, timedelta, UTC
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.core.exceptions import AuthenticationError, AuthorizationError

# Security scheme
security = HTTPBearer()


class JWTHandler:
    """Handles JWT token creation and validation."""

    @staticmethod
    def create_access_token(
        data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(
                minutes=settings.access_token_expire_minutes
            )
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.algorithm,
        )
        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """Create a JWT refresh token."""
        to_encode = data.copy()
        expire = datetime.now(UTC) + timedelta(
            days=settings.refresh_token_expire_days
        )
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.algorithm,
        )
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> dict:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm],
            )
            return payload
        except JWTError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")

    @staticmethod
    def verify_token_type(payload: dict, expected_type: str = "access") -> None:
        """Verify the token type matches the expected type."""
        token_type = payload.get("type")
        if token_type != expected_type:
            raise AuthenticationError(
                f"Invalid token type. Expected '{expected_type}', got '{token_type}'"
            )


class PasswordHandler:
    """Handles password hashing and verification using bcrypt directly."""

    # bcrypt only uses the first 72 bytes of a password.
    _MAX_BYTES = 72

    @staticmethod
    def _prep(password: str) -> bytes:
        return password.encode("utf-8")[: PasswordHandler._MAX_BYTES]

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password."""
        return bcrypt.hashpw(PasswordHandler._prep(password), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        try:
            return bcrypt.checkpw(
                PasswordHandler._prep(plain_password),
                hashed_password.encode("utf-8"),
            )
        except ValueError:
            return False


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Dependency to extract and validate JWT token from request.
    Returns the payload if valid.
    """
    token = credentials.credentials
    try:
        payload = JWTHandler.decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("Invalid token claims")
        return payload
    except JWTError:
        raise AuthenticationError("Invalid token")


async def verify_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency to verify user has admin role.
    """
    role = current_user.get("role")
    if role != "admin":
        raise AuthorizationError("Admin access required")
    return current_user


def verify_role(required_roles: list):
    """
    Factory function to create role-checking dependencies.

    Usage:
        @app.get("/endpoint")
        async def endpoint(current_user: dict = Depends(verify_role(["admin", "operator"]))):
            pass
    """
    async def _verify_role(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role")
        if user_role not in required_roles:
            raise AuthorizationError(f"Requires one of roles: {', '.join(required_roles)}")
        return current_user

    return _verify_role
