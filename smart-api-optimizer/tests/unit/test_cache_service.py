import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.cache import CacheService

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
class TestCacheService:
    """Test cache service."""

    async def test_cache_key_generation(self):
        """Test cache key generation."""
        service = CacheService()
        
        key1 = service.compute_cache_key(
            endpoint="/api/users",
            method="GET",
            cache_by_user=False
        )
        
        key2 = service.compute_cache_key(
            endpoint="/api/users",
            method="GET",
            cache_by_user=False
        )
        
        assert key1 == key2
        assert key1.startswith("cache:")

    def test_cache_key_different_for_different_params(self):
        """Test cache keys differ for different parameters."""
        service = CacheService()
        
        key1 = service.compute_cache_key(
            endpoint="/api/users/1",
            method="GET",
            cache_by_user=False
        )
        
        key2 = service.compute_cache_key(
            endpoint="/api/users/2",
            method="GET",
            cache_by_user=False
        )
        
        assert key1 != key2

    def test_cache_key_includes_user_id(self):
        """Test cache key includes user ID when specified."""
        service = CacheService()
        
        key_with_user = service.compute_cache_key(
            endpoint="/api/users/1",
            method="GET",
            cache_by_user=True,
            user_id=123
        )
        
        key_without_user = service.compute_cache_key(
            endpoint="/api/users/1",
            method="GET",
            cache_by_user=False
        )
        
        assert key_with_user != key_without_user
        assert "123" in key_with_user

    def test_cache_key_includes_query_params(self):
        """Test cache key includes query params when specified."""
        service = CacheService()
        
        key_with_params = service.compute_cache_key(
            endpoint="/api/users",
            method="GET",
            cache_by_query_params=True,
            query_params={"page": "1", "limit": "10"}
        )
        
        key_without_params = service.compute_cache_key(
            endpoint="/api/users",
            method="GET",
            cache_by_query_params=False
        )
        
        assert key_with_params != key_without_params

    def test_cache_key_includes_headers(self):
        """Test cache key includes headers when specified."""
        service = CacheService()
        
        key_with_headers = service.compute_cache_key(
            endpoint="/api/users",
            method="GET",
            cache_by_headers=True,
            headers={"Accept-Language": "en-US"}
        )
        
        key_without_headers = service.compute_cache_key(
            endpoint="/api/users",
            method="GET",
            cache_by_headers=False
        )
        
        assert key_with_headers != key_without_headers
