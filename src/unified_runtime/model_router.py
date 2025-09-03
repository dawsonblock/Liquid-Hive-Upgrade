from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Dict, Optional

from .providers.base_provider import BaseProvider, GenRequest, GenResponse, StreamChunk


@dataclass
class RouterConfig:
    conf_threshold: float = 0.5
    support_threshold: float = 0.5
    max_cot_tokens: int = 2048
    max_oracle_tokens_per_day: int = 1_000_000
    max_oracle_usd_per_day: float = 1000.0
    provider_timeout_seconds: int = 30

    @classmethod
    def from_env(cls) -> "RouterConfig":
        return cls(
            conf_threshold=float(os.getenv("CONF_THRESHOLD", "0.5")),
            support_threshold=float(os.getenv("SUPPORT_THRESHOLD", "0.5")),
            max_cot_tokens=int(os.getenv("MAX_COT_TOKENS", "2048")),
            max_oracle_tokens_per_day=int(os.getenv("MAX_ORACLE_TOKENS_PER_DAY", "1000000")),
            max_oracle_usd_per_day=float(os.getenv("MAX_ORACLE_USD_PER_DAY", "1000")),
            provider_timeout_seconds=int(os.getenv("PROVIDER_TIMEOUT_SECONDS", "30")),
        )


class _BudgetTracker:
    def __init__(self, cfg: RouterConfig) -> None:
        self.cfg = cfg
        self._fallback_tokens = 0
        self._fallback_usd = 0.0

    def _daily_key(self, tenant: Optional[str]) -> str:
        t = (tenant or "global").replace(":", "_")
        day = datetime.utcnow().strftime("%Y-%m-%d")
        return f"lh:budget:{t}:{day}"

    async def check_budget(self, tenant: Optional[str] = None) -> Dict[str, Any]:
        exceeded = (
            self._fallback_tokens >= self.cfg.max_oracle_tokens_per_day or
            self._fallback_usd >= self.cfg.max_oracle_usd_per_day
        )
        tomorrow = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return {
            "exceeded": exceeded,
            "tokens_used": int(self._fallback_tokens),
            "usd_spent": float(self._fallback_usd),
            "next_reset_utc": tomorrow.strftime("%Y-%m-%d %H:%M:%S UTC"),
        }

    async def record_usage(self, resp: GenResponse, tenant: Optional[str] = None) -> None:
        tokens = int((resp.prompt_tokens or 0) + (resp.output_tokens or 0))
        cost = float(resp.cost_usd or 0.0)
        self._fallback_tokens += tokens
        self._fallback_usd += cost

    async def reset_daily_budget(self, tenant: Optional[str] = None) -> Dict[str, Any]:
        self._fallback_tokens = 0
        self._fallback_usd = 0.0
        return {"status": "fallback_reset"}


class _EchoProvider(BaseProvider):
    async def generate(self, request: GenRequest) -> GenResponse:
        content = (request.system_prompt or "") + "\n" + (request.prompt or "")
        return GenResponse(
            content=content.strip(),
            provider=self.name,
            prompt_tokens=len((request.prompt or "").split()),
            output_tokens=len(content.split()),
            latency_ms=1.0,
            cost_usd=0.0,
            metadata={"stub": True},
        )

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "ok"}


class DSRouter:
    def __init__(self, config: RouterConfig = None) -> None:
        self.config = config or RouterConfig.from_env()
        self.logger = logging.getLogger(__name__)

        # Providers
        self.providers: Dict[str, BaseProvider] = {}
        self._initialize_providers()

        # Budgets
        self._budget_tracker = _BudgetTracker(self.config)

        # Tracer optional
        try:
            from .observability import get_tracer  # type: ignore
            self._tracer = get_tracer()
        except Exception:
            self._tracer = None

    def _initialize_providers(self) -> None:
        # Install a simple echo provider and a qwen_cpu placeholder
        self.providers["default"] = _EchoProvider("default")
        self.providers["qwen_cpu"] = _EchoProvider("qwen_cpu")
        self.logger.info("Initialized DSRouter providers: %s", list(self.providers.keys()))

    def refresh_config_from_env(self) -> None:
        self.config = RouterConfig.from_env()
        self.logger.info("Router config refreshed from env")

    async def get_provider_status(self) -> Dict[str, Any]:
        out = []
        for name, prov in self.providers.items():
            try:
                h = await prov.health_check()
            except Exception as e:
                h = {"status": "error", "error": str(e)}
            out.append({"name": name, **h})
        return {"providers": out}

    async def generate(self, request: GenRequest) -> GenResponse:
        # Budget check
        try:
            tenant = None
        except Exception:
            tenant = None
        budget = await self._budget_tracker.check_budget(tenant)
        if budget.get("exceeded"):
            return GenResponse(content="budget_exceeded", provider="budget", metadata={"blocked": True})

        provider = self.providers.get("default") or next(iter(self.providers.values()))
        if self._tracer:
            with self._tracer.start_as_current_span("provider.generate", attributes={"provider.name": provider.name}):
                resp = await provider.generate(request)
        else:
            resp = await provider.generate(request)

        await self._budget_tracker.record_usage(resp, tenant)
        return resp

    async def generate_stream(self, request: GenRequest) -> AsyncGenerator[StreamChunk, None]:
        # Default stream as single chunk
        resp = await self.generate(request)
        yield StreamChunk(content=resp.content, is_final=True, provider=resp.provider)