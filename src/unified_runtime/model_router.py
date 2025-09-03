"""
DS-Router v1: Model Router with Intelligence Routing
==================================================
"""

from __future__ import annotations
import asyncio
import re
import logging
import os
from typing import Dict, Any, List, Optional, Tuple, Union, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from .providers import (
    BaseProvider, GenRequest, GenResponse, StreamChunk,
    DeepSeekChatProvider, DeepSeekThinkingProvider, 
    DeepSeekR1Provider, QwenCPUProvider
)

try:
    from ..safety.pre_guard import PreGuard
    from ..safety.post_guard import PostGuard
except ImportError:
    PreGuard = None
    PostGuard = None

log = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Provider disabled due to failures
    HALF_OPEN = "half_open"  # Testing if provider recovered

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5          # Failures before opening circuit
    recovery_timeout: int = 300         # Seconds before attempting recovery
    success_threshold: int = 3          # Successes needed to close circuit
    timeout_seconds: int = 30           # Request timeout

@dataclass 
class CircuitBreaker:
    """Circuit breaker for provider health management."""
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    state: CircuitState = CircuitState.CLOSED
    
    def should_attempt_call(self) -> bool:
        """Determine if we should attempt to call the provider."""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            # Check if we should transition to half-open
            if (self.last_failure_time and 
                datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.config.recovery_timeout)):
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return True
        return False
    
    def record_success(self):
        """Record a successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.success_count = 0

@dataclass
class RouterConfig:
    """Configuration for the DS-Router."""
    conf_threshold: float = 0.62
    support_threshold: float = 0.55
    max_cot_tokens: int = 6000
    max_oracle_tokens_per_day: int = 250000
    max_oracle_usd_per_day: float = 50.0
    budget_enforcement: str = "hard"  # hard|warn
    
    # Provider configurations
    deepseek_api_key: Optional[str] = None
    hf_token: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'RouterConfig':
        """Load configuration from environment variables."""
        # Support both HF_TOKEN and HUGGING_FACE_HUB_TOKEN
        hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
        return cls(
            conf_threshold=float(os.getenv("CONF_THRESHOLD", "0.62")),
            support_threshold=float(os.getenv("SUPPORT_THRESHOLD", "0.55")),
            max_cot_tokens=int(os.getenv("MAX_COT_TOKENS", "6000")),
            max_oracle_tokens_per_day=int(os.getenv("MAX_ORACLE_TOKENS_PER_DAY", "250000")),
            max_oracle_usd_per_day=float(os.getenv("MAX_ORACLE_USD_PER_DAY", "50.0")),
            budget_enforcement=os.getenv("BUDGET_ENFORCEMENT", "hard"),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
            hf_token=hf_token
        )

class DSRouter:
    """Intelligent model router with safety, fallback, and circuit breaker capabilities."""
    
    def __init__(self, config: RouterConfig = None):
        self.config = config or RouterConfig.from_env()
        self.logger = logging.getLogger(__name__)
        
        # Initialize providers
        self.providers: Dict[str, BaseProvider] = {}
        self._initialize_providers()
        
        # Initialize circuit breakers for each provider
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._initialize_circuit_breakers()
        
        # Initialize safety guards
        self.pre_guard = PreGuard() if PreGuard else None
        self.post_guard = PostGuard() if PostGuard else None
        
        # Budget tracking (now uses Redis for distributed state)
        self._budget_tracker = BudgetTracker(self.config)
        
        # Compile regex patterns for hard problem detection
        self._hard_patterns = self._compile_hard_patterns()
        
        # Start background health check task
        self._health_check_task = None
        self._start_health_monitoring()
        
    def _initialize_circuit_breakers(self):
        """Initialize circuit breakers for all providers."""
        breaker_config = CircuitBreakerConfig(
            failure_threshold=int(os.getenv("PROVIDER_FAILURE_THRESHOLD", "5")),
            recovery_timeout=int(os.getenv("PROVIDER_RECOVERY_TIMEOUT", "300")),
            success_threshold=int(os.getenv("PROVIDER_SUCCESS_THRESHOLD", "3")),
            timeout_seconds=int(os.getenv("PROVIDER_TIMEOUT_SECONDS", "30"))
        )
        
        for provider_name in self.providers.keys():
            self.circuit_breakers[provider_name] = CircuitBreaker(breaker_config)
        
        self.logger.info("Initialized circuit breakers for providers: %s", list(self.circuit_breakers.keys()))
    
    def _start_health_monitoring(self):
        """Start background task for periodic health checks."""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            self._health_check_task = loop.create_task(self._periodic_health_check())
        except Exception as e:
            self.logger.warning(f"Could not start health monitoring: {e}")
    
    async def _periodic_health_check(self):
        """Periodically check provider health and update circuit breakers."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                for provider_name, provider in self.providers.items():
                    circuit_breaker = self.circuit_breakers.get(provider_name)
                    if not circuit_breaker:
                        continue
                    
                    # Only check health for providers in OPEN state (trying to recover)
                    if circuit_breaker.state == CircuitState.OPEN:
                        try:
                            health_result = await asyncio.wait_for(
                                provider.health_check(), 
                                timeout=circuit_breaker.config.timeout_seconds
                            )
                            
                            if health_result.get("status") == "healthy":
                                self.logger.info(f"Provider {provider_name} health recovered, transitioning to HALF_OPEN")
                                circuit_breaker.state = CircuitState.HALF_OPEN
                                circuit_breaker.success_count = 0
                            
                        except Exception as e:
                            self.logger.debug(f"Health check failed for {provider_name}: {e}")
                            # Keep circuit open
                            
            except Exception as e:
                self.logger.error(f"Health monitoring error: {e}")
                
    async def _call_provider_with_circuit_breaker(self, provider_name: str, request: GenRequest) -> GenResponse:
        """Call provider with circuit breaker protection."""
        circuit_breaker = self.circuit_breakers.get(provider_name)
        provider = self.providers.get(provider_name)
        
        if not circuit_breaker or not provider:
            raise ValueError(f"Provider {provider_name} or circuit breaker not found")
        
        # Check if circuit breaker allows the call
        if not circuit_breaker.should_attempt_call():
            raise Exception(f"Provider {provider_name} circuit breaker is OPEN (too many failures)")
        
        try:
            # Make the actual provider call with timeout
            response = await asyncio.wait_for(
                provider.generate(request),
                timeout=circuit_breaker.config.timeout_seconds
            )
            
            # Record success
            circuit_breaker.record_success()
            self.logger.debug(f"Provider {provider_name} call successful, circuit state: {circuit_breaker.state}")
            
            return response
            
        except Exception as e:
            # Record failure
            circuit_breaker.record_failure()
            self.logger.warning(f"Provider {provider_name} call failed, circuit state: {circuit_breaker.state}, error: {e}")
            raise
        
        except Exception as e:
            # Record failure
            circuit_breaker.record_failure()
            self.logger.warning(f"Provider {provider_name} call failed, circuit state: {circuit_breaker.state}, error: {e}")
            raise

    def _install_oracle_providers(self) -> None:
        """Replace built-in providers with those loaded from config/providers.yaml via ProviderManager.
        Falls back to existing providers on error.
        """
        try:
            from oracle.manager import ProviderManager
            from .oracle_adapter import OracleToBaseAdapter
            pm = ProviderManager()
            provs, routing = pm.load()
            new_providers: Dict[str, BaseProvider] = {}
            # Build instances
            for name, pcfg in provs.items():
                key = pm.resolve_api_key(pcfg)
                prov_impl = None
                if pcfg.kind == "deepseek":
                    from oracle.deepseek import DeepSeekProvider
                    prov_impl = DeepSeekProvider(pcfg, key)
                elif pcfg.kind == "openai":
                    from oracle.openai import OpenAIProvider
                    prov_impl = OpenAIProvider(pcfg, key)
                elif pcfg.kind == "anthropic":
                    from oracle.anthropic import AnthropicProvider
                    prov_impl = AnthropicProvider(pcfg, key)
                elif pcfg.kind == "qwen":
                    from oracle.qwen import QwenProvider
                    prov_impl = QwenProvider(pcfg, key)
                if prov_impl is not None:
                    new_providers[name] = OracleToBaseAdapter(name, prov_impl)
            if new_providers:
                self.providers = new_providers
                self._initialize_circuit_breakers()
                self.logger.info("Installed oracle providers: %s", list(self.providers.keys()))
        except Exception as e:
            self.logger.warning(f"Oracle provider install failed; using built-ins: {e}")

    def _initialize_providers(self):
        """Initialize all available providers."""
        try:
            # DeepSeek providers
            deepseek_config = {"api_key": self.config.deepseek_api_key}
            
            self.providers["deepseek_chat"] = DeepSeekChatProvider(deepseek_config)
            self.providers["deepseek_thinking"] = DeepSeekThinkingProvider(deepseek_config)
            self.providers["deepseek_r1"] = DeepSeekR1Provider(deepseek_config)
            
            # Local fallback
            qwen_config = {"hf_token": self.config.hf_token}
            self.providers["qwen_cpu"] = QwenCPUProvider(qwen_config)
            
            self.logger.info("Initialized DS-Router with providers: %s", list(self.providers.keys()))
            
        except Exception as e:
            self.logger.error(f"Failed to initialize providers: {e}")

    def refresh_config_from_env(self) -> None:
        """Refresh config values from environment and rebuild providers/circuit breakers."""
        try:
            self.config.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
            self.config.hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")

            # Rebuild providers dict fresh
            new_providers: Dict[str, BaseProvider] = {}
            deepseek_config = {"api_key": self.config.deepseek_api_key}
            try:
                new_providers["deepseek_chat"] = DeepSeekChatProvider(deepseek_config)
                new_providers["deepseek_thinking"] = DeepSeekThinkingProvider(deepseek_config)
                new_providers["deepseek_r1"] = DeepSeekR1Provider(deepseek_config)
            except Exception as e:
                self.logger.warning(f"DeepSeek providers refresh error: {e}")

            qwen_config = {"hf_token": self.config.hf_token}
            try:
                new_providers["qwen_cpu"] = QwenCPUProvider(qwen_config)
            except Exception as e:
                self.logger.warning(f"Qwen provider refresh error: {e}")

            self.providers = new_providers

            # Rebuild circuit breakers for new providers
            self._initialize_circuit_breakers()
            self.logger.info("Router config refreshed from env; providers reloaded: %s", list(self.providers.keys()))
        except Exception as e:
            self.logger.error(f"Failed to refresh router config: {e}")
    
    def _compile_hard_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns for detecting hard problems."""
        patterns = [
            # Math and logic
            r'\b(prove|derive|optimize|constraints?)\b',
            r'\b(induction|deduction|axiom|theorem)\b',
            r'\b(NP-complete|complexity|Big-O|algorithm)\b',
            
            # Code and technical
            r'\b(regex|regular expression|compiler|parser)\b',
            r'\b(unit test|test case|debugging)\b',
            r'\b(refactor|optimize code|performance)\b',
            
            # Complex reasoning
            r'\b(paradox|contradiction|logical fallacy)\b',
            r'\b(multi-step|step-by-step|systematic)\b',
            r'\b(analyze|compare|evaluate|critique)\b',
            
            # Mathematical symbols and operations
            r'[∀∃∈∉∪∩⊂⊃∧∨¬→↔]',  # Logical symbols
            r'\b(integral|derivative|limit|convergence)\b',
        ]
        
        return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    async def generate(self, request: GenRequest) -> GenResponse:
        """Main router entry point with full safety and intelligence routing."""
        start_time = asyncio.get_event_loop().time()
        
        # Step 1: Pre-filtering and sanitization
        if self.pre_guard:
            sanitized_request, pre_guard_result = await self.pre_guard.process(request)
            if pre_guard_result.blocked:
                return self._create_blocked_response(pre_guard_result.reason, start_time)
        else:
            sanitized_request = request
            pre_guard_result = None
        
        # Step 2: Budget check
        budget_status = await self._budget_tracker.check_budget()
        if budget_status.exceeded and self.config.budget_enforcement == "hard":
            return self._create_budget_exceeded_response(budget_status, start_time)
        
        # Step 3: Determine routing strategy
        routing_decision = await self._determine_routing(sanitized_request)
        
        # Step 4: Generate response with chosen provider
        try:
            response = await self._generate_with_routing(sanitized_request, routing_decision)
        except Exception as e:
            self.logger.error(f"Generation failed: {e}")
            # Fallback to local provider
            response = await self._fallback_generate(sanitized_request, str(e))
        
        # Step 5: Confidence assessment and escalation
        if routing_decision.provider != "qwen_cpu":  # Skip confidence check for fallback
            confidence = await self._assess_confidence(response, sanitized_request)
            response.confidence = confidence
            
            # Escalate if confidence too low and not already using R1
            if (confidence < self.config.conf_threshold and 
                routing_decision.provider != "deepseek_r1"):
                
                escalation_decision = RoutingDecision(
                    provider="deepseek_r1",
                    reasoning="low_confidence_escalation", 
                    cot_budget=self.config.max_cot_tokens
                )
                
                try:
                    response = await self._generate_with_routing(sanitized_request, escalation_decision)
                    response.confidence = await self._assess_confidence(response, sanitized_request)
                    response.metadata["escalated"] = True
                    response.metadata["escalation_reason"] = "low_confidence"
                except Exception as e:
                    self.logger.warning(f"Escalation to R1 failed: {e}")
        
        # Step 6: Post-filtering and verification
        if self.post_guard:
            final_response, post_guard_result = await self.post_guard.process(response, sanitized_request)
            if post_guard_result.blocked:
                return self._create_blocked_response(post_guard_result.reason, start_time)
        else:
            final_response = response
            post_guard_result = None
        
        # Step 7: Budget tracking and audit logging
        await self._budget_tracker.record_usage(final_response)
        await self._audit_log(sanitized_request, final_response, routing_decision, pre_guard_result, post_guard_result)
        
        return final_response
    
    async def _determine_routing(self, request: GenRequest) -> 'RoutingDecision':
        """Determine which provider to use based on request characteristics and RAG support."""
        
        # Check if this is a hard problem
        is_hard = self._is_hard_problem(request.prompt)
        
        # RAG-Aware Routing: Get semantic support score
        support_score = await self._get_rag_support_score(request.prompt)
        
        # Enhanced routing logic based on RAG availability
        if support_score >= self.config.support_threshold:
            # High RAG support - use faster model with RAG-focused instructions
            self.logger.debug(f"High RAG support ({support_score:.2f}) - routing to DeepSeek Chat with RAG context")
            return RoutingDecision(
                provider="deepseek_chat",
                reasoning="high_rag_support",
                cot_budget=None,
                rag_enhanced=True
            )
        elif support_score < 0.3:
            # Low RAG support - novel question, escalate to reasoning model
            self.logger.debug(f"Low RAG support ({support_score:.2f}) - escalating to DeepSeek R1 for novel reasoning")
            return RoutingDecision(
                provider="deepseek_r1", 
                reasoning="novel_query_no_rag_support",
                cot_budget=self.config.max_cot_tokens,
                rag_enhanced=False
            )
        elif is_hard:
            # Hard problem with moderate RAG support - use thinking mode
            self.logger.debug(f"Hard problem with moderate RAG support ({support_score:.2f}) - using DeepSeek Thinking")
            return RoutingDecision(
                provider="deepseek_thinking", 
                reasoning="complex_query_with_context",
                cot_budget=min(self.config.max_cot_tokens, 3000),
                rag_enhanced=True
            )
        else:
            # Simple query - use chat model
            return RoutingDecision(
                provider="deepseek_chat",
                reasoning="simple_query",
                cot_budget=None,
                rag_enhanced=bool(support_score > 0.1)
            )
    
    async def _get_rag_support_score(self, prompt: str) -> float:
        """Get semantic similarity score from RAG system to determine context availability."""
        try:
            # Try to import and use the retriever if available
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
            
            from hivemind.rag.retriever import Retriever
            from hivemind.config import Settings
            
            settings = Settings()
            retriever = Retriever(settings.rag_index, settings.embed_model)
            
            if not retriever.is_ready:
                self.logger.debug("RAG retriever not ready, assuming low support")
                return 0.3  # Assume moderate support if RAG unavailable
            
            # Perform semantic search and get relevance scores
            docs = await retriever.search(prompt, k=3)
            
            if not docs:
                return 0.0  # No relevant documents found
            
            # Calculate average relevance score
            relevance_scores = [doc.get('score', 0.0) for doc in docs]
            avg_score = sum(relevance_scores) / len(relevance_scores)
            
            # Normalize score to 0-1 range (typical FAISS scores can vary)
            # Assuming scores > 0.8 are highly relevant
            normalized_score = min(avg_score / 0.8, 1.0)
            
            self.logger.debug(f"RAG support score: {normalized_score:.3f} (raw: {avg_score:.3f})")
            return normalized_score
            
        except Exception as e:
            self.logger.warning(f"Failed to get RAG support score: {e}")
            return 0.5  # Fallback to moderate support
    
    def _is_hard_problem(self, prompt: str) -> bool:
        """Detect if a prompt represents a hard problem requiring reasoning."""
        for pattern in self._hard_patterns:
            if pattern.search(prompt):
                return True
        return False
    
    async def _generate_with_routing(self, request: GenRequest, decision: 'RoutingDecision') -> GenResponse:
        """Generate response using the specified routing decision with circuit breaker protection."""
        try:
            response = await self._call_provider_with_circuit_breaker(decision.provider, request)
            response.metadata.update({
                "routing_decision": decision.provider,
                "routing_reasoning": decision.reasoning
            })
            return response
            
        except Exception as e:
            # If primary provider fails, attempt fallback
            self.logger.warning(f"Provider {decision.provider} failed: {e}")
            
            # Try fallback providers in order
            fallback_order = ["qwen_cpu"]  # Local fallback
            
            for fallback_provider in fallback_order:
                if fallback_provider == decision.provider:
                    continue  # Skip if it's the same provider that failed
                
                try:
                    response = await self._call_provider_with_circuit_breaker(fallback_provider, request)
                    response.metadata.update({
                        "routing_decision": fallback_provider,
                        "routing_reasoning": f"fallback_from_{decision.provider}",
                        "original_provider_failed": decision.provider,
                        "fallback_reason": str(e)
                    })
                    return response
                    
                except Exception as fallback_error:
                    self.logger.warning(f"Fallback provider {fallback_provider} also failed: {fallback_error}")
                    continue
            
            # All providers failed, raise the original error
            raise e
    
    async def _fallback_generate(self, request: GenRequest, error: str) -> GenResponse:
        """Generate response using local fallback provider."""
        qwen_provider = self.providers.get("qwen_cpu")
        if qwen_provider:
            response = await qwen_provider.generate(request)
            response.metadata["fallback_reason"] = error
            return response
        else:
            # Ultimate fallback
            return GenResponse(
                content="I apologize, but I'm currently unable to process your request due to system limitations.",
                provider="system_fallback",
                metadata={"error": error, "ultimate_fallback": True}
            )
    
    async def _assess_confidence(self, response: GenResponse, request: GenRequest) -> float:
        """Assess confidence in the generated response."""
        # Simple heuristic-based confidence assessment
        # In production, this could use a dedicated confidence model
        
        confidence = 0.7  # Base confidence
        
        # Adjust based on response length
        if len(response.content) < 50:
            confidence -= 0.2
        elif len(response.content) > 500:
            confidence += 0.1
        
        # Adjust based on provider
        if response.provider.startswith("deepseek_r1"):
            confidence += 0.2
        elif response.provider.startswith("deepseek_thinking"):
            confidence += 0.1
        elif response.provider.startswith("qwen_cpu"):
            confidence -= 0.3
        
        # Check for uncertainty indicators
        uncertainty_markers = ["i'm not sure", "i don't know", "uncertain", "maybe", "possibly"]
        content_lower = response.content.lower()
        for marker in uncertainty_markers:
            if marker in content_lower:
                confidence -= 0.15
                break
        
        return max(0.0, min(1.0, confidence))
    
    def _create_blocked_response(self, reason: str, start_time: float) -> GenResponse:
        """Create response for blocked requests."""
        latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        
        return GenResponse(
            content="I cannot provide a response to this request due to safety or policy restrictions.",
            provider="safety_filter",
            latency_ms=latency_ms,
            metadata={"blocked": True, "block_reason": reason}
        )
    
    def _create_budget_exceeded_response(self, budget_status: 'BudgetStatus', start_time: float) -> GenResponse:
        """Create response for budget exceeded scenarios."""
        latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        
        return GenResponse(
            content=f"Daily budget limit has been exceeded. Service will resume at {budget_status.next_reset_utc}.",
            provider="budget_limiter",
            latency_ms=latency_ms,
            metadata={
                "budget_exceeded": True,
                "next_reset": budget_status.next_reset_utc,
                "usage_tokens": budget_status.tokens_used,
                "usage_usd": budget_status.usd_spent
            }
        )
    
    async def _audit_log(self, request: GenRequest, response: GenResponse, routing: 'RoutingDecision', 
                        pre_guard=None, post_guard=None):
        """Log audit information for compliance and monitoring."""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "input_sha256": self._hash_content(request.prompt),
            "provider": response.provider,
            "confidence": response.confidence,
            "routing_decision": routing.provider,
            "routing_reasoning": routing.reasoning,
            "blocked": response.metadata.get("blocked", False),
            "escalated": response.metadata.get("escalated", False),
            "filters": {
                "pre_guard": pre_guard.status if pre_guard else "disabled",
                "post_guard": post_guard.status if post_guard else "disabled"
            },
            "tokens": {
                "prompt": response.prompt_tokens,
                "output": response.output_tokens
            },
            "cost_usd": response.cost_usd,
            "latency_ms": response.latency_ms
        }
        
        # In production, send to audit log service
        self.logger.info("Audit log", extra={"audit": audit_entry})
    
    def _hash_content(self, content: str) -> str:
        """Create SHA256 hash of content for audit logging."""
        import hashlib
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    async def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers including circuit breaker state."""
        status = {}
        for name, provider in self.providers.items():
            try:
                # Get basic health check
                health = await asyncio.wait_for(provider.health_check(), timeout=10)
                
                # Add circuit breaker information
                circuit_breaker = self.circuit_breakers.get(name)
                if circuit_breaker:
                    health.update({
                        "circuit_state": circuit_breaker.state.value,
                        "failure_count": circuit_breaker.failure_count,
                        "success_count": circuit_breaker.success_count,
                        "last_failure": circuit_breaker.last_failure_time.isoformat() if circuit_breaker.last_failure_time else None
                    })
                
                status[name] = health
                
            except Exception as e:
                # If health check fails, record the failure in circuit breaker
                circuit_breaker = self.circuit_breakers.get(name)
                if circuit_breaker:
                    circuit_breaker.record_failure()
                
                status[name] = {
                    "status": "error", 
                    "error": str(e),
                    "circuit_state": circuit_breaker.state.value if circuit_breaker else "unknown",
                    "failure_count": circuit_breaker.failure_count if circuit_breaker else 0
                }
        
        return status

@dataclass
class RoutingDecision:
    """Represents a routing decision made by the router."""
    provider: str
    reasoning: str
    cot_budget: Optional[int] = None
    rag_enhanced: bool = False

@dataclass 
class BudgetStatus:
    """Budget tracking status."""
    exceeded: bool
    tokens_used: int
    usd_spent: float
    next_reset_utc: str

class BudgetTracker:
    """Distributed budget tracker using Redis for stateful tracking across instances."""
    
    def __init__(self, config: RouterConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize Redis client
        self.redis_client = None
        self._initialize_redis()
        
        # Fallback in-memory tracking if Redis unavailable
        self._fallback_tokens = 0
        self._fallback_usd = 0.0
    

        # Expose testing-friendly properties mapping to fallback counters
        # These are used by unit tests to manipulate state without Redis
        @property
        def tokens_used(self) -> int:
            return int(getattr(self, "_fallback_tokens", 0))
        
        @tokens_used.setter
        def tokens_used(self, v: int) -> None:
            self._fallback_tokens = int(v)
        
        @property
        def usd_spent(self) -> float:
            return float(getattr(self, "_fallback_usd", 0.0))
        
        @usd_spent.setter
        def usd_spent(self, v: float) -> None:
            self._fallback_usd = float(v)

    def _initialize_redis(self):
        """Initialize Redis client for distributed budget tracking."""
        try:
            import redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            self.logger.info("Redis budget tracking initialized")
        except Exception as e:
            self.logger.warning(f"Redis unavailable, using fallback tracking: {e}")
            self.redis_client = None
    
    def _get_daily_key(self) -> str:
        """Get Redis key for today's budget tracking."""
        from datetime import datetime
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return f"liquid_hive:budget:daily:{today}"
    
    async def check_budget(self) -> BudgetStatus:
        """Check current budget status from Redis or fallback."""
        if self.redis_client:
            try:
                return await self._check_redis_budget()
            except Exception as e:
                self.logger.error(f"Redis budget check failed: {e}")
                return await self._check_fallback_budget()
        else:
            return await self._check_fallback_budget()
    
    async def _check_redis_budget(self) -> BudgetStatus:
        """Check budget using Redis distributed state."""
        daily_key = self._get_daily_key()
        
        # Get current usage atomically
        pipe = self.redis_client.pipeline()
        pipe.hget(daily_key, "tokens")
        pipe.hget(daily_key, "usd")
        results = pipe.execute()
        
        tokens_used = int(results[0] or 0)
        usd_spent = float(results[1] or 0.0)
        
        exceeded = (
            tokens_used >= self.config.max_oracle_tokens_per_day or
            usd_spent >= self.config.max_oracle_usd_per_day
        )
        
        # Calculate next reset time (UTC midnight)
        from datetime import datetime, timedelta
        tomorrow = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        next_reset = tomorrow.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Set TTL on the key to auto-expire after tomorrow
        self.redis_client.expire(daily_key, int((tomorrow - datetime.utcnow()).total_seconds()) + 3600)
        
        return BudgetStatus(
            exceeded=exceeded,
            tokens_used=tokens_used,
            usd_spent=usd_spent,
            next_reset_utc=next_reset
        )
    
    async def _check_fallback_budget(self) -> BudgetStatus:
        """Check budget using fallback in-memory tracking."""
        exceeded = (
            self._fallback_tokens >= self.config.max_oracle_tokens_per_day or
            self._fallback_usd >= self.config.max_oracle_usd_per_day
        )
        
        from datetime import datetime, timedelta
        next_reset = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00 UTC")
        
        return BudgetStatus(
            exceeded=exceeded,
            tokens_used=self._fallback_tokens,
            usd_spent=self._fallback_usd,
            next_reset_utc=next_reset
        )
    
    async def record_usage(self, response: GenResponse):
        """Record token and cost usage atomically."""
        tokens = response.prompt_tokens + response.output_tokens
        cost = response.cost_usd
        
        if self.redis_client:
            try:
                await self._record_redis_usage(tokens, cost)
            except Exception as e:
                self.logger.error(f"Redis usage recording failed: {e}")
                await self._record_fallback_usage(tokens, cost)
        else:
            await self._record_fallback_usage(tokens, cost)
    
    async def _record_redis_usage(self, tokens: int, cost: float):
        """Record usage in Redis with atomic increments."""
        daily_key = self._get_daily_key()
        
        # Atomic increment operations
        pipe = self.redis_client.pipeline()
        pipe.hincrby(daily_key, "tokens", tokens)
        pipe.hincrbyfloat(daily_key, "usd", cost)
        pipe.execute()
        
        self.logger.debug(f"Recorded usage: {tokens} tokens, ${cost:.4f}")
    
    async def _record_fallback_usage(self, tokens: int, cost: float):
        """Record usage in fallback in-memory tracking."""
        self._fallback_tokens += tokens
        self._fallback_usd += cost
        
        self.logger.debug(f"Fallback recorded usage: {tokens} tokens, ${cost:.4f}")
    
    async def reset_daily_budget(self) -> Dict[str, Any]:
        """Reset daily budget (admin operation)."""
        if self.redis_client:
            try:
                daily_key = self._get_daily_key()
                self.redis_client.delete(daily_key)
                return {"status": "redis_reset", "key": daily_key}
            except Exception as e:
                self.logger.error(f"Redis budget reset failed: {e}")
                return {"status": "redis_error", "error": str(e)}
        else:
            self._fallback_tokens = 0
            self._fallback_usd = 0.0
            return {
                "status": "fallback_reset"
            }