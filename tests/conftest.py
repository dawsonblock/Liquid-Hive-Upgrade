"""Pytest configuration and shared fixtures."""

import os
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

# Set test environment
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"

@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    with patch("redis.Redis") as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        mock_instance.ping.return_value = True
        mock_instance.get.return_value = None
        mock_instance.set.return_value = True
        yield mock_instance

@pytest.fixture
def mock_database():
    """Mock database for testing."""
    with patch("sqlalchemy.create_engine") as mock:
        yield mock

@pytest.fixture
def test_client():
    """Create test client for API testing."""
    from apps.api.main import app
    return TestClient(app)

@pytest.fixture(autouse=True)
def clean_env():
    """Clean environment variables after each test."""
    yield
    # Clean up any test-specific environment variables
    test_vars = [k for k in os.environ.keys() if k.startswith("TEST_")]
    for var in test_vars:
        del os.environ[var]