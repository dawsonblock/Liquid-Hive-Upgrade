from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol


@dataclass
class ProviderConfig:
    name: str
    kind: str
    base_url: str
    api_key_env: Optional[str] = None
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    role: Optional[str] = None
    cost_profile: Optional[str] = None


class OracleProvider(Protocol):
    name: str
    cfg: ProviderConfig

    async def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        ...

    async def health(self) -> Dict[str, Any]:
        ...