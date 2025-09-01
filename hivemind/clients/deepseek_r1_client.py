"""
DeepSeek R1 Client for Arbiter System
====================================

This module replaces the GPT-4o client with DeepSeek R1 for the dreaming/training pipeline.
DeepSeek R1 provides excellent reasoning capabilities at significantly lower cost.
"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional

try:
    import httpx
except ImportError:
    httpx = None

class DeepSeekR1Client:
    """Asynchronous client for the DeepSeek R1 model (replaces GPT-4o in dreaming)."""
    
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.model = "deepseek-reasoner"  # DeepSeek R1 reasoning model
        self._max_retries = 3
        self._retry_delay = 1.0
        
        # Cost optimization (DeepSeek R1 is much cheaper than GPT-4o)
        self.input_cost_per_1k = 0.00055   # ~70% cheaper than GPT-4o
        self.output_cost_per_1k = 0.0022   # ~70% cheaper than GPT-4o
        
        if not self.api_key:
            logging.warning("DeepSeek API key not found. DeepSeekR1Client will use stub responses.")
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate a response from DeepSeek R1 (reasoning mode).
        
        This replaces GPT-4o in the dreaming/training pipeline with DeepSeek R1
        for superior reasoning capabilities at significantly lower cost.
        """
        
        if not self.api_key or not httpx:
            return self._stub_response(prompt)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            # Default system prompt for arbiter role
            messages.append({
                "role": "system", 
                "content": "You are a meticulous AI arbiter responsible for refining and improving responses. Analyze the given response critically and provide detailed improvements."
            })
        
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 2048),
            "temperature": kwargs.get("temperature", 0.3),  # Lower temperature for more focused reasoning
            "stream": False
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=120) as client:
                    response = await client.post(self.base_url, json=payload, headers=headers)
                    response.raise_for_status()
                    
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    
                    # Calculate cost (much lower than GPT-4o)
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    cost_usd = self._calculate_cost(prompt_tokens, completion_tokens)
                    
                    return {
                        "refined_answer": content,
                        "correction_analysis": f"Enhanced by DeepSeek R1 reasoning model with {completion_tokens} tokens generated",
                        "model_used": self.model,
                        "cost_usd": cost_usd,
                        "tokens_used": prompt_tokens + completion_tokens,
                        "reasoning_quality": "high",  # DeepSeek R1 provides excellent reasoning
                        "cost_efficiency": "excellent"  # 70% cheaper than GPT-4o
                    }
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit
                    if attempt < self._max_retries:
                        await asyncio.sleep(self._retry_delay * (2 ** attempt))
                        continue
                else:
                    logging.error(f"DeepSeek R1 API request failed (attempt {attempt+1}/{self._max_retries+1}): {e}", exc_info=True)
                    if attempt < self._max_retries:
                        await asyncio.sleep(self._retry_delay)
                        continue
            except Exception as e:
                try:
                    logging.error(f"DeepSeek R1 API response format error (attempt {attempt+1}/{self._max_retries+1}): {e}, response: {response.text}", exc_info=True)
                except:
                    logging.error(f"DeepSeek R1 API error (attempt {attempt+1}/{self._max_retries+1}): {e}", exc_info=True)
                if attempt < self._max_retries:
                    await asyncio.sleep(self._retry_delay)
                    continue
            
            # If we reach here, all retries failed
            return self._stub_response(prompt, error=f"API failed after {self._max_retries + 1} attempts")
        
        return self._stub_response(prompt, error="Max retries exceeded")
    
    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost for DeepSeek R1 (much cheaper than GPT-4o)."""
        input_cost = (prompt_tokens / 1000) * self.input_cost_per_1k
        output_cost = (completion_tokens / 1000) * self.output_cost_per_1k
        return input_cost + output_cost
    
    def _stub_response(self, prompt: str, error: Optional[str] = None) -> Dict[str, Any]:
        """Provide a stub response when the API is unavailable."""
        return {
            "refined_answer": prompt,  # Return original if can't improve
            "correction_analysis": f"This is a stubbed DeepSeek R1 response; no real analysis was performed. {error or 'Add DEEPSEEK_API_KEY to enable real Arbiter refinement.'}",
            "model_used": "stub",
            "cost_usd": 0.0,
            "tokens_used": 0,
            "reasoning_quality": "unavailable",
            "cost_efficiency": "N/A"
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check DeepSeek R1 client health."""
        if not self.api_key:
            return {"status": "unavailable", "reason": "no_api_key"}
        
        try:
            test_result = await self.generate("Test health check", max_tokens=10)
            return {
                "status": "healthy" if test_result.get("model_used") != "stub" else "degraded",
                "model": self.model,
                "api_available": test_result.get("model_used") != "stub"
            }
        except Exception as e:
            return {"status": "unhealthy", "reason": str(e)}

# Backward compatibility function
async def test_r1_client():
    """Test the DeepSeek R1 client functionality."""
    client = DeepSeekR1Client()
    
    health = await client.health_check()
    print(f"DeepSeek R1 Client Health: {health}")
    
    if health["status"] != "unavailable":
        test_response = await client.generate(
            "Analyze this response and suggest improvements: The sky is blue because of light scattering.",
            system_prompt="You are an expert arbiter. Provide detailed analysis and improvements."
        )
        
        print(f"DeepSeek R1 Response: {test_response}")
        return test_response
    
    return None

if __name__ == "__main__":
    # Test the client
    asyncio.run(test_r1_client())