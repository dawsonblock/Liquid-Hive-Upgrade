"""
Test Routing Decision Paths
==========================
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from unified_runtime.model_router import DSRouter, RouterConfig
from unified_runtime.providers.base_provider import GenRequest


class TestRoutingPaths:
    """Test different routing decision paths."""

    @pytest.fixture
    def router(self):
        """Create router with test configuration."""
        config = RouterConfig(conf_threshold=0.65, support_threshold=0.55, max_cot_tokens=2000)
        router = DSRouter(config)

        # Mock providers
        router.providers = {
            "deepseek_chat": Mock(),
            "deepseek_thinking": Mock(),
            "deepseek_r1": Mock(),
            "qwen_cpu": Mock(),
        }

        return router

    @pytest.mark.asyncio
    async def test_easy_to_chat_routing(self, router):
        """Test that easy questions route to chat provider."""

        easy_questions = [
            "Hello, how are you?",
            "What's the weather like?",
            "Tell me a joke",
            "What is Python?",
        ]

        for question in easy_questions:
            decision = await router._determine_routing(GenRequest(prompt=question))
            assert decision.provider == "deepseek_chat"
            assert decision.reasoning == "simple_query"
            assert decision.cot_budget is None

    @pytest.mark.asyncio
    async def test_hard_to_thinking_routing(self, router):
        """Test that hard questions route to thinking provider."""

        hard_questions = [
            "Prove that the square root of 2 is irrational",
            "Write a regex to validate email addresses",
            "Optimize this algorithm for better Big-O complexity",
            "Debug this unit test failure in my code",
            "Analyze the logical fallacy in this argument",
            "Derive the quadratic formula step by step",
        ]

        for question in hard_questions:
            print(f"\nTesting: {question}")
            print(f"Is hard: {router._is_hard_problem(question)}")
            decision = await router._determine_routing(GenRequest(prompt=question))
            print(f"Decision: provider={decision.provider}, reasoning={decision.reasoning}")
            assert decision.provider == "deepseek_thinking", f"Expected deepseek_thinking, got {decision.provider} for '{question}'"
            assert decision.reasoning == "complex_query"
            assert decision.cot_budget <= router.config.max_cot_tokens

    @pytest.mark.asyncio
    async def test_low_confidence_escalation_to_r1(self, router):
        """Test escalation to R1 when confidence is low."""

        # Mock thinking provider with low confidence response
        thinking_response = Mock()
        thinking_response.provider = "deepseek_thinking"
        thinking_response.content = "I'm not entirely sure about this..."
        thinking_response.confidence = None  # Will be set by confidence assessment
        thinking_response.metadata = {}

        router.providers["deepseek_thinking"].generate = AsyncMock(return_value=thinking_response)

        # Mock R1 provider
        r1_response = Mock()
        r1_response.provider = "deepseek_r1"
        r1_response.content = "After careful analysis..."
        r1_response.confidence = None
        r1_response.metadata = {}

        router.providers["deepseek_r1"].generate = AsyncMock(return_value=r1_response)

        # Mock confidence assessment to return low confidence first, then high
        with patch.object(router, "_assess_confidence", side_effect=[0.4, 0.9]):
            request = GenRequest(prompt="Please prove this mathematical theorem")
            response = await router.generate(request)

        # Should have escalated to R1
        assert response.provider == "deepseek_r1"
        assert response.metadata.get("escalated")

    def test_confidence_assessment_heuristics(self, router):
        """Test confidence assessment heuristics."""

        from unified_runtime.providers.base_provider import GenResponse

        # High confidence response
        high_conf_response = GenResponse(
            content="The answer is definitively X because of clear reasons A, B, and C.",
            provider="deepseek_thinking",
            metadata={},
        )
        request = GenRequest(prompt="Test question")

        confidence = asyncio.run(router._assess_confidence(high_conf_response, request))
        assert confidence > 0.7

        # Low confidence response
        low_conf_response = GenResponse(
            content="I'm not sure about this.", provider="deepseek_chat", metadata={}
        )

        confidence = asyncio.run(router._assess_confidence(low_conf_response, request))
        assert confidence < 0.5

    @pytest.mark.asyncio
    async def test_support_threshold_routing(self, router):
        """Test routing based on RAG support threshold."""

        # Mock low RAG support
        with patch.object(router, "_get_rag_support_score", return_value=0.3):
            # Even simple question should route to thinking if low RAG support
            decision = await router._determine_routing(GenRequest(prompt="Simple question"))
            assert decision.provider == "deepseek_thinking"
            assert decision.reasoning == "complex_query"

        # Mock high RAG support
        with patch.object(router, "_get_rag_support_score", return_value=0.8):
            # Hard question with good support might still go to thinking
            decision = await router._determine_routing(GenRequest(prompt="Complex analysis"))
            # This should still be thinking due to hard problem detection
            assert decision.provider == "deepseek_thinking"


if __name__ == "__main__":
    pytest.main([__file__])
