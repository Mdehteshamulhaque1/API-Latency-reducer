import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert "timestamp" in response.json()


class TestAnalyticsEndpoints:
    """Test analytics endpoints."""

    def test_get_analytics_summary_unauthorized(self, client: TestClient):
        """Test analytics summary without authentication."""
        response = client.get("/api/v1/analytics/summary")
        
        assert response.status_code == 401

    def test_get_analytics_summary_authorized(
        self, client: TestClient, auth_headers
    ):
        """Test analytics summary with authentication."""
        response = client.get(
            "/api/v1/analytics/summary?hours=24",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        assert "cache_hit_rate" in data
        assert "avg_response_time_ms" in data
        assert "error_rate" in data

    def test_get_analytics_summary_invalid_hours(
        self, client: TestClient, auth_headers
    ):
        """Test analytics summary with invalid hours parameter."""
        response = client.get(
            "/api/v1/analytics/summary?hours=-1",
            headers=auth_headers
        )
        
        assert response.status_code == 422

    def test_get_endpoint_logs_unauthorized(self, client: TestClient):
        """Test endpoint logs without authentication."""
        response = client.get("/api/v1/analytics/endpoints/test-endpoint")
        
        assert response.status_code == 401

    def test_get_endpoint_logs_authorized(
        self, client: TestClient, auth_headers
    ):
        """Test endpoint logs with authentication."""
        response = client.get(
            "/api/v1/analytics/endpoints/test-endpoint?hours=24",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or data == []


class TestRulesEndpoints:
    """Test cache rules endpoints."""

    def test_get_rules_unauthorized(self, client: TestClient):
        """Test getting rules without authentication."""
        response = client.get("/api/v1/rules")
        
        assert response.status_code == 401

    def test_get_rules_authorized(self, client: TestClient, auth_headers):
        """Test getting rules with authentication."""
        response = client.get("/api/v1/rules", headers=auth_headers)
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_rule_unauthorized(self, client: TestClient):
        """Test creating rule without authentication."""
        response = client.post(
            "/api/v1/rules",
            json={
                "endpoint_pattern": "/api/users/*",
                "ttl": 3600,
                "enabled": True
            }
        )
        
        assert response.status_code == 401

    def test_create_rule_authorized(self, client: TestClient, auth_headers):
        """Test creating rule with authentication."""
        response = client.post(
            "/api/v1/rules",
            headers=auth_headers,
            json={
                "endpoint_pattern": "/api/users/*",
                "ttl": 3600,
                "enabled": True,
                "cache_by_user": False,
                "cache_by_query_params": False,
                "cache_by_headers": False
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["endpoint_pattern"] == "/api/users/*"
        assert data["ttl"] == 3600
        assert data["enabled"] is True

    def test_create_rule_invalid_ttl(self, client: TestClient, auth_headers):
        """Test creating rule with invalid TTL."""
        response = client.post(
            "/api/v1/rules",
            headers=auth_headers,
            json={
                "endpoint_pattern": "/api/users/*",
                "ttl": -100,
                "enabled": True
            }
        )
        
        assert response.status_code == 422

    def test_get_rule_by_id_unauthorized(self, client: TestClient):
        """Test getting rule by ID without authentication."""
        response = client.get("/api/v1/rules/1")
        
        assert response.status_code == 401

    def test_get_rule_by_id_not_found(self, client: TestClient, auth_headers):
        """Test getting non-existent rule."""
        response = client.get("/api/v1/rules/99999", headers=auth_headers)
        
        assert response.status_code == 404

    def test_update_rule_unauthorized(self, client: TestClient):
        """Test updating rule without authentication."""
        response = client.put(
            "/api/v1/rules/1",
            json={"ttl": 7200, "enabled": False}
        )
        
        assert response.status_code == 401

    def test_delete_rule_unauthorized(self, client: TestClient):
        """Test deleting rule without authentication."""
        response = client.delete("/api/v1/rules/1")
        
        assert response.status_code == 401

    def test_delete_rule_not_found(self, client: TestClient, auth_headers):
        """Test deleting non-existent rule."""
        response = client.delete("/api/v1/rules/99999", headers=auth_headers)
        
        assert response.status_code == 404
