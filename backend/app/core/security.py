"""
Security utilities for JWT, password hashing, and authentication.
"""
from datetime import datetime, timedelta
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.core.exceptions import AuthenticationError, AuthorizationError

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.access_token_expire_minutes
            )
        
        to_encode.update({"exp": expire})
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
        expire = datetime.utcnow() + timedelta(
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
    def verify_token_type(payload: dict, expected_type: str = "access"):
        """Verify the token type."""
        token_type = payload.get("type", expected_type)
        if expected_type != "access" and token_type != expected_type:
            raise AuthenticationError(f"Invalid token type. Expected {expected_type}")


class PasswordHandler:
    """Handles password hashing and verification."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)


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
