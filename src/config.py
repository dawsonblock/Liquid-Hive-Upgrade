"""Centralized configuration management for Liquid Hive."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from src.logging_config import get_logger


class DatabaseConfig(BaseSettings):
    """Database configuration."""
    
    url: str = Field(default="sqlite:///./liquid_hive.db", env="DATABASE_URL")
    echo: bool = Field(default=False, env="DATABASE_ECHO")
    pool_size: int = Field(default=5, env="DATABASE_POOL_SIZE")
    max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    pool_recycle: int = Field(default=3600, env="DATABASE_POOL_RECYCLE")


class RedisConfig(BaseSettings):
    """Redis configuration."""
    
    url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    max_connections: int = Field(default=10, env="REDIS_MAX_CONNECTIONS")
    socket_timeout: int = Field(default=5, env="REDIS_SOCKET_TIMEOUT")
    socket_connect_timeout: int = Field(default=5, env="REDIS_SOCKET_CONNECT_TIMEOUT")
    retry_on_timeout: bool = Field(default=True, env="REDIS_RETRY_ON_TIMEOUT")


class APIConfig(BaseSettings):
    """API configuration."""
    
    host: str = Field(default="0.0.0.0", env="API_HOST")
    port: int = Field(default=8000, env="API_PORT")
    workers: int = Field(default=1, env="API_WORKERS")
    reload: bool = Field(default=False, env="API_RELOAD")
    log_level: str = Field(default="info", env="API_LOG_LEVEL")
    cors_origins: list[str] = Field(default=["http://localhost:3000"], env="API_CORS_ORIGINS")


class SecurityConfig(BaseSettings):
    """Security configuration."""
    
    secret_key: str = Field(default="dev-secret-key-change-in-production", env="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    algorithm: str = Field(default="HS256", env="SECURITY_ALGORITHM")
    password_min_length: int = Field(default=8, env="PASSWORD_MIN_LENGTH")
    max_login_attempts: int = Field(default=5, env="MAX_LOGIN_ATTEMPTS")
    lockout_duration_minutes: int = Field(default=15, env="LOCKOUT_DURATION_MINUTES")


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    
    level: str = Field(default="INFO", env="LOG_LEVEL")
    format: str = Field(default="json", env="LOG_FORMAT")
    handlers: list[Dict[str, Any]] = Field(default_factory=list)


class MonitoringConfig(BaseSettings):
    """Monitoring configuration."""
    
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    prometheus_port: int = Field(default=9090, env="PROMETHEUS_PORT")


class FeaturesConfig(BaseSettings):
    """Feature flags configuration."""
    
    rag_enabled: bool = Field(default=True, env="RAG_ENABLED")
    agent_autonomy: bool = Field(default=True, env="AGENT_AUTONOMY")
    swarm_protocol: bool = Field(default=True, env="SWARM_PROTOCOL")
    safety_checks: bool = Field(default=True, env="SAFETY_CHECKS")
    confidence_modeling: bool = Field(default=True, env="CONFIDENCE_MODELING")
    debug_mode: bool = Field(default=False, env="DEBUG_MODE")
    mock_external_services: bool = Field(default=False, env="MOCK_EXTERNAL_SERVICES")


class AppConfig(BaseSettings):
    """Main application configuration."""
    
    name: str = Field(default="Liquid Hive", env="APP_NAME")
    version: str = Field(default="0.1.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="production", env="ENVIRONMENT")
    
    # Sub-configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        allowed = {"development", "staging", "production", "test"}
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


class ConfigLoader:
    """Configuration loader with environment-specific overrides."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration loader."""
        self.config_dir = config_dir or Path(__file__).parent.parent.parent / "configs"
        self._config: Optional[AppConfig] = None
    
    def load_config(self, environment: Optional[str] = None) -> AppConfig:
        """Load configuration with environment-specific overrides."""
        if self._config is not None:
            return self._config
        
        # Determine environment
        env = environment or os.getenv("APP_ENV", "production")
        
        # Load base configuration
        base_config = self._load_yaml_config("base/settings.yaml")
        
        # Load environment-specific overrides
        env_config = self._load_yaml_config(f"{env}/settings.yaml")
        
        # Merge configurations
        merged_config = self._merge_configs(base_config, env_config)
        
        # Create Pydantic model
        self._config = AppConfig(**merged_config)
        return self._config
    
    def _load_yaml_config(self, config_path: str) -> Dict[str, Any]:
        """Load YAML configuration file."""
        full_path = self.config_dir / config_path
        if not full_path.exists():
            return {}
        
        with open(full_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result


# Global configuration instance
_config_loader = ConfigLoader()


def get_config(environment: Optional[str] = None) -> AppConfig:
    """Get application configuration."""
    return _config_loader.load_config(environment)


# Convenience function for common use
config = get_config()