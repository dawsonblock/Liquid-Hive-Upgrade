"""DeepSeek R1 Reasoning Provider
=============================
"""

from __future__ import annotations

import asyncio
import os
import random
from typing import Any, Optional

from .base_provider import BaseProvider, GenRequest, GenResponse

try:
    import httpx
except ImportError:
    httpx = None


class DeepSeekR1Provider(BaseProvider):
    """DeepSeek R1 reasoning mode provider."""

    def __init__(self, config: dict[str, Any] = None):
        super().__init__("deepseek_r1", config)
        self.api_key = config.get("api_key") or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.model = config.get("model", "deepseek-reasoner")  # R1 model
        self.timeout = config.get("timeout", 300)  # Long timeout for reasoning
        self.max_retries = config.get("max_retries", 3)
        self.max_cot_tokens = config.get("max_cot_tokens", 6000)

        # DeepSeek R1 pricing (typically higher for reasoning)
        self.input_cost_per_1k = 0.00055  # Higher for R1
        self.output_cost_per_1k = 0.0022  # Higher for R1 reasoning

    async def generate(self, request: GenRequest) -> GenResponse:
        """Generate response using DeepSeek R1 reasoning mode."""
        start_time = asyncio.get_event_loop().time()

        if not self.api_key or httpx is None:
            return self._fallback_response(request, start_time)

        # Enforce CoT budget limit
        cot_budget = min(request.cot_budget or self.max_cot_tokens, self.max_cot_tokens)

        messages = []
        if request.system_prompt:
            # Enhanced system prompt for R1 reasoning
            enhanced_system = f"""{request.system_prompt}

You are operating in deep reasoning mode. Take time to think through this problem carefully:
1. Break down the problem into components
2. Consider multiple solution approaches
3. Analyze potential issues or edge cases
4. Verify your reasoning before concluding
5. Provide detailed justification for your final answer"""
            messages.append({"role": "system", "content": enhanced_system})
        else:
            messages.append(
                {
                    "role": "system",
                    "content": """You are operating in deep reasoning mode. Think carefully through problems:
1. Break down the problem systematically
2. Consider multiple approaches
3. Check for potential issues
4. Verify your reasoning
5. Provide clear justification for your conclusions""",
                }
            )

        messages.append({"role": "user", "content": request.prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": min(request.max_tokens or 8192, cot_budget + 2000),
            "temperature": request.temperature or 0.3,  # Lower temp for reasoning
            "stream": False,
        }

        # R1-specific parameters if supported
        if "reasoning_effort" in self.config.get("supported_features", []):
            payload["reasoning_effort"] = "high"
        if "cot_budget" in self.config.get("supported_features", []):
            payload["cot_budget"] = cot_budget

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

                    # Extract reasoning chain if present
                    reasoning_chain, final_answer = self._parse_reasoning_response(content)

                    gen_response = GenResponse(
                        content=final_answer or content,
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
                            "reasoning_chain": reasoning_chain,
                            "raw_content": content,
                            "reasoning_mode": "r1",
                        },
                    )

                    self._log_generation(request, gen_response)
                    return gen_response

            except Exception as e:
                error_msg = str(e)
                self.logger.warning(f"DeepSeek R1 API attempt {attempt + 1} failed: {error_msg}")

                if attempt < self.max_retries - 1:
                    # Exponential backoff with jitter
                    sleep_time = (1.0 * (2**attempt)) + random.uniform(0, 2)
                    await asyncio.sleep(sleep_time)
                    continue
                else:
                    # Final attempt failed
                    self._log_generation(request, None, error_msg)
                    return self._fallback_response(request, start_time, error=error_msg)

    def _parse_reasoning_response(self, content: str) -> tuple[Optional[str], Optional[str]]:
        """Parse R1 response to extract reasoning chain and final answer."""
        # Look for structured reasoning patterns
        reasoning_markers = [
            ("**Reasoning:**", "**Answer:**"),
            ("<reasoning>", "</reasoning>"),
            ("Let me think", "Therefore"),
            ("Analysis:", "Conclusion:"),
        ]

        for start_marker, end_marker in reasoning_markers:
            if start_marker in content:
                parts = content.split(start_marker, 1)
                if len(parts) > 1:
                    reasoning_part = parts[1]
                    if end_marker in reasoning_part:
                        reasoning, answer = reasoning_part.split(end_marker, 1)
                        return reasoning.strip(), answer.strip()
                    else:
                        return reasoning_part.strip(), None

        # If no clear structure, return original content
        return None, content

    def _fallback_response(
        self, request: GenRequest, start_time: float, error: Optional[str] = None
    ) -> GenResponse:
        """Generate fallback response when R1 API is unavailable."""
        fallback_content = (
            "I apologize, but the advanced reasoning system (DeepSeek R1) is currently unavailable. "
            "This appears to be a complex problem that requires deep analysis. "
            "The system will attempt to route your request to an alternative provider or "
            "provide a simpler analysis using available resources."
        )

        latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

        return GenResponse(
            content=fallback_content,
            provider=f"{self.name}_fallback",
            latency_ms=latency_ms,
            metadata={"fallback": True, "error": error, "reasoning_mode": "r1"},
        )

    async def health_check(self) -> dict[str, Any]:
        """Quick health check for DeepSeek R1 API (single attempt, short timeout)."""
        if not self.api_key:
            return {"status": "unavailable", "reason": "no_api_key", "provider": self.name}

        if httpx is None:
            return {"status": "unavailable", "reason": "httpx_missing", "provider": self.name}

        messages = [
            {"role": "system", "content": "Reason concisely."},
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
                    "reasoning_mode": "r1",
                    "max_cot_tokens": self.max_cot_tokens,
                }
        except Exception as e:
            return {"status": "unhealthy", "reason": str(e), "provider": self.name}

    def _estimate_cost(self, prompt_tokens: int, output_tokens: int) -> float:
        """Estimate cost for DeepSeek R1 reasoning mode."""
        input_cost = (prompt_tokens / 1000) * self.input_cost_per_1k
        output_cost = (output_tokens / 1000) * self.output_cost_per_1k
        return input_cost + output_cost
