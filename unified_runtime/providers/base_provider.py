"""
Base Provider Interface for DS-Router
====================================

Enhanced with streaming support for real-time response generation.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
import logging
import time

log = logging.getLogger(__name__)

@dataclass
class GenRequest:
    """Standardized generation request."""
    prompt: str
    system_prompt: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    cot_budget: Optional[int] = None  # For reasoning modes
    metadata: Dict[str, Any] = None
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
    logprobs: Optional[List[float]] = None
    metadata: Dict[str, Any] = None
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
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class BaseProvider(ABC):
    """Abstract base class for all LLM providers."""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
    @abstractmethod
    async def generate(self, request: GenRequest) -> GenResponse:
        """Generate response from the provider."""
        pass
        
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check provider health status."""
        pass
        
    def _log_generation(self, request: GenRequest, response: GenResponse, error: Optional[str] = None):
        """Log generation attempt with structured data."""
        log_data = {
            "provider": self.name,
            "prompt_tokens": response.prompt_tokens if response else 0,
            "output_tokens": response.output_tokens if response else 0,
            "latency_ms": response.latency_ms if response else 0,
            "cost_usd": response.cost_usd if response else 0,
            "confidence": response.confidence if response else None,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if error:
            self.logger.error("Generation failed", extra=log_data)
        else:
            self.logger.info("Generation completed", extra=log_data)
            
    def _estimate_cost(self, prompt_tokens: int, output_tokens: int) -> float:
        """Estimate cost based on token usage. Override in subclasses."""
        # Default fallback - providers should implement their own pricing
        return 0.0