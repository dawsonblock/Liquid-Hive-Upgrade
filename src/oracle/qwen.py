from __future__ import annotations

from typing import Any, Optional

import httpx

from .base import ProviderConfig


class QwenProvider:
    def __init__(self, cfg: ProviderConfig, api_key: Optional[str]) -> None:
        self.name = cfg.name
        self.cfg = cfg
        self._key = api_key

    async def generate(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        if not self._key:
            return {
                "provider": self.name,
                "content": f"[stub:qwen] {prompt[:64]}...",
                "status": "stub",
            }
        url = self.cfg.base_url.rstrip("/") + "/chat/completions"
        headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}
        payload = {
            "model": self.cfg.model or "qwen2.5-7b-instruct",
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
