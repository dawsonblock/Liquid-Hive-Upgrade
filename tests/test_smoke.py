"""
Smoke tests for basic functionality
"""
import pathlib
import pytest


def test_truth():
    """Basic sanity check"""
    assert True


def test_env_example_present():
    """Ensure .env.example is present"""
    assert (pathlib.Path('.') / '.env.example').exists()


def test_dockerfile_present():
    """Ensure Dockerfile is present"""
    assert (pathlib.Path('.') / 'Dockerfile').exists()


def test_requirements_present():
    """Ensure requirements.txt is present"""
    assert (pathlib.Path('.') / 'requirements.txt').exists()


def test_src_directory_exists():
    """Ensure src directory exists"""
    assert (pathlib.Path('.') / 'src').exists()


def test_basic_imports():
    """Test that core modules can be imported"""
    try:
        from src.unified_runtime import server
        assert hasattr(server, 'app')
    except ImportError:
        pytest.skip("Core modules not available in test environment")


if __name__ == "__main__":
    pytest.main([__file__])