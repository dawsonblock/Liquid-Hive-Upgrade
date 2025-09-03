from __future__ import annotations

import os
import signal
from typing import Any, Dict
from fastapi import APIRouter, Request, Depends

from oracle.manager import ProviderManager

API_PREFIX = "/api"

router = APIRouter(prefix=f"{API_PREFIX}/admin", tags=["admin"]) 

# Global singleton for simplicity
_pm = ProviderManager()
_providers_cache: Dict[str, Any] = {}
_routing: Dict[str, Any] = {}


def _load_providers() -> None:
    global _providers_cache, _routing
    providers, routing = _pm.load()
    _routing = routing
    # Resolve keys from env. Keys are never returned in API.
    cache: Dict[str, Any] = {}
    for name, cfg in providers.items():
        key = _pm.resolve_api_key(cfg)
        prov = None
        try:
            if cfg.kind == "deepseek":
                from oracle.deepseek import DeepSeekProvider
                prov = DeepSeekProvider(cfg, key)
            elif cfg.kind == "openai":
                from oracle.openai import OpenAIProvider
                prov = OpenAIProvider(cfg, key)
            elif cfg.kind == "anthropic":
                from oracle.anthropic import AnthropicProvider
                prov = AnthropicProvider(cfg, key)
            elif cfg.kind == "qwen":
                from oracle.qwen import QwenProvider
                prov = QwenProvider(cfg, key)
        except Exception:
            prov = None
        if prov is not None:
            cache[name] = prov
    _providers_cache = cache


@router.get("/providers")
async def list_providers() -> Dict[str, Any]:
    if not _providers_cache:
        try:
            _load_providers()
        except Exception as e:
            return {"error": str(e)}
    out = []
    for name, prov in _providers_cache.items():
        cfg = getattr(prov, "cfg")
        out.append({
            "name": name,
            "kind": cfg.kind,
            "base_url": cfg.base_url,
            "model": cfg.model,
            "max_tokens": cfg.max_tokens,
            "role": cfg.role,
            "state": "unknown",  # placeholder for breaker state in future
        })
    return {
        "providers": out,
        "routing": _routing,
    }


@router.post("/reload-providers")
async def reload_providers(request: Request) -> Dict[str, Any]:
    # Optional simple admin token check
    admin_token = os.getenv("ADMIN_TOKEN")
    if admin_token:
        header_token = request.headers.get("x-admin-token") or request.headers.get("X-Admin-Token")
        if header_token != admin_token:
            return {"error": "Unauthorized"}
    try:
        _load_providers()
        # Optionally broadcast SIGHUP to trigger reload in other processes if needed
        try:
            os.kill(os.getpid(), signal.SIGHUP)
        except Exception:
            pass
        return {"status": "reloaded", "providers": list(_providers_cache.keys())}
    except Exception as e:
        return {"error": str(e)}