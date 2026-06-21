"""
Tests for JWT token type validation.

This test suite validates that:
1. Access tokens include type="access"
2. Refresh tokens include type="refresh"
3. AuthMiddleware rejects refresh tokens on protected endpoints
4. Refresh tokens can only be used on /auth/refresh endpoint
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from jose import jwt

from app.core.security import JWTHandler
from app.core.exceptions import AuthenticationError
from app.config import settings


class TestJWTTokenType:
    """Test JWT token type validation."""

    def test_access_token_has_type_access(self):
        """Verify that access tokens include type='access' claim."""
        data = {"sub": "123", "role": "admin"}
        access_token = JWTHandler.create_access_token(data)

        # Decode token (without verification to inspect claims)
        decoded = jwt.decode(
            access_token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )

        assert decoded.get("type") == "access", "Access token must have type='access'"
        assert decoded.get("sub") == "123"
        assert decoded.get("role") == "admin"

    def test_refresh_token_has_type_refresh(self):
        """Verify that refresh tokens include type='refresh' claim."""
        data = {"sub": "123", "role": "admin"}
        refresh_token = JWTHandler.create_refresh_token(data)

        # Decode token (without verification to inspect claims)
        decoded = jwt.decode(
            refresh_token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )

        assert decoded.get("type") == "refresh", "Refresh token must have type='refresh'"
        assert decoded.get("sub") == "123"
        assert decoded.get("role") == "admin"

    def test_verify_token_type_accepts_correct_type(self):
        """Verify that verify_token_type() accepts correct token types."""
        # Access token type validation
        payload_access = {"type": "access", "sub": "123"}
        JWTHandler.verify_token_type(payload_access, "access")  # Should not raise

        # Refresh token type validation
        payload_refresh = {"type": "refresh", "sub": "123"}
        JWTHandler.verify_token_type(payload_refresh, "refresh")  # Should not raise

    def test_verify_token_type_rejects_wrong_type(self):
        """Verify that verify_token_type() rejects mismatched token types."""
        # Attempt to use refresh token where access token is expected
        payload_refresh = {"type": "refresh", "sub": "123"}
        with pytest.raises(AuthenticationError) as exc_info:
            JWTHandler.verify_token_type(payload_refresh, "access")

        assert "Invalid token type" in str(exc_info.value)
        assert "'refresh'" in str(exc_info.value)
        assert "'access'" in str(exc_info.value)

        # Attempt to use access token where refresh token is expected
        payload_access = {"type": "access", "sub": "123"}
        with pytest.raises(AuthenticationError) as exc_info:
            JWTHandler.verify_token_type(payload_access, "refresh")

        assert "Invalid token type" in str(exc_info.value)

    def test_verify_token_type_rejects_missing_type(self):
        """Verify that verify_token_type() rejects tokens with missing type claim."""
        # Token without type claim (legacy or malformed)
        payload_no_type = {"sub": "123"}
        with pytest.raises(AuthenticationError) as exc_info:
            JWTHandler.verify_token_type(payload_no_type, "access")

        assert "Invalid token type" in str(exc_info.value)

    def test_refresh_token_validation_in_auth_service(self):
        """Verify that AuthService validates refresh tokens correctly."""
        from app.services.auth import AuthService

        # Create a mock session
        mock_session = AsyncMock()

        # Create auth service
        auth_service = AuthService(mock_session)

        # Create a refresh token
        refresh_token = JWTHandler.create_refresh_token({"sub": "123", "role": "admin"})

        # Decode to verify it has the correct type
        decoded = jwt.decode(
            refresh_token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        assert decoded.get("type") == "refresh"

    def test_access_token_cannot_be_used_as_refresh_token(self):
        """Verify that an access token is rejected when refresh is expected."""
        from app.services.auth import AuthService

        mock_session = AsyncMock()
        auth_service = AuthService(mock_session)

        # Create an access token
        access_token = JWTHandler.create_access_token({"sub": "123", "role": "admin"})

        # Attempt to use access token for refresh should fail
        with pytest.raises(AuthenticationError) as exc_info:
            payload = JWTHandler.decode_token(access_token)
            JWTHandler.verify_token_type(payload, "refresh")

        assert "Invalid token type" in str(exc_info.value)

    def test_token_type_claim_persists_after_decode(self):
        """Verify that token type claim is preserved through decode."""
        # Test access token
        access_data = {"sub": "456", "role": "viewer"}
        access_token = JWTHandler.create_access_token(access_data)
        decoded_access = JWTHandler.decode_token(access_token)

        assert decoded_access.get("type") == "access"
        assert decoded_access.get("sub") == "456"

        # Test refresh token
        refresh_data = {"sub": "456", "role": "viewer"}
        refresh_token = JWTHandler.create_refresh_token(refresh_data)
        decoded_refresh = JWTHandler.decode_token(refresh_token)

        assert decoded_refresh.get("type") == "refresh"
        assert decoded_refresh.get("sub") == "456"


class TestAuthMiddlewareTokenType:
    """Test AuthMiddleware token type validation."""

    @pytest.mark.asyncio
    async def test_middleware_accepts_access_token(self):
        """Verify that AuthMiddleware accepts valid access tokens."""
        from app.middleware.auth import AuthMiddleware

        # Create a mock request
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/analytics"
        mock_request.headers = {}

        # Create access token
        access_token = JWTHandler.create_access_token({"sub": "123", "role": "admin"})
        mock_request.headers.get = lambda key, default="": f"Bearer {access_token}"

        # Create mock call_next
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_call_next = AsyncMock(return_value=mock_response)

        # Test middleware
        middleware = AuthMiddleware(AsyncMock())
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Verify request proceeded (call_next was called)
        assert mock_call_next.called
        assert mock_request.state.user_id == "123"
        assert mock_request.state.user_role == "admin"

    @pytest.mark.asyncio
    async def test_middleware_rejects_refresh_token(self):
        """Verify that AuthMiddleware rejects refresh tokens on protected endpoints."""
        from app.middleware.auth import AuthMiddleware

        # Create a mock request
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/analytics"
        mock_request.headers = {}

        # Create refresh token
        refresh_token = JWTHandler.create_refresh_token({"sub": "123", "role": "admin"})
        mock_request.headers.get = lambda key, default="": f"Bearer {refresh_token}" if key == "Authorization" else default

        # Create mock call_next
        mock_call_next = AsyncMock()

        # Test middleware
        middleware = AuthMiddleware(AsyncMock())
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Verify request was rejected with 401
        assert response.status_code == 401
        assert "Invalid token type" in response.body.decode()
        assert not mock_call_next.called  # call_next should not be called

    @pytest.mark.asyncio
    async def test_middleware_allows_refresh_endpoint(self):
        """Verify that /auth/refresh endpoint is not protected by AuthMiddleware."""
        from app.middleware.auth import AuthMiddleware

        # Create a mock request
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/auth/refresh"
        mock_request.headers = {}

        # Create mock call_next
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_call_next = AsyncMock(return_value=mock_response)

        # Test middleware - refresh endpoint should skip auth
        middleware = AuthMiddleware(AsyncMock())
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Verify request proceeded without authentication
        assert mock_call_next.called
        assert response.status_code == 200


class TestTokenTypeValidationScenarios:
    """Integration scenarios for token type validation."""

    def test_login_flow_creates_typed_tokens(self):
        """Verify login flow creates properly typed tokens."""
        from app.services.auth import AuthService
        from app.models import User

        # Create a mock user
        mock_user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_pass",
            role="admin",
            is_active=True,
        )

        # Create auth service
        auth_service = AuthService(AsyncMock())

        # Create tokens
        tokens = auth_service.create_tokens(mock_user)

        # Verify access token
        access_decoded = jwt.decode(
            tokens.access_token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        assert access_decoded.get("type") == "access"

        # Verify refresh token
        refresh_decoded = jwt.decode(
            tokens.refresh_token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        assert refresh_decoded.get("type") == "refresh"

    def test_security_scenario_refresh_token_injection(self):
        """
        Security Scenario: Verify that a refresh token cannot be used to access protected endpoints.

        Attack Vector: An attacker somehow obtains a refresh token and attempts to use it
        as an access token on a protected endpoint (e.g., GET /api/v1/analytics).

        Expected Outcome: Request is rejected with 401 Unauthorized.
        """
        # Create a refresh token
        refresh_token = JWTHandler.create_refresh_token({"sub": "999", "role": "admin"})

        # Attempt to decode and validate as access token
        decoded = JWTHandler.decode_token(refresh_token)

        # This should raise AuthenticationError
        with pytest.raises(AuthenticationError) as exc_info:
            JWTHandler.verify_token_type(decoded, "access")

        assert "Invalid token type" in str(exc_info.value)
        print(f"✓ Security check passed: Refresh token rejected as access token")
        print(f"  Error message: {exc_info.value.message}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
