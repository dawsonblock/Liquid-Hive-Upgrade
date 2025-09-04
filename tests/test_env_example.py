#!/usr/bin/env python3
"""
Test suite for environment variable examples and configurations.
Validates that .env.example contains all necessary variables.
"""

import os
import re
from pathlib import Path


def test_env_example_exists():
    """Test that .env.example file exists."""
    env_example_path = Path(__file__).parent.parent / ".env.example"
    assert env_example_path.exists(), ".env.example file should exist"


def test_env_example_has_required_variables():
    """Test that .env.example contains all required environment variables."""
    env_example_path = Path(__file__).parent.parent / ".env.example"

    with open(env_example_path, "r") as f:
        content = f.read()

    # Required variables that should be documented
    required_vars = [
        "MONGO_URL",
        "REDIS_URL",
        "ADMIN_TOKEN",
        "ENABLE_PLANNER",
        "ENABLE_ARENA",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "DEEPSEEK_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ]

    for var in required_vars:
        assert (
            var in content
        ), f"Required environment variable {var} should be documented in .env.example"


def test_env_example_format():
    """Test that .env.example follows proper format conventions."""
    env_example_path = Path(__file__).parent.parent / ".env.example"

    with open(env_example_path, "r") as f:
        lines = f.readlines()

    # Check for proper formatting
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue  # Skip empty lines and comments

        # Should match VAR=value or VAR= pattern
        assert re.match(
            r"^[A-Z_][A-Z0-9_]*=.*$", line
        ), f"Line {line_num} should follow VAR=value format: {line}"


def test_sensitive_variables_not_exposed():
    """Test that sensitive variables don't contain real values."""
    env_example_path = Path(__file__).parent.parent / ".env.example"

    with open(env_example_path, "r") as f:
        content = f.read()

    # Patterns that suggest real API keys/secrets
    sensitive_patterns = [
        r"sk-[a-zA-Z0-9]{20,}",  # OpenAI API key pattern
        r"claude-[a-zA-Z0-9]{20,}",  # Anthropic API key pattern
        r"Bearer [a-zA-Z0-9]{20,}",  # Bearer token pattern
        r"mongodb://[^:]+:[^@]+@",  # MongoDB with real credentials
    ]

    for pattern in sensitive_patterns:
        assert not re.search(
            pattern, content
        ), f"Found potential real secret matching pattern: {pattern}"


def test_database_urls_are_examples():
    """Test that database URLs are example values, not real endpoints."""
    env_example_path = Path(__file__).parent.parent / ".env.example"

    with open(env_example_path, "r") as f:
        content = f.read()

    # Should contain example/placeholder values
    example_indicators = [
        "localhost",
        "example.com",
        "your-",
        "REPLACE_ME",
        "changeme",
        "mongodb:",
        "redis:",
        "neo4j:",
        "http://",
    ]

    # Extract URLs from the content
    url_pattern = r"URL=([^\n\r]+)"
    urls = re.findall(url_pattern, content)

    for url in urls:
        has_example_indicator = any(indicator in url for indicator in example_indicators)
        assert has_example_indicator, f"URL should contain example placeholder: {url}"


if __name__ == "__main__":
    test_env_example_exists()
    test_env_example_has_required_variables()
    test_env_example_format()
    test_sensitive_variables_not_exposed()
    test_database_urls_are_examples()
    print("✅ All environment variable tests passed!")
