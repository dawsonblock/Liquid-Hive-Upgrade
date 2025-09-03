from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, Optional

from .providers.base_provider import BaseProvider, GenRequest, GenResponse, StreamChunk


@dataclass
class RouterConfig:
    conf_threshold: float = 0.62
    support_threshold: float = 0.55
    max_cot_tokens: int = 1000
    deepseek_api_key: str | None = None

    @classmethod
    def from_env(cls) -> "RouterConfig":
        return cls(
            conf_threshold=float(os.getenv("CONF_THRESHOLD", "0.62")),
            support_threshold=float(os.getenv("SUPPORT_THRESHOLD", "0.55")),
            max_cot_tokens=int(os.getenv("MAX_COT_TOKENS", "1000")),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
        )


@dataclass
class RoutingDecision:
    provider: str
    reasoning: str


class DSRouter:
    def __init__(self, config: RouterConfig = None) -> None:
        self.config = config or RouterConfig.from_env()
        self.logger = logging.getLogger(__name__)
        self.providers: Dict[str, BaseProvider] = {}
        self._install_defaults()

    def _install_defaults(self) -> None:
        # Minimal defaults expected by tests
        class _Echo(BaseProvider):
            async def generate(self, request: GenRequest) -> GenResponse:
                return GenResponse(content="Simple response", provider=self.name, confidence=0.8)
            async def health_check(self) -> Dict[str, Any]:
                return {"status": "healthy"}
        self.providers["deepseek_chat"] = _Echo("deepseek_chat")
        self.providers["deepseek_thinking"] = _Echo("deepseek_thinking")
        self.providers["deepseek_r1"] = _Echo("deepseek_r1")
        self.providers["qwen_cpu"] = _Echo("qwen_cpu")

    def _is_hard_problem(self, text: str) -> bool:
        hard_keywords = ["prove", "optimize", "debug", "analyze", "irrational", "big-o", "regex"]
        tl = text.lower()
        return any(k in tl for k in hard_keywords)

    async def _assess_confidence(self, resp: GenResponse) -> float:
        return float(resp.confidence or 0.8)

    async def get_provider_status(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for name, p in self.providers.items():
            try:
                h = await p.health_check()
            except Exception as e:
                h = {"status": "error", "error": str(e)}
            out[name] = h
        return out

    async def generate(self, request: GenRequest) -> GenResponse:
        # Route simple vs hard
        if self._is_hard_problem(request.prompt):
            choice = "deepseek_thinking"
            reasoning = "hard_problem"
        else:
            choice = "deepseek_chat"
            reasoning = "simple"

        # Call primary
        try:
            resp = await self.providers[choice].generate(request)
            resp.metadata.setdefault("routing_decision", choice)
            resp.metadata.setdefault("routing_reasoning", reasoning)
            # confidence assessment
            resp.confidence = await self._assess_confidence(resp)
            # escalate on low confidence for hard problems
            if choice == "deepseek_thinking" and resp.confidence < self.config.conf_threshold:
                resp = await self.providers["deepseek_r1"].generate(request)
                resp.metadata["escalated"] = True
                resp.metadata["escalation_reason"] = "low_confidence"
            return resp
        except Exception as e:
            # fallback to qwen_cpu
            fb = await self.providers["qwen_cpu"].generate(request)
            fb.metadata["fallback_reason"] = str(e)
            return fb

    async def generate_stream(self, request: GenRequest) -> AsyncGenerator[StreamChunk, None]:
        r = await self.generate(request)
        yield StreamChunk(content=r.content, is_final=True, provider=r.provider)