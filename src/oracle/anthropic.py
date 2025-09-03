from __future__ import annotations

import httpx
from typing import Any, Dict, Optional
from .base import ProviderConfig


class AnthropicProvider:
    def __init__(self, cfg: ProviderConfig, api_key: Optional[str]) -> None:
        self.name = cfg.name
        self.cfg = cfg
        self._key = api_key

    async def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        if not self._key:
            return {"provider": self.name, "content": f"[stub:anthropic] {prompt[:64]}...", "status": "stub"}
        # Anthropics' Messages API
        url = self.cfg.base_url.rstrip("/") + "/messages"
        headers = {
            "x-api-key": self._key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.cfg.model or "claude-3-5-sonnet",
            "max_tokens": kwargs.get("max_tokens") or self.cfg.max_tokens or 512,
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient(timeout=kwargs.get("timeout", 30)) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            # Simplified content extraction
            content = ""
            try:
                content = data.get("content", [{}])[0].get("text", "")
            except Exception:
                pass
            return {"provider": self.name, "content": content, "raw": data}

    async def health(self) -> Dict[str, Any]:
        return {"status": "healthy" if bool(self._key) else "stub"}