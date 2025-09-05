"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestAPIEndpoints:
    """Test API endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["message"] == "Liquid Hive API"
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
    
    def test_version_info(self, client):
        """Test version information endpoint."""
        response = client.get("/version")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "build_date" in data
        assert "build_commit" in data
        assert "build_branch" in data
    
    def test_config_info_debug_mode(self, client):
        """Test configuration info endpoint in debug mode."""
        with pytest.MonkeyPatch().context() as m:
            m.setenv("DEBUG", "true")
            # Reload the app to pick up the new environment variable
            from apps.api.main import app
            test_client = TestClient(app)
            
            response = test_client.get("/config")
            assert response.status_code == 200
            data = response.json()
            assert "app" in data
            assert "api" in data
            assert "features" in data
    
    def test_config_info_production_mode(self, client):
        """Test configuration info endpoint in production mode."""
        response = client.get("/config")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "Configuration endpoint only available in debug mode" in data["error"]


class TestCORS:
    """Test CORS configuration."""
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
    
    def test_cors_preflight(self, client):
        """Test CORS preflight request."""
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            }
        )
        assert response.status_code == 200