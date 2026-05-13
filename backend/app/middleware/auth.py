"""
Authentication middleware using JWT.
"""
import logging
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.exceptions import AuthenticationError
from app.core.security import JWTHandler

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    JWT Authentication middleware.
    Validates JWT tokens and extracts user information.
    
    Protected endpoints require 'Authorization: Bearer <token>' header.
    """

    # Paths that don't require authentication
    UNPROTECTED_PATHS = {
        "/",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/health",
        "/api/v1/ping",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    async def dispatch(self, request: Request, call_next):
        """Process request and validate JWT token."""
        
        # Skip authentication for unprotected paths
        if request.url.path in self.UNPROTECTED_PATHS:
            return await call_next(request)
        
        # Check for Authorization header
        auth_header = request.headers.get("Authorization", "")
        
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Missing or invalid Authorization header",
                    "error_code": "AUTHENTICATION_ERROR",
                },
            )
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        try:
            payload = JWTHandler.decode_token(token)
            # Add user info to request state
            request.state.user_id = payload.get("sub")
            request.state.user_role = payload.get("role")
            request.state.payload = payload
        except AuthenticationError as e:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": e.message,
                    "error_code": e.error_code,
                },
            )
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Invalid token",
                    "error_code": "AUTHENTICATION_ERROR",
                },
            )
        
        return await call_next(request)
