"""Dynamic model routing system for flexible AI model management."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class ModelProvider(str, Enum):
    """Supported model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    LOCAL = "local"
    CUSTOM = "custom"


class ModelStatus(str, Enum):
    """Model availability status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    DEPRECATED = "deprecated"


@dataclass
class ModelEndpoint:
    """Represents a model endpoint configuration."""
    
    # Identity
    model_id: str
    provider: ModelProvider
    model_name: str
    
    # Configuration
    api_endpoint: Optional[str] = None
    api_key_name: str = "default"
    
    # Capabilities
    max_tokens: int = 4096
    supports_streaming: bool = True
    supports_function_calling: bool = False
    context_window: int = 8192
    
    # Performance characteristics
    avg_latency_ms: float = 500.0
    cost_per_1k_tokens: float = 0.002
    quality_score: float = 0.8  # 0-1 scale
    
    # Routing configuration
    weight: float = 1.0  # Routing weight
    max_requests_per_hour: int = 1000
    timeout_seconds: int = 30
    
    # Status and metadata
    status: ModelStatus = ModelStatus.ACTIVE
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    
    # Runtime statistics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_used: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    @property 
    def requests_per_hour(self) -> float:
        """Calculate recent requests per hour."""
        if not self.last_used:
            return 0.0
        
        hours_since_last_use = (datetime.utcnow() - self.last_used).total_seconds() / 3600
        if hours_since_last_use == 0:
            return float(self.total_requests)
        
        return min(self.total_requests / hours_since_last_use, self.total_requests)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        # Convert datetime to string
        if data['last_used']:
            data['last_used'] = self.last_used.isoformat()
        # Convert enums to strings
        data['provider'] = self.provider.value
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelEndpoint":
        """Create from dictionary representation."""
        # Convert string back to datetime
        if data.get('last_used'):
            data['last_used'] = datetime.fromisoformat(data['last_used'])
        
        # Convert strings back to enums
        data['provider'] = ModelProvider(data['provider'])
        data['status'] = ModelStatus(data['status'])
        
        return cls(**data)


class RoutingStrategy(str, Enum):
    """Model routing strategies."""
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    LEAST_LATENCY = "least_latency"
    HIGHEST_SUCCESS = "highest_success"
    COST_OPTIMIZED = "cost_optimized"
    QUALITY_OPTIMIZED = "quality_optimized"
    LOAD_BALANCED = "load_balanced"


class ModelRouter:
    """Dynamic model routing system with performance monitoring."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the model router.
        
        Args:
            config_path: Path to model configuration file
        """
        self.config_path = config_path
        self.endpoints: Dict[str, ModelEndpoint] = {}
        self.routing_strategy = RoutingStrategy.WEIGHTED
        
        # Routing state
        self._round_robin_counter = 0
        self._performance_history = {}
        self._circuit_breaker_states = {}  # Track failed endpoints
        
        # Statistics
        self.routing_stats = {
            "total_routes": 0,
            "successful_routes": 0,
            "failed_routes": 0,
            "avg_routing_time_ms": 0.0,
            "circuit_breaker_trips": 0
        }
        
        logger.info("ModelRouter initialized", strategy=self.routing_strategy.value)
        
        # Load configuration if provided
        if config_path:
            asyncio.create_task(self._load_configuration())
        else:
            # Add default endpoints
            self._setup_default_endpoints()
    
    def _setup_default_endpoints(self):
        """Set up default model endpoints for demo purposes."""
        default_endpoints = [
            ModelEndpoint(
                model_id="gpt-4-turbo",
                provider=ModelProvider.OPENAI,
                model_name="gpt-4-turbo-preview",
                api_endpoint="https://api.openai.com/v1/chat/completions",
                api_key_name="OPENAI_API_KEY",
                max_tokens=128000,
                context_window=128000,
                avg_latency_ms=800.0,
                cost_per_1k_tokens=0.01,
                quality_score=0.95,
                weight=3.0,
                tags=["reasoning", "coding", "analysis"]
            ),
            ModelEndpoint(
                model_id="claude-3-sonnet",
                provider=ModelProvider.ANTHROPIC,
                model_name="claude-3-sonnet-20240229",
                api_endpoint="https://api.anthropic.com/v1/messages",
                api_key_name="ANTHROPIC_API_KEY",
                max_tokens=4096,
                context_window=200000,
                avg_latency_ms=1200.0,
                cost_per_1k_tokens=0.003,
                quality_score=0.92,
                weight=2.0,
                tags=["creative", "analysis", "long_context"]
            ),
            ModelEndpoint(
                model_id="deepseek-chat",
                provider=ModelProvider.DEEPSEEK,
                model_name="deepseek-chat",
                api_endpoint="https://api.deepseek.com/v1/chat/completions",
                api_key_name="DEEPSEEK_API_KEY",
                max_tokens=4096,
                context_window=32000,
                avg_latency_ms=600.0,
                cost_per_1k_tokens=0.0014,
                quality_score=0.88,
                weight=1.5,
                tags=["coding", "fast", "cost_effective"]
            ),
            ModelEndpoint(
                model_id="gpt-3.5-turbo",
                provider=ModelProvider.OPENAI,
                model_name="gpt-3.5-turbo",
                api_endpoint="https://api.openai.com/v1/chat/completions",
                api_key_name="OPENAI_API_KEY",
                max_tokens=4096,
                context_window=16384,
                avg_latency_ms=400.0,
                cost_per_1k_tokens=0.0015,
                quality_score=0.82,
                weight=1.0,
                tags=["fast", "cost_effective", "general"]
            )
        ]
        
        for endpoint in default_endpoints:
            self.endpoints[endpoint.model_id] = endpoint
        
        logger.info(
            "Default model endpoints configured",
            endpoint_count=len(self.endpoints),
            endpoints=list(self.endpoints.keys())
        )
    
    async def _load_configuration(self):
        """Load model configuration from file."""
        try:
            if not self.config_path:
                return
            
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            # Load endpoints
            for endpoint_data in config.get("endpoints", []):
                endpoint = ModelEndpoint.from_dict(endpoint_data)
                self.endpoints[endpoint.model_id] = endpoint
            
            # Load routing strategy
            strategy_name = config.get("routing_strategy", "weighted")
            self.routing_strategy = RoutingStrategy(strategy_name)
            
            logger.info(
                "Model configuration loaded",
                config_path=self.config_path,
                endpoints=len(self.endpoints),
                strategy=self.routing_strategy.value
            )
            
        except Exception as e:
            logger.error("Failed to load model configuration", error=str(e))
            # Fall back to default endpoints
            self._setup_default_endpoints()
    
    async def route_request(
        self,
        request_context: Dict[str, Any],
        preferred_model: Optional[str] = None,
        required_tags: Optional[List[str]] = None
    ) -> Optional[str]:
        """Route a request to the most appropriate model endpoint.
        
        Args:
            request_context: Context information about the request
            preferred_model: Specific model requested (if any)
            required_tags: Required capabilities/tags
            
        Returns:
            Model ID of the selected endpoint, or None if no suitable endpoint
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Filter available endpoints
            available_endpoints = await self._get_available_endpoints(required_tags)
            
            if not available_endpoints:
                logger.warning("No available endpoints for request", required_tags=required_tags)
                return None
            
            # Check for preferred model
            if preferred_model and preferred_model in available_endpoints:
                selected_endpoint = preferred_model
            else:
                # Apply routing strategy
                selected_endpoint = await self._apply_routing_strategy(
                    available_endpoints, 
                    request_context
                )
            
            if selected_endpoint:
                # Update endpoint statistics
                endpoint = self.endpoints[selected_endpoint]
                endpoint.total_requests += 1
                endpoint.last_used = datetime.utcnow()
                
                # Update routing statistics
                self.routing_stats["total_routes"] += 1
                self.routing_stats["successful_routes"] += 1
                
                # Update average routing time
                routing_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                self._update_avg_routing_time(routing_time_ms)
                
                logger.debug(
                    "Request routed successfully",
                    selected_endpoint=selected_endpoint,
                    routing_strategy=self.routing_strategy.value,
                    routing_time_ms=routing_time_ms
                )
                
                return selected_endpoint
            
            return None
            
        except Exception as e:
            logger.error("Error routing request", error=str(e))
            self.routing_stats["failed_routes"] += 1
            return None
    
    async def _get_available_endpoints(
        self, 
        required_tags: Optional[List[str]] = None
    ) -> Dict[str, ModelEndpoint]:
        """Get endpoints that are available and meet requirements.
        
        Args:
            required_tags: Required tags/capabilities
            
        Returns:
            Dictionary of available endpoints
        """
        available = {}
        
        for model_id, endpoint in self.endpoints.items():
            # Check basic availability
            if endpoint.status != ModelStatus.ACTIVE:
                continue
            
            # Check circuit breaker state
            if self._is_circuit_breaker_open(model_id):
                continue
            
            # Check rate limits
            if endpoint.requests_per_hour >= endpoint.max_requests_per_hour:
                logger.debug(
                    "Endpoint rate limited",
                    model_id=model_id,
                    current_rate=endpoint.requests_per_hour,
                    limit=endpoint.max_requests_per_hour
                )
                continue
            
            # Check required tags
            if required_tags:
                if not all(tag in endpoint.tags for tag in required_tags):
                    continue
            
            available[model_id] = endpoint
        
        return available
    
    async def _apply_routing_strategy(
        self,
        available_endpoints: Dict[str, ModelEndpoint],
        request_context: Dict[str, Any]
    ) -> Optional[str]:
        """Apply the configured routing strategy to select an endpoint.
        
        Args:
            available_endpoints: Available endpoints to choose from
            request_context: Request context for routing decisions
            
        Returns:
            Selected endpoint model ID
        """
        if not available_endpoints:
            return None
        
        endpoint_ids = list(available_endpoints.keys())
        
        if self.routing_strategy == RoutingStrategy.ROUND_ROBIN:
            selected_id = endpoint_ids[self._round_robin_counter % len(endpoint_ids)]
            self._round_robin_counter += 1
            return selected_id
        
        elif self.routing_strategy == RoutingStrategy.WEIGHTED:
            # Weighted random selection
            weights = [available_endpoints[eid].weight for eid in endpoint_ids]
            total_weight = sum(weights)
            
            if total_weight == 0:
                return endpoint_ids[0]  # Fallback to first
            
            # Simple weighted selection (would use random.choices in production)
            # For demo, select highest weight
            max_weight_idx = weights.index(max(weights))
            return endpoint_ids[max_weight_idx]
        
        elif self.routing_strategy == RoutingStrategy.LEAST_LATENCY:
            # Select endpoint with lowest average latency
            latencies = [(eid, available_endpoints[eid].avg_latency_ms) for eid in endpoint_ids]
            selected_id = min(latencies, key=lambda x: x[1])[0]
            return selected_id
        
        elif self.routing_strategy == RoutingStrategy.HIGHEST_SUCCESS:
            # Select endpoint with highest success rate
            success_rates = [(eid, available_endpoints[eid].success_rate) for eid in endpoint_ids]
            selected_id = max(success_rates, key=lambda x: x[1])[0]
            return selected_id
        
        elif self.routing_strategy == RoutingStrategy.COST_OPTIMIZED:
            # Select endpoint with lowest cost per token
            costs = [(eid, available_endpoints[eid].cost_per_1k_tokens) for eid in endpoint_ids]
            selected_id = min(costs, key=lambda x: x[1])[0]
            return selected_id
        
        elif self.routing_strategy == RoutingStrategy.QUALITY_OPTIMIZED:
            # Select endpoint with highest quality score
            qualities = [(eid, available_endpoints[eid].quality_score) for eid in endpoint_ids]
            selected_id = max(qualities, key=lambda x: x[1])[0]
            return selected_id
        
        elif self.routing_strategy == RoutingStrategy.LOAD_BALANCED:
            # Select endpoint with lowest current load
            loads = [(eid, available_endpoints[eid].requests_per_hour) for eid in endpoint_ids]
            selected_id = min(loads, key=lambda x: x[1])[0]
            return selected_id
        
        else:
            # Default to first available
            return endpoint_ids[0]
    
    def _is_circuit_breaker_open(self, model_id: str) -> bool:
        """Check if circuit breaker is open for an endpoint.
        
        Args:
            model_id: Model endpoint ID
            
        Returns:
            True if circuit breaker is open (endpoint unavailable)
        """
        if model_id not in self._circuit_breaker_states:
            return False
        
        cb_state = self._circuit_breaker_states[model_id]
        
        # Check if enough time has passed to try again
        if cb_state["open_until"] and datetime.utcnow() < cb_state["open_until"]:
            return True
        
        # Reset circuit breaker if timeout passed
        if cb_state["open_until"] and datetime.utcnow() >= cb_state["open_until"]:
            self._circuit_breaker_states[model_id] = {"failures": 0, "open_until": None}
            return False
        
        return False
    
    async def report_request_result(
        self,
        model_id: str,
        success: bool,
        latency_ms: Optional[float] = None,
        error: Optional[str] = None
    ):
        """Report the result of a request to update endpoint statistics.
        
        Args:
            model_id: Model endpoint that handled the request
            success: Whether the request succeeded
            latency_ms: Request latency in milliseconds
            error: Error message if request failed
        """
        try:
            if model_id not in self.endpoints:
                logger.warning("Unknown model ID in result report", model_id=model_id)
                return
            
            endpoint = self.endpoints[model_id]
            
            # Update success/failure counts
            if success:
                endpoint.successful_requests += 1
                
                # Reset circuit breaker on success
                if model_id in self._circuit_breaker_states:
                    self._circuit_breaker_states[model_id]["failures"] = 0
                    
            else:
                endpoint.failed_requests += 1
                
                # Update circuit breaker
                self._update_circuit_breaker(model_id, error)
            
            # Update latency if provided
            if latency_ms is not None:
                # Exponential moving average for latency
                alpha = 0.1  # Smoothing factor
                endpoint.avg_latency_ms = (
                    alpha * latency_ms + 
                    (1 - alpha) * endpoint.avg_latency_ms
                )
            
            # Update performance history for analysis
            self._update_performance_history(model_id, success, latency_ms)
            
            logger.debug(
                "Request result reported",
                model_id=model_id,
                success=success,
                latency_ms=latency_ms,
                success_rate=endpoint.success_rate
            )
            
        except Exception as e:
            logger.error("Error reporting request result", error=str(e))
    
    def _update_circuit_breaker(self, model_id: str, error: Optional[str]):
        """Update circuit breaker state after a failure.
        
        Args:
            model_id: Model endpoint ID
            error: Error message
        """
        if model_id not in self._circuit_breaker_states:
            self._circuit_breaker_states[model_id] = {"failures": 0, "open_until": None}
        
        cb_state = self._circuit_breaker_states[model_id]
        cb_state["failures"] += 1
        
        # Open circuit breaker after 5 failures
        failure_threshold = 5
        timeout_minutes = 5
        
        if cb_state["failures"] >= failure_threshold and not cb_state["open_until"]:
            cb_state["open_until"] = datetime.utcnow() + timedelta(minutes=timeout_minutes)
            self.routing_stats["circuit_breaker_trips"] += 1
            
            logger.warning(
                "Circuit breaker opened",
                model_id=model_id,
                failures=cb_state["failures"],
                timeout_until=cb_state["open_until"],
                error=error
            )
    
    def _update_performance_history(
        self,
        model_id: str,
        success: bool,
        latency_ms: Optional[float]
    ):
        """Update performance history for trend analysis.
        
        Args:
            model_id: Model endpoint ID
            success: Whether request succeeded
            latency_ms: Request latency
        """
        if model_id not in self._performance_history:
            self._performance_history[model_id] = []
        
        history = self._performance_history[model_id]
        
        # Add new data point
        data_point = {
            "timestamp": datetime.utcnow(),
            "success": success,
            "latency_ms": latency_ms
        }
        
        history.append(data_point)
        
        # Keep only last 100 data points
        if len(history) > 100:
            history.pop(0)
    
    def _update_avg_routing_time(self, routing_time_ms: float):
        """Update average routing time with exponential moving average.
        
        Args:
            routing_time_ms: Current routing time
        """
        alpha = 0.1  # Smoothing factor
        current_avg = self.routing_stats["avg_routing_time_ms"]
        
        if current_avg == 0:
            self.routing_stats["avg_routing_time_ms"] = routing_time_ms
        else:
            self.routing_stats["avg_routing_time_ms"] = (
                alpha * routing_time_ms + (1 - alpha) * current_avg
            )
    
    async def swap_route(self, from_model: str, to_model: str) -> bool:
        """Swap routing from one model to another.
        
        Args:
            from_model: Current model to route away from
            to_model: New model to route to
            
        Returns:
            True if swap was successful
        """
        try:
            if from_model not in self.endpoints:
                logger.error("Source model not found", from_model=from_model)
                return False
            
            if to_model not in self.endpoints:
                logger.error("Target model not found", to_model=to_model)
                return False
            
            # Get current weight of source model
            from_endpoint = self.endpoints[from_model]
            to_endpoint = self.endpoints[to_model]
            
            old_from_weight = from_endpoint.weight
            old_to_weight = to_endpoint.weight
            
            # Transfer weight
            to_endpoint.weight += from_endpoint.weight
            from_endpoint.weight = 0.1  # Minimal weight to keep endpoint available
            
            logger.info(
                "Model route swapped",
                from_model=from_model,
                to_model=to_model,
                old_from_weight=old_from_weight,
                old_to_weight=old_to_weight,
                new_from_weight=from_endpoint.weight,
                new_to_weight=to_endpoint.weight
            )
            
            return True
            
        except Exception as e:
            logger.error("Error swapping model route", error=str(e))
            return False
    
    async def set_routing_strategy(self, strategy: RoutingStrategy) -> bool:
        """Change the routing strategy.
        
        Args:
            strategy: New routing strategy to use
            
        Returns:
            True if strategy was changed successfully
        """
        try:
            old_strategy = self.routing_strategy
            self.routing_strategy = strategy
            
            # Reset round robin counter if switching to round robin
            if strategy == RoutingStrategy.ROUND_ROBIN:
                self._round_robin_counter = 0
            
            logger.info(
                "Routing strategy changed",
                old_strategy=old_strategy.value,
                new_strategy=strategy.value
            )
            
            return True
            
        except Exception as e:
            logger.error("Error changing routing strategy", error=str(e))
            return False
    
    async def get_endpoint_status(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status information for endpoints.
        
        Args:
            model_id: Specific model ID, or None for all endpoints
            
        Returns:
            Dictionary with endpoint status information
        """
        try:
            if model_id:
                if model_id not in self.endpoints:
                    return {"error": "Endpoint not found"}
                
                endpoint = self.endpoints[model_id]
                return {
                    "endpoint": endpoint.to_dict(),
                    "circuit_breaker": self._circuit_breaker_states.get(model_id, {}),
                    "performance_history": self._performance_history.get(model_id, [])[-10:]  # Last 10 requests
                }
            else:
                return {
                    "routing_strategy": self.routing_strategy.value,
                    "total_endpoints": len(self.endpoints),
                    "active_endpoints": len([e for e in self.endpoints.values() if e.status == ModelStatus.ACTIVE]),
                    "routing_stats": self.routing_stats,
                    "circuit_breakers": {
                        mid: cb for mid, cb in self._circuit_breaker_states.items()
                        if cb.get("open_until") or cb.get("failures", 0) > 0
                    },
                    "endpoints": {
                        model_id: {
                            "status": endpoint.status.value,
                            "success_rate": endpoint.success_rate,
                            "avg_latency_ms": endpoint.avg_latency_ms,
                            "total_requests": endpoint.total_requests,
                            "weight": endpoint.weight
                        }
                        for model_id, endpoint in self.endpoints.items()
                    }
                }
                
        except Exception as e:
            logger.error("Error getting endpoint status", error=str(e))
            return {"error": str(e)}
    
    async def add_endpoint(self, endpoint: ModelEndpoint) -> bool:
        """Add a new model endpoint.
        
        Args:
            endpoint: Model endpoint to add
            
        Returns:
            True if endpoint was added successfully
        """
        try:
            if endpoint.model_id in self.endpoints:
                logger.warning("Endpoint already exists", model_id=endpoint.model_id)
                return False
            
            self.endpoints[endpoint.model_id] = endpoint
            
            logger.info(
                "Model endpoint added",
                model_id=endpoint.model_id,
                provider=endpoint.provider.value,
                model_name=endpoint.model_name
            )
            
            return True
            
        except Exception as e:
            logger.error("Error adding endpoint", error=str(e))
            return False
    
    async def remove_endpoint(self, model_id: str) -> bool:
        """Remove a model endpoint.
        
        Args:
            model_id: Model endpoint ID to remove
            
        Returns:
            True if endpoint was removed successfully
        """
        try:
            if model_id not in self.endpoints:
                logger.warning("Endpoint not found", model_id=model_id)
                return False
            
            # Clean up related state
            if model_id in self._circuit_breaker_states:
                del self._circuit_breaker_states[model_id]
            
            if model_id in self._performance_history:
                del self._performance_history[model_id]
            
            # Remove endpoint
            del self.endpoints[model_id]
            
            logger.info("Model endpoint removed", model_id=model_id)
            
            return True
            
        except Exception as e:
            logger.error("Error removing endpoint", error=str(e))
            return False
    
    async def save_configuration(self, config_path: str) -> bool:
        """Save current configuration to file.
        
        Args:
            config_path: Path to save configuration
            
        Returns:
            True if configuration was saved successfully
        """
        try:
            config = {
                "routing_strategy": self.routing_strategy.value,
                "endpoints": [endpoint.to_dict() for endpoint in self.endpoints.values()]
            }
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2, default=str)
            
            logger.info("Model configuration saved", config_path=config_path)
            return True
            
        except Exception as e:
            logger.error("Error saving configuration", error=str(e))
            return False