from __future__ import annotations

import time
from typing import Any

from .providers.base_provider import BaseProvider, GenRequest, GenResponse


class OracleToBaseAdapter(BaseProvider):
    """Adapts an oracle.* provider (generate(prompt)) to BaseProvider interface."""

    def __init__(self, name: str, oracle_provider: Any):
        super().__init__(name, {})
        self._oracle = oracle_provider

    async def generate(self, request: GenRequest) -> GenResponse:
        start = time.perf_counter()
        try:
            res: dict[str, Any] = await self._oracle.generate(
                request.prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                cot_budget=request.cot_budget,
            )
            latency_ms = (time.perf_counter() - start) * 1000.0
            content = str(res.get("content", ""))
            return GenResponse(
                content=content,
                provider=self.name,
                prompt_tokens=0,
                output_tokens=len(content.split()),
                latency_ms=latency_ms,
                cost_usd=0.0,
                metadata={"oracle": True, "raw_present": "raw" in res},
            )
        except Exception as e:
            raise e

    async def health_check(self) -> dict[str, Any]:
        try:
            h = await self._oracle.health()
            return {"status": h.get("status", "unknown")}
        except Exception as e:
            return {"status": "error", "error": str(e)}
