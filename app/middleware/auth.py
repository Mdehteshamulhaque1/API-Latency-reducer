"""
Authentication middleware using JWT.

Runs before RateLimit and Cache so both can key on the authenticated user.
Public paths pass straight through; every other path needs a valid, non-revoked
access token. On success the user id, role, and raw claims are stored on
``request.state`` for downstream middleware and routes.
"""
import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.exceptions import AuthenticationError
from app.core.security import JWTHandler
from app.services.token_denylist import TokenDenylist

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
        "/api/v1/demo/latency",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    # Path prefixes whose requests are authenticated by the upstream they are
    # forwarded to (see app/api/v1/proxy.py), not by this gateway. Approved by
    # the project owner on 2026-11-16.
    UNPROTECTED_PREFIXES = ("/proxy/",)

    async def dispatch(self, request: Request, call_next):
        """Process request and validate JWT token."""

        # Skip authentication for unprotected paths
        if request.url.path in self.UNPROTECTED_PATHS or request.url.path.startswith(self.UNPROTECTED_PREFIXES):
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

            # Verify token type is 'access' (not 'refresh' or other types)
            JWTHandler.verify_token_type(payload, "access")

            # Reject tokens revoked by logout (fails open when Redis is down)
            if await TokenDenylist().is_revoked(payload.get("jti")):
                raise AuthenticationError("Token has been revoked")

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
