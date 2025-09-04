"""
DeepSeek V3.1 Thinking Provider
==============================
"""

from __future__ import annotations
import asyncio
import json
import os
import random
from typing import Dict, Any, Optional

from .base_provider import BaseProvider, GenRequest, GenResponse

try:
    import httpx
except ImportError:
    httpx = None


class DeepSeekThinkingProvider(BaseProvider):
    """DeepSeek V3.1 thinking mode provider."""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("deepseek_thinking", config)
        self.api_key = config.get("api_key") or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.model = config.get("model", "deepseek-chat")  # Same model, thinking mode
        self.timeout = config.get("timeout", 180)  # Longer timeout for thinking
        self.max_retries = config.get("max_retries", 3)

        # DeepSeek V3 pricing (same as chat mode)
        self.input_cost_per_1k = 0.00014
        self.output_cost_per_1k = 0.00028

    async def generate(self, request: GenRequest) -> GenResponse:
        """Generate response using DeepSeek thinking mode."""
        start_time = asyncio.get_event_loop().time()

        if not self.api_key or httpx is None:
            return self._fallback_response(request, start_time)

        # Construct thinking prompt with CoT budget
        cot_budget = request.cot_budget or 3000
        thinking_prompt = self._construct_thinking_prompt(request.prompt, cot_budget)

        messages = []
        if request.system_prompt:
            # Enhanced system prompt for thinking mode
            enhanced_system = f"{request.system_prompt}\n\nYou should think step-by-step about this problem. Use <think> tags to show your reasoning process, then provide your final answer."
            messages.append({"role": "system", "content": enhanced_system})
        else:
            messages.append(
                {
                    "role": "system",
                    "content": "Think step-by-step about the problem. Use <think> tags to show your reasoning process, then provide your final answer.",
                }
            )
        messages.append({"role": "user", "content": thinking_prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": min(request.max_tokens or 4096, cot_budget + 1000),
            "temperature": request.temperature or 0.7,
            "stream": False,
        }

        # Add thinking flag if supported by API
        if "thinking" in self.config.get("supported_features", []):
            payload["thinking"] = True

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

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

                    # Extract final answer from thinking tags if present
                    final_content = self._extract_final_answer(content)

                    gen_response = GenResponse(
                        content=final_content,
                        provider=self.name,
                        prompt_tokens=prompt_tokens,
                        output_tokens=output_tokens,
                        latency_ms=latency_ms,
                        cost_usd=cost_usd,
                        confidence=None,  # Will be computed by router
                        metadata={
                            "model": self.model,
                            "attempt": attempt + 1,
                            "cot_budget": cot_budget,
                            "raw_content": content,
                            "thinking_mode": True,
                        },
                    )

                    self._log_generation(request, gen_response)
                    return gen_response

            except Exception as e:
                error_msg = str(e)
                self.logger.warning(
                    f"DeepSeek thinking API attempt {attempt + 1} failed: {error_msg}"
                )

                if attempt < self.max_retries - 1:
                    # Exponential backoff with jitter
                    sleep_time = (0.5 * (2**attempt)) + random.uniform(0, 1)
                    await asyncio.sleep(sleep_time)
                    continue
                else:
                    # Final attempt failed
                    self._log_generation(request, None, error_msg)
                    return self._fallback_response(request, start_time, error=error_msg)

    def _construct_thinking_prompt(self, original_prompt: str, cot_budget: int) -> str:
        """Construct a prompt that encourages step-by-step thinking."""
        return f"""Please think carefully about this problem step-by-step. Show your reasoning process using <think> tags, then provide your final answer.

Original question: {original_prompt}

Instructions:
- Use <think>...</think> tags to show your reasoning process
- Consider multiple approaches if applicable  
- Check your work before providing the final answer
- Keep your reasoning within approximately {cot_budget} tokens
- After thinking, provide a clear final answer

Begin your response with <think> and end with your final answer outside the tags."""

    def _extract_final_answer(self, content: str) -> str:
        """Extract final answer from content with thinking tags."""
        if "<think>" not in content:
            return content

        # Find the last closing </think> tag
        think_end = content.rfind("</think>")
        if think_end == -1:
            return content

        # Everything after the last </think> tag is the final answer
        final_answer = content[think_end + 8 :].strip()

        # If no content after </think>, return the original
        if not final_answer:
            return content

        return final_answer

    def _fallback_response(
        self, request: GenRequest, start_time: float, error: Optional[str] = None
    ) -> GenResponse:
        """Generate fallback response when API is unavailable."""
        fallback_content = (
            "I apologize, but I'm currently experiencing connectivity issues with the DeepSeek thinking service. "
            "This appears to be a complex problem that would benefit from step-by-step reasoning. "
            "Please try again in a moment, or the system may route your request to an alternative reasoning provider."
        )

        latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

        return GenResponse(
            content=fallback_content,
            provider=f"{self.name}_fallback",
            latency_ms=latency_ms,
            metadata={"fallback": True, "error": error},
        )

    async def health_check(self) -> Dict[str, Any]:
        """Quick health check for DeepSeek thinking API (single attempt, short timeout)."""
        if not self.api_key:
            return {"status": "unavailable", "reason": "no_api_key", "provider": self.name}

        if httpx is None:
            return {"status": "unavailable", "reason": "httpx_missing", "provider": self.name}

        messages = [
            {"role": "system", "content": "Think step by step, but keep it minimal."},
            {"role": "user", "content": "ping"},
        ]
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 1,
            "temperature": 0.0,
            "stream": False,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(self.base_url, json=payload, headers=headers)
                if resp.status_code == 401:
                    return {"status": "unhealthy", "reason": "unauthorized", "provider": self.name}
                resp.raise_for_status()
                return {
                    "status": "healthy",
                    "provider": self.name,
                    "model": self.model,
                    "thinking_mode": True,
                }
        except Exception as e:
            return {"status": "unhealthy", "reason": str(e), "provider": self.name}

    def _estimate_cost(self, prompt_tokens: int, output_tokens: int) -> float:
        """Estimate cost for DeepSeek V3.1 thinking mode."""
        input_cost = (prompt_tokens / 1000) * self.input_cost_per_1k
        output_cost = (output_tokens / 1000) * self.output_cost_per_1k
        return input_cost + output_cost
