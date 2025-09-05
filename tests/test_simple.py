"""Simple tests that don't require complex dependencies."""

import pytest

pytestmark = pytest.mark.unit


def test_basic_math():
    """Test basic math operations."""
    assert 1 + 1 == 2
    assert 2 * 3 == 6
    assert 10 / 2 == 5


def test_string_operations():
    """Test string operations."""
    text = "Hello, World!"
    assert len(text) == 13
    assert text.lower() == "hello, world!"
    assert text.upper() == "HELLO, WORLD!"


def test_list_operations():
    """Test list operations."""
    numbers = [1, 2, 3, 4, 5]
    assert len(numbers) == 5
    assert sum(numbers) == 15
    assert max(numbers) == 5
    assert min(numbers) == 1


def test_dict_operations():
    """Test dictionary operations."""
    data = {"name": "Liquid Hive", "version": "1.0.0"}
    assert "name" in data
    assert data["name"] == "Liquid Hive"
    assert data.get("version") == "1.0.0"


def test_file_structure():
    """Test that key files exist."""
    import os
    
    # Check that key directories exist
    assert os.path.exists("src")
    assert os.path.exists("apps")
    assert os.path.exists("tests")
    assert os.path.exists("infra")
    
    # Check that key files exist
    assert os.path.exists("pyproject.toml")
    assert os.path.exists("requirements.txt")
    assert os.path.exists("docker-compose.yml")
    assert os.path.exists("Makefile")
    assert os.path.exists(".env.example")


def test_import_basic_modules():
    """Test importing basic Python modules."""
    import os
    import sys
    import json
    import pathlib
    
    # These should always work
    assert os is not None
    assert sys is not None
    assert json is not None
    assert pathlib is not None


def test_truth():
    """Basic sanity check."""
    assert True