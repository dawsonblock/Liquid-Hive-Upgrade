"""
DeepSeek V3.1 Chat Provider with Streaming Support
=================================================
"""

from __future__ import annotations

import asyncio
import json
import os
import random
from typing import Any, AsyncGenerator, Dict, Optional, cast

from .base_provider import BaseProvider, GenRequest, GenResponse, StreamChunk

try:
    import httpx
except ImportError:
    httpx = None


class DeepSeekChatProvider(BaseProvider):
    """DeepSeek V3.1 non-thinking mode provider."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        super().__init__("deepseek_chat", cfg)
        self.api_key = cfg.get("api_key") or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.model = cfg.get("model", "deepseek-chat")
        self.timeout = cfg.get("timeout", 120)
        self.max_retries = cfg.get("max_retries", 3)

        # DeepSeek V3 pricing (approximate)
        self.input_cost_per_1k = 0.00014  # $0.14 per 1K input tokens
        self.output_cost_per_1k = 0.00028  # $0.28 per 1K output tokens

    async def generate(self, request: GenRequest) -> GenResponse:
        """Generate response using DeepSeek chat mode."""
        start_time = asyncio.get_event_loop().time()

        if not self.api_key or httpx is None:
            return self._fallback_response(request, start_time)

        messages: list[dict[str, Any]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": request.max_tokens or 2048,
            "temperature": request.temperature or 0.7,
            "stream": bool(request.stream),
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error: Optional[str] = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:  # type: ignore[reportUnknownMemberType]
                    response = await client.post(
                        self.base_url, json=payload, headers=headers
                    )
                    response.raise_for_status()

                    data: dict[str, Any] = response.json()
                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})

                    prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
                    output_tokens = int(usage.get("completion_tokens", 0) or 0)
                    latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                    cost_usd = self._estimate_cost(prompt_tokens, output_tokens)

                    gen_response = GenResponse(
                        content=content,
                        provider=self.name,
                        prompt_tokens=prompt_tokens,
                        output_tokens=output_tokens,
                        latency_ms=latency_ms,
                        cost_usd=cost_usd,
                        confidence=None,
                        metadata={"model": self.model, "attempt": attempt + 1},
                    )

                    self._log_generation(request, gen_response)
                    return gen_response

            except Exception as e:
                error_msg = str(e)
                last_error = error_msg
                self.logger.warning(
                    f"DeepSeek API attempt {attempt + 1} failed: {error_msg}"
                )

                if attempt < self.max_retries - 1:
                    # Exponential backoff with jitter
                    sleep_time = (0.5 * (2**attempt)) + random.uniform(0, 1)
                    await asyncio.sleep(sleep_time)
                    continue
        # All attempts failed, return fallback
        return self._fallback_response(request, start_time, error=last_error)

    # NOTE: The streaming logic below is the only streaming implementation for this provider.
    # It uses DeepSeek's native Server-Sent Events to stream tokens.

    async def generate_stream(
        self, request: GenRequest
    ) -> AsyncGenerator[StreamChunk, None]:
        """Generate streaming response using DeepSeek chat mode."""
        if not self.api_key or httpx is None:
            # Fallback to base implementation
            async for chunk in super().generate_stream(request):
                yield chunk
            return

        messages: list[dict[str, Any]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": request.max_tokens or 2048,
            "temperature": request.temperature or 0.7,
            "stream": True,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        chunk_id = 0
        accumulated_content = ""

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:  # type: ignore[reportUnknownMemberType]
                async with client.stream(
                    "POST", self.base_url, json=payload, headers=headers
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line or not line.strip():
                            continue
                        if not line.startswith("data: "):
                            continue

                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            yield StreamChunk(
                                content="",
                                chunk_id=chunk_id,
                                is_final=True,
                                provider=self.name,
                                metadata={
                                    "model": self.model,
                                    "total_content": accumulated_content,
                                    "stream_complete": True,
                                },
                            )
                            break

                        try:
                            data_any = json.loads(data_str)
                            if not isinstance(data_any, dict):
                                continue
                            data_obj: Dict[str, Any] = cast(Dict[str, Any], data_any)

                            choices_any = data_obj.get("choices")
                            if not isinstance(choices_any, list) or not choices_any:
                                continue
                            choices_list = cast(list[Dict[str, Any]], choices_any)
                            choice0: Dict[str, Any] = choices_list[0]

                            delta_any = choice0.get("delta", {})
                            if not isinstance(delta_any, dict):
                                continue
                            delta: Dict[str, Any] = cast(Dict[str, Any], delta_any)

                            piece_any = delta.get("content", "")
                            content_piece = "" if piece_any is None else str(piece_any)

                            if content_piece:
                                accumulated_content += content_piece
                                yield StreamChunk(
                                    content=content_piece,
                                    chunk_id=chunk_id,
                                    is_final=False,
                                    provider=self.name,
                                    metadata={
                                        "model": self.model,
                                        "accumulated_length": len(accumulated_content),
                                    },
                                )
                                chunk_id += 1
                        except Exception:
                            continue

        except Exception as e:
            yield StreamChunk(
                content=f"[Streaming Error: {str(e)}]",
                chunk_id=chunk_id,
                is_final=True,
                provider=f"{self.name}_error",
                metadata={"error": str(e), "stream_failed": True},
            )

    def _fallback_response(
        self, request: GenRequest, start_time: float, error: Optional[str] = None
    ) -> GenResponse:
        """Generate fallback response when API is unavailable."""
        fallback_content = (
            "I apologize, but I'm currently experiencing connectivity issues with the DeepSeek service. "
            "This is a fallback response. Please try again in a moment, or the system may route "
            "your request to an alternative provider."
        )

        latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

        return GenResponse(
            content=fallback_content,
            provider=f"{self.name}_fallback",
            latency_ms=latency_ms,
            metadata={"fallback": True, "error": error},
        )

    async def health_check(self) -> Dict[str, Any]:
        """Check DeepSeek API health quickly (single attempt, short timeout)."""
        if not self.api_key:
            return {
                "status": "unavailable",
                "reason": "no_api_key",
                "provider": self.name,
            }

        if httpx is None:
            return {
                "status": "unavailable",
                "reason": "httpx_missing",
                "provider": self.name,
            }

        # Minimal request with short timeout, no retries
        messages: list[dict[str, str]] = [{"role": "user", "content": "ping"}]
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 1,
            "temperature": 0.0,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(self.base_url, json=payload, headers=headers)
                if resp.status_code == 401:
                    return {
                        "status": "unhealthy",
                        "reason": "unauthorized",
                        "provider": self.name,
                    }
                resp.raise_for_status()
                return {"status": "healthy", "provider": self.name, "model": self.model}
        except Exception as e:
            return {"status": "unhealthy", "reason": str(e), "provider": self.name}

    def _estimate_cost(self, prompt_tokens: int, output_tokens: int) -> float:
        """Estimate cost for DeepSeek V3.1."""
        input_cost = (prompt_tokens / 1000) * self.input_cost_per_1k
        output_cost = (output_tokens / 1000) * self.output_cost_per_1k
        return input_cost + output_cost
