from __future__ import annotations

import os
from typing import Any
from src.logging_config import get_logger

try:
    import yaml  # type: ignore
except Exception:  # Fallback tiny parser for simple YAML-like (very limited)
    yaml = None  # type: ignore

from .base import ProviderConfig


class ProviderManager:
    def __init__(self, config_path: str = "/app/config/providers.yaml") -> None:
        self.config_path = config_path
        self.routing: dict[str, Any] = {}
        self.providers_cfg: dict[str, ProviderConfig] = {}
        self.policies: dict[str, Any] = {}
        self.admin: dict[str, Any] = {}

    def _load_yaml(self) -> dict[str, Any]:
        if yaml is None:
            raise RuntimeError("PyYAML not installed; cannot load providers.yaml")
        with open(self.config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def load(self) -> tuple[dict[str, ProviderConfig], dict[str, Any]]:
        data = self._load_yaml()
        self.routing = data.get("routing", {})
        self.policies = data.get("policies", {})
        self.admin = data.get("admin", {})

        providers: dict[str, ProviderConfig] = {}
        for name, cfg in (data.get("providers", {}) or {}).items():
            providers[name] = ProviderConfig(
                name=name,
                kind=str(cfg.get("kind")),
                base_url=str(cfg.get("base_url")),
                api_key_env=cfg.get("api_key_env"),
                model=cfg.get("model"),
                max_tokens=cfg.get("max_tokens"),
                role=cfg.get("role"),
                cost_profile=cfg.get("cost_profile"),
            )
        self.providers_cfg = providers
        return providers, self.routing

    def resolve_api_key(self, cfg: ProviderConfig) -> str | None:
        if not cfg.api_key_env:
            return None
        # Environment first. External secrets manager integration can be added here
        val = os.getenv(cfg.api_key_env)
        return val
