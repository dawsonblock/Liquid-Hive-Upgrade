from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ProviderConfig:
    name: str
    kind: str
    base_url: str
    api_key_env: str | None = None
    model: str | None = None
    max_tokens: int | None = None
    role: str | None = None
    cost_profile: str | None = None


class OracleProvider(Protocol):
    name: str
    cfg: ProviderConfig

    async def generate(self, prompt: str, **kwargs: Any) -> dict[str, Any]: ...

    async def health(self) -> dict[str, Any]: ...
