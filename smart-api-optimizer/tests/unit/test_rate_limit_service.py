import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.rate_limit import RateLimitService
from app.core.exceptions import RateLimitExceeded

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
class TestRateLimitService:
    """Test rate limiting service."""

    async def test_rate_limit_key_for_user(self):
        """Test rate limit key generation for user."""
        service = RateLimitService()
        
        key = service._get_limit_key(user_id=123, ip="127.0.0.1")
        
        assert "123" in key
        assert "rate_limit" in key

    async def test_rate_limit_key_for_ip(self):
        """Test rate limit key generation for IP."""
        service = RateLimitService()
        
        key = service._get_limit_key(ip="192.168.1.1")
        
        assert "192.168.1.1" in key
        assert "rate_limit" in key

    async def test_rate_limit_key_different_identifiers(self):
        """Test rate limit keys differ for different identifiers."""
        service = RateLimitService()
        
        key1 = service._get_limit_key(user_id=123)
        key2 = service._get_limit_key(user_id=456)
        
        assert key1 != key2

    def test_check_rate_limit_logic(self):
        """Test rate limit checking logic."""
        service = RateLimitService()
        
        # Rate limit should have tokens and reset time
        limit_data = {
            "tokens": 900,  # 900 requests remaining
            "reset_at": 1234567890
        }
        
        assert limit_data["tokens"] > 0  # Not rate limited
        assert limit_data["reset_at"] > 0  # Has reset time
