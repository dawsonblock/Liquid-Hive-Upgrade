"""Base Provider Interface for DS-Router
====================================

Enhanced with streaming support for real-time response generation.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

log = logging.getLogger(__name__)


@dataclass
class GenRequest:
    """Standardized generation request."""

    prompt: str
    system_prompt: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    cot_budget: Optional[int] = None  # For reasoning modes
    metadata: dict[str, Any] = None
    stream: bool = False  # Enable streaming mode

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class GenResponse:
    """Standardized generation response."""

    content: str
    provider: str
    prompt_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    confidence: Optional[float] = None
    logprobs: Optional[list[float]] = None
    metadata: dict[str, Any] = None
    is_complete: bool = True  # For streaming responses

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class StreamChunk:
    """Represents a chunk in a streaming response."""

    content: str
    chunk_id: int = 0
    is_final: bool = False
    provider: str = ""
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseProvider(ABC):
    """Abstract base class for all LLM providers with streaming support."""

    def __init__(self, name: str, config: dict[str, Any] = None):
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{name}")

    @abstractmethod
    async def generate(self, request: GenRequest) -> GenResponse:
        """Generate response from the provider."""

    async def generate_stream(self, request: GenRequest) -> AsyncGenerator[StreamChunk, None]:
        """Generate streaming response from the provider.
        Default implementation falls back to non-streaming.
        Subclasses should override this for true streaming support.
        """
        # Default fallback: generate full response and yield as single chunk
        response = await self.generate(request)

        yield StreamChunk(
            content=response.content,
            chunk_id=0,
            is_final=True,
            provider=self.name,
            metadata={
                "fallback_stream": True,
                "original_latency_ms": response.latency_ms,
                "tokens": response.output_tokens,
            },
        )

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check provider health status."""

    def supports_streaming(self) -> bool:
        """Check if this provider supports native streaming."""
        # Check if the provider has overridden generate_stream
        return (
            hasattr(self.__class__, "generate_stream")
            and self.__class__.generate_stream != BaseProvider.generate_stream
        )

    def _log_generation(
        self, request: GenRequest, response: GenResponse, error: Optional[str] = None
    ):
        """Log generation attempt with structured data."""
        log_data = {
            "provider": self.name,
            "prompt_tokens": response.prompt_tokens if response else 0,
            "output_tokens": response.output_tokens if response else 0,
            "latency_ms": response.latency_ms if response else 0,
            "cost_usd": response.cost_usd if response else 0,
            "confidence": response.confidence if response else None,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if error:
            self.logger.error("Generation failed", extra=log_data)
        else:
            self.logger.info("Generation completed", extra=log_data)

    def _estimate_cost(self, prompt_tokens: int, output_tokens: int) -> float:
        """Estimate cost based on token usage. Override in subclasses."""
        # Default fallback - providers should implement their own pricing
        return 0.0
