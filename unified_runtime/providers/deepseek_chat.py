"""
DeepSeek V3.1 Chat Provider with Streaming Support
=================================================
"""

from __future__ import annotations
import asyncio
import json
import os
import random
from typing import Dict, Any, Optional, AsyncGenerator

from .base_provider import BaseProvider, GenRequest, GenResponse, StreamChunk

try:
    import httpx
except ImportError:
    httpx = None

class DeepSeekChatProvider(BaseProvider):
    """DeepSeek V3.1 non-thinking mode provider."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("deepseek_chat", config)
        self.api_key = config.get("api_key") or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.model = config.get("model", "deepseek-chat")
        self.timeout = config.get("timeout", 120)
        self.max_retries = config.get("max_retries", 3)
        
        # DeepSeek V3 pricing (approximate)
        self.input_cost_per_1k = 0.00014  # $0.14 per 1K input tokens
        self.output_cost_per_1k = 0.00028  # $0.28 per 1K output tokens
        
    async def generate(self, request: GenRequest) -> GenResponse:
        """Generate response using DeepSeek chat mode."""
        start_time = asyncio.get_event_loop().time()
        
        if not self.api_key or httpx is None:
            return self._fallback_response(request, start_time)
            
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": request.max_tokens or 2048,
            "temperature": request.temperature or 0.7,
            "stream": request.stream
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(self.base_url, json=payload, headers=headers)
                    response.raise_for_status()
                    
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    output_tokens = usage.get("completion_tokens", 0)
                    latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                    cost_usd = self._estimate_cost(prompt_tokens, output_tokens)
                    
                    gen_response = GenResponse(
                        content=content,
                        provider=self.name,
                        prompt_tokens=prompt_tokens,
                        output_tokens=output_tokens,
                        latency_ms=latency_ms,
                        cost_usd=cost_usd,
                        confidence=None,  # Will be computed by router
                        metadata={"model": self.model, "attempt": attempt + 1}
                    )
                    
                    self._log_generation(request, gen_response)
                    return gen_response
                    
            except Exception as e:
                error_msg = str(e)
                self.logger.warning(f"DeepSeek API attempt {attempt + 1} failed: {error_msg}")
                
                if attempt < self.max_retries - 1:
                    # Exponential backoff with jitter
                    sleep_time = (0.5 * (2 ** attempt)) + random.uniform(0, 1)
                    await asyncio.sleep(sleep_time)
                    continue
                else:
                    # Final attempt failed
                    self._log_generation(request, None, error_msg)
                    return self._fallback_response(request, start_time, error=error_msg)
    
    async def generate_stream(self, request: GenRequest) -> AsyncGenerator[StreamChunk, None]:
        """Generate streaming response using DeepSeek chat mode."""
        if not self.api_key or httpx is None:
            # Fallback to base implementation
            async for chunk in super().generate_stream(request):
                yield chunk
            return
            
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": request.max_tokens or 2048,
            "temperature": request.temperature or 0.7,
            "stream": True
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        chunk_id = 0
        accumulated_content = ""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", self.base_url, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        
                        if not line.startswith("data: "):
                            continue
                        
                        data_str = line[6:]  # Remove "data: " prefix
                        
                        if data_str.strip() == "[DONE]":
                            # Send final chunk
                            yield StreamChunk(
                                content="",
                                chunk_id=chunk_id,
                                is_final=True,
                                provider=self.name,
                                metadata={
                                    "model": self.model,
                                    "total_content": accumulated_content,
                                    "stream_complete": True
                                }
                            )
                            break
                        
                        try:
                            data = json.loads(data_str)
                            choice = data.get("choices", [{}])[0]
                            delta = choice.get("delta", {})
                            content = delta.get("content", "")
                            
                            if content:
                                accumulated_content += content
                                
                                yield StreamChunk(
                                    content=content,
                                    chunk_id=chunk_id,
                                    is_final=False,
                                    provider=self.name,
                                    metadata={
                                        "model": self.model,
                                        "accumulated_length": len(accumulated_content)
                                    }
                                )
                                
                                chunk_id += 1
                                
                        except json.JSONDecodeError:
                            # Skip malformed chunks
                            continue
                            
        except Exception as e:
            # Send error chunk
            yield StreamChunk(
                content=f"[Streaming Error: {str(e)}]",
                chunk_id=chunk_id,
                is_final=True,
                provider=f"{self.name}_error",
                metadata={"error": str(e), "stream_failed": True}
            )
    
    def _fallback_response(self, request: GenRequest, start_time: float, error: str = None) -> GenResponse:
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
            metadata={"fallback": True, "error": error}
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check DeepSeek API health."""
        if not self.api_key:
            return {
                "status": "unavailable",
                "reason": "no_api_key",
                "provider": self.name
            }
            
        try:
            # Simple health check with minimal request
            test_request = GenRequest(
                prompt="Hello",
                max_tokens=5,
                temperature=0.1
            )
            response = await self.generate(test_request)
            
            return {
                "status": "healthy" if response.content and not response.metadata.get("fallback") else "degraded",
                "provider": self.name,
                "model": self.model,
                "latency_ms": response.latency_ms
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "reason": str(e),
                "provider": self.name
            }
    
    def _estimate_cost(self, prompt_tokens: int, output_tokens: int) -> float:
        """Estimate cost for DeepSeek V3.1."""
        input_cost = (prompt_tokens / 1000) * self.input_cost_per_1k
        output_cost = (output_tokens / 1000) * self.output_cost_per_1k
        return input_cost + output_cost