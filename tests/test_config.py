"""Tests for configuration management."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from src.config import AppConfig, ConfigLoader, get_config

pytestmark = pytest.mark.unit


class TestConfigLoader:
    """Test configuration loader functionality."""
    
    def test_load_base_config(self):
        """Test loading base configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            base_config_path = config_dir / "base" / "settings.yaml"
            base_config_path.parent.mkdir(parents=True)
            
            base_config = {
                "app": {
                    "name": "Test App",
                    "version": "1.0.0",
                    "debug": False,
                },
                "api": {
                    "host": "0.0.0.0",
                    "port": 8000,
                },
            }
            
            with open(base_config_path, "w") as f:
                yaml.dump(base_config, f)
            
            loader = ConfigLoader(config_dir)
            config = loader.load_config("base")
            
            assert config.app.name == "Test App"
            assert config.app.version == "1.0.0"
            assert config.app.debug is False
            assert config.api.host == "0.0.0.0"
            assert config.api.port == 8000
    
    def test_load_with_environment_override(self):
        """Test loading configuration with environment overrides."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # Create base config
            base_config_path = config_dir / "base" / "settings.yaml"
            base_config_path.parent.mkdir(parents=True)
            base_config = {
                "app": {"debug": False},
                "api": {"port": 8000},
            }
            with open(base_config_path, "w") as f:
                yaml.dump(base_config, f)
            
            # Create dev config
            dev_config_path = config_dir / "dev" / "settings.yaml"
            dev_config_path.parent.mkdir(parents=True)
            dev_config = {
                "app": {"debug": True},
                "api": {"port": 8001},
            }
            with open(dev_config_path, "w") as f:
                yaml.dump(dev_config, f)
            
            loader = ConfigLoader(config_dir)
            config = loader.load_config("dev")
            
            assert config.app.debug is True
            assert config.api.port == 8001
    
    def test_environment_variable_override(self):
        """Test that environment variables override config values."""
        with patch.dict(os.environ, {
            "API_HOST": "192.168.1.100",
            "API_PORT": "9000",
            "DEBUG": "true",
        }):
            config = get_config()
            
            assert config.api.host == "192.168.1.100"
            assert config.api.port == 9000
            assert config.debug is True


class TestAppConfig:
    """Test application configuration model."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = AppConfig()
        
        assert config.name == "Liquid Hive"
        assert config.version == "0.1.0"
        assert config.debug is False
        assert config.environment == "production"
        assert config.api.host == "0.0.0.0"
        assert config.api.port == 8000
    
    def test_environment_validation(self):
        """Test environment validation."""
        with pytest.raises(ValueError, match="Environment must be one of"):
            AppConfig(environment="invalid")
        
        # Valid environments should work
        for env in ["development", "staging", "production", "test"]:
            config = AppConfig(environment=env)
            assert config.environment == env
    
    def test_security_config_defaults(self):
        """Test security configuration defaults."""
        config = AppConfig()
        
        assert config.security.algorithm == "HS256"
        assert config.security.password_min_length == 8
        assert config.security.max_login_attempts == 5
        assert config.security.lockout_duration_minutes == 15
    
    def test_features_config_defaults(self):
        """Test features configuration defaults."""
        config = AppConfig()
        
        assert config.features.rag_enabled is True
        assert config.features.agent_autonomy is True
        assert config.features.swarm_protocol is True
        assert config.features.safety_checks is True
        assert config.features.confidence_modeling is True
        assert config.features.debug_mode is False
        assert config.features.mock_external_services is False