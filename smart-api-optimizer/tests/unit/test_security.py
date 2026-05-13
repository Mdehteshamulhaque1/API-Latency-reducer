import pytest
from datetime import datetime, timedelta
from app.core.security import (
    hash_password,
    verify_password,
    create_tokens,
    verify_token,
)

pytestmark = pytest.mark.unit


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 20
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False

    def test_password_hashes_are_unique(self):
        """Test that same password produces different hashes."""
        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2


class TestTokenGeneration:
    """Test JWT token generation and verification."""

    def test_create_tokens(self):
        """Test token creation."""
        user_id = 1
        tokens = create_tokens(user_id)
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"

    def test_verify_access_token(self):
        """Test access token verification."""
        user_id = 1
        tokens = create_tokens(user_id)
        access_token = tokens["access_token"]
        
        payload = verify_token(access_token)
        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"

    def test_verify_refresh_token(self):
        """Test refresh token verification."""
        user_id = 1
        tokens = create_tokens(user_id)
        refresh_token = tokens["refresh_token"]
        
        payload = verify_token(refresh_token)
        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"

    def test_verify_invalid_token(self):
        """Test verification of invalid token."""
        invalid_token = "invalid.token.here"
        
        payload = verify_token(invalid_token)
        assert payload is None

    def test_verify_expired_token(self):
        """Test verification of expired token."""
        from app.core.security import create_access_token
        from datetime import datetime, timedelta
        
        # Create token that expires immediately
        user_id = 1
        expires_delta = timedelta(seconds=-1)  # Already expired
        token = create_access_token(
            data={"sub": str(user_id), "type": "access"},
            expires_delta=expires_delta
        )
        
        payload = verify_token(token)
        assert payload is None
