"""Unit tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Liquid Hive API"
    assert data["version"] == "1.0.0"


def test_health_endpoint():
    """Test the health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"


def test_healthz_endpoint():
    """Test the healthz endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"


def test_version_endpoint():
    """Test the version endpoint."""
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "1.0.0"
    assert "build_date" in data
    assert "git_commit" in data


def test_memory_health_endpoint():
    """Test the memory health endpoint."""
    response = client.get("/api/memory/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "components" in data


def test_memory_stats_endpoint():
    """Test the memory stats endpoint."""
    response = client.get("/api/memory/stats")
    assert response.status_code == 200
    data = response.json()
    assert "collection_stats" in data
    assert "timestamp" in data


def test_memory_ingest_endpoint():
    """Test the memory ingest endpoint."""
    request_data = {
        "text": "Test memory content",
        "tags": ["test"],
        "source": "test",
        "quality": 0.8
    }
    response = client.post("/api/memory/ingest", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ingested"
    assert "id" in data


def test_memory_query_endpoint():
    """Test the memory query endpoint."""
    request_data = {
        "query": "test",
        "limit": 5
    }
    response = client.post("/api/memory/query", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "query_time_ms" in data
