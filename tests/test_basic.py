"""Basic functionality tests."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    """Test that basic imports work."""
    try:
        from src.config import get_config
        from src.version import get_version
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")


def test_config_basic():
    """Test basic configuration functionality."""
    from src.config import get_config
    
    # This should not raise an exception
    config = get_config()
    assert config is not None


def test_version():
    """Test version functionality."""
    from src.version import get_version
    
    version = get_version()
    assert isinstance(version, str)
    assert len(version) > 0


def test_truth():
    """Basic sanity check."""
    assert True