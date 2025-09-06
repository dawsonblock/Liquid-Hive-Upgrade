"""Unit tests for memory endpoints."""

import pytest
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_memory_init():
    """Test memory system initialization."""
    response = client.post("/api/memory/init")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "initialized"
    assert data["collection_created"] is True


def test_memory_ingest():
    """Test memory ingestion."""
    request_data = {
        "text": "This is a test memory",
        "tags": ["test", "example"],
        "source": "test",
        "quality": 0.8,
        "metadata": {"test": True}
    }

    response = client.post("/api/memory/ingest", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ingested"
    assert "id" in data
    assert data["embedding_dimension"] == 384
    assert data["duplicate_skipped"] is False


def test_memory_query():
    """Test memory querying."""
    # First ingest some data
    request_data = {
        "text": "This is a test memory for querying",
        "tags": ["test", "query"],
        "source": "test"
    }
    client.post("/api/memory/ingest", json=request_data)

    # Then query it
    query_data = {
        "query": "test memory",
        "limit": 5
    }

    response = client.post("/api/memory/query", json=query_data)
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "query_time_ms" in data
    assert "total_results" in data
    assert data["cached"] is False


def test_memory_query_empty():
    """Test memory query with no results."""
    query_data = {
        "query": "nonexistent content",
        "limit": 5
    }

    response = client.post("/api/memory/query", json=query_data)
    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] == 0
    assert data["results"] == []
