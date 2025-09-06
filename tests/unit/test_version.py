"""Unit tests for version endpoints."""

import pytest
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_version_endpoint():
    """Test the /version endpoint."""
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "build_date" in data
    assert "git_commit" in data
    assert data["version"] == "1.0.0"


def test_memory_health_endpoint():
    """Test the memory health endpoint."""
    response = client.get("/api/memory/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "components" in data
    assert "memory_store" in data["components"]


def test_memory_stats_endpoint():
    """Test the memory stats endpoint."""
    response = client.get("/api/memory/stats")
    assert response.status_code == 200
    data = response.json()
    assert "collection_stats" in data
    assert "cache_stats" in data
    assert "provider_status" in data
    assert "timestamp" in data
