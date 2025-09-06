from __future__ import annotations

from typing import Any

import httpx

from .base import ProviderConfig
from src.logging_config import get_logger


class OpenAIProvider:
    def __init__(self, cfg: ProviderConfig, api_key: str | None) -> None:
        self.name = cfg.name
        self.cfg = cfg
        self._key = api_key

    async def generate(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        if not self._key:
            return {
                "provider": self.name,
                "content": f"[stub:openai] {prompt[:64]}...",
                "status": "stub",
            }
        url = self.cfg.base_url.rstrip("/") + "/chat/completions"
        headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}
        payload = {
            "model": self.cfg.model or "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": kwargs.get("max_tokens") or self.cfg.max_tokens or 512,
        }
        async with httpx.AsyncClient(timeout=kwargs.get("timeout", 30)) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"provider": self.name, "content": content, "raw": data}

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy" if bool(self._key) else "stub"}
