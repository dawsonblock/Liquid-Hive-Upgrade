"""Provider System for LIQUID-HIVE DS-Router
========================================

This module implements the provider abstraction for different LLM backends:
- DeepSeek V3.1 (chat mode)
- DeepSeek V3.1 (thinking mode)
- DeepSeek R1 (reasoning mode)
- Qwen 2.5 7B (local fallback)
"""

from .base_provider import BaseProvider, GenRequest, GenResponse, StreamChunk
from .deepseek_chat import DeepSeekChatProvider
from .deepseek_r1 import DeepSeekR1Provider
from .deepseek_thinking import DeepSeekThinkingProvider
from .hf_qwen_cpu import QwenCPUProvider

__all__ = [
    "BaseProvider",
    "GenRequest",
    "GenResponse",
    "StreamChunk",
    "DeepSeekChatProvider",
    "DeepSeekThinkingProvider",
    "DeepSeekR1Provider",
    "QwenCPUProvider",
]
