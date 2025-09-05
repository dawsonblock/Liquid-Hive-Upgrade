# Backend Development Guide

This guide covers the Python-based backend system, including core modules, APIs, and development practices.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Core Modules](#core-modules)
- [API Development](#api-development)
- [Oracle Provider System](#oracle-provider-system)
- [Swarm Intelligence](#swarm-intelligence)
- [Security & Authentication](#security--authentication)
- [Development Setup](#development-setup)
- [Testing](#testing)
- [Deployment](#deployment)

## Architecture Overview

The backend is built with:
- **FastAPI** for REST API framework
- **Redis** for distributed state and caching
- **PostgreSQL** for persistent storage
- **WebSocket** for real-time communication
- **Pydantic** for data validation

```mermaid
graph TB
    A[FastAPI Server] --> B[Oracle Manager]
    A --> C[Swarm Protocol]
    A --> D[Arena Service]
    A --> E[Security Layer]
    
    B --> F[Provider Adapters]
    C --> G[Redis Cluster]
    D --> H[Model Evaluation]
    E --> I[Secrets Manager]
    
    F --> J[OpenAI Provider]
    F --> K[Anthropic Provider]
    F --> L[DeepSeek Provider]
    F --> M[Qwen Provider]
```

## Core Modules

### Oracle Provider System

#### Base Provider Interface

Located in `src/oracle/base.py`:

```python
from typing import Protocol, Optional, Any
from dataclasses import dataclass

@dataclass
class ProviderConfig:
    """Configuration for an Oracle Provider."""
    name: str
    kind: str  # 'openai', 'anthropic', 'deepseek', etc.
    base_url: str
    api_key_env: Optional[str] = None
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    role: Optional[str] = None
    cost_profile: Optional[str] = None

class OracleProvider(Protocol):
    """Protocol defining the interface for Oracle Providers."""
    
    async def generate(
        self, 
        prompt: str, 
        **kwargs: Any
    ) -> dict[str, Any]:
        """Generate a response from the provider."""
        ...
    
    async def health_check(self) -> dict[str, Any]:
        """Check provider health and availability."""
        ...
```

#### Provider Manager

Located in `src/oracle/manager.py`:

```python
class ProviderManager:
    """Manages Oracle Provider configuration and routing."""
    
    def __init__(self, config_path: str = "/app/config/providers.yaml") -> None:
        self.config_path = config_path
        self.routing: dict[str, Any] = {}
        self.providers_cfg: dict[str, ProviderConfig] = {}
        self.policies: dict[str, Any] = {}
        self.admin: dict[str, Any] = {}

    def load(self) -> tuple[dict[str, ProviderConfig], dict[str, Any]]:
        """Load provider configurations from YAML."""
        data = self._load_yaml()
        self.routing = data.get("routing", {})
        self.policies = data.get("policies", {})
        self.admin = data.get("admin", {})

        providers: dict[str, ProviderConfig] = {}
        for name, cfg in (data.get("providers", {}) or {}).items():
            providers[name] = ProviderConfig(
                name=name,
                kind=str(cfg.get("kind")),
                base_url=str(cfg.get("base_url")),
                api_key_env=cfg.get("api_key_env"),
                model=cfg.get("model"),
                max_tokens=cfg.get("max_tokens"),
                role=cfg.get("role"),
                cost_profile=cfg.get("cost_profile"),
            )
        self.providers_cfg = providers
        return providers, self.routing

    def resolve_api_key(self, cfg: ProviderConfig) -> Optional[str]:
        """Resolve API key from environment or secrets manager."""
        if not cfg.api_key_env:
            return None
        # Environment first. External secrets manager integration can be added here
        val = os.getenv(cfg.api_key_env)
        return val
```

**Usage Example:**
```python
# Initialize provider manager
manager = ProviderManager("/app/config/providers.yaml")
providers, routing = manager.load()

# Get provider configuration
openai_config = providers.get("openai-gpt4o")
api_key = manager.resolve_api_key(openai_config)
```

#### Individual Providers

**OpenAI Provider (`src/oracle/openai.py`):**
```python
class OpenAIProvider:
    """OpenAI API provider implementation."""
    
    def __init__(self, config: ProviderConfig, api_key: str):
        self.config = config
        self.api_key = api_key
        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=config.base_url
        )
    
    async def generate(self, prompt: str, **kwargs) -> dict[str, Any]:
        """Generate completion using OpenAI API."""
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model or "gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config.max_tokens or 2000,
                **kwargs
            )
            
            return {
                "content": response.choices[0].message.content,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def health_check(self) -> dict[str, Any]:
        """Check OpenAI API health."""
        try:
            # Simple test request
            await self.generate("Hello", max_tokens=1)
            return {"status": "healthy", "provider": "openai"}
        except Exception as e:
            return {"status": "error", "provider": "openai", "error": str(e)}
```

### Swarm Intelligence System

#### Core Components

Located in `src/hivemind/swarm_protocol.py`:

```python
@dataclass
class SwarmTask:
    """Represents a task that can be delegated across the swarm."""
    task_id: str
    task_type: str
    payload: dict[str, Any]
    requester_id: str
    priority: int = 1
    timeout_seconds: int = 300
    created_at: float = None
    assigned_to: Optional[str] = None
    status: str = "pending"  # pending, assigned, completed, failed, timeout
    result: Optional[dict[str, Any]] = None

@dataclass
class SwarmNode:
    """Represents a node in the swarm network."""
    node_id: str
    capabilities: list[str]
    status: str = "active"  # active, busy, offline
    last_heartbeat: float = None
    current_load: float = 0.0
    tasks_completed: int = 0
    average_response_time: float = 0.0

class SwarmCoordinator:
    """Coordinates task delegation and swarm state management."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.node_id = str(uuid.uuid4())
        self.capabilities: list[str] = []
        self.is_running = False

    async def connect(self) -> None:
        """Connect to Redis and initialize swarm participation."""
        if redis is None:
            raise RuntimeError("redis package not installed")
        
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        await self.redis_client.ping()
        
        # Register this node
        await self._register_node()
        self.is_running = True

    async def delegate_task(
        self, 
        task_type: str, 
        payload: dict[str, Any],
        priority: int = 1,
        timeout_seconds: int = 300,
        required_capabilities: Optional[list[str]] = None
    ) -> str:
        """Delegate a task to the swarm for distributed processing."""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        task = SwarmTask(
            task_id=task_id,
            task_type=task_type,
            payload=payload,
            requester_id=self.node_id,
            priority=priority,
            timeout_seconds=timeout_seconds
        )
        
        # Store task in Redis
        task_key = f"swarm:task:{task_id}"
        await self.redis_client.setex(
            task_key,
            timeout_seconds + 60,  # Extra buffer
            json.dumps(asdict(task))
        )
        
        # Add to priority queue
        await self.redis_client.zadd(
            "swarm:task_queue",
            {task_id: priority}
        )
        
        # Publish task notification
        await self.redis_client.publish(
            "swarm:new_task",
            json.dumps({
                "task_id": task_id,
                "task_type": task_type,
                "required_capabilities": required_capabilities or []
            })
        )
        
        return task_id

    async def get_task_result(self, task_id: str) -> Optional[dict[str, Any]]:
        """Get the result of a completed task."""
        task_key = f"swarm:task:{task_id}"
        task_data = await self.redis_client.get(task_key)
        
        if not task_data:
            return None
        
        task = SwarmTask(**json.loads(task_data))
        
        if task.status == "completed":
            return task.result
        elif task.status == "failed":
            return {"error": "Task failed", "task_id": task_id}
        else:
            return {"status": task.status, "task_id": task_id}

    async def get_swarm_status(self) -> dict[str, Any]:
        """Get overall swarm health and statistics."""
        # Get active nodes
        nodes_data = await self.redis_client.hgetall("swarm:nodes")
        active_nodes = []
        
        for node_id, node_data in nodes_data.items():
            node = SwarmNode(**json.loads(node_data))
            if time.time() - node.last_heartbeat < 60:  # Active within last minute
                active_nodes.append(node)
        
        # Get pending tasks
        pending_tasks = await self.redis_client.zcard("swarm:task_queue")
        
        return {
            "total_nodes": len(nodes_data),
            "active_nodes": len(active_nodes),
            "pending_tasks": pending_tasks,
            "node_utilization": sum(n.current_load for n in active_nodes) / len(active_nodes) if active_nodes else 0,
            "nodes": [asdict(node) for node in active_nodes]
        }
```

**Usage Example:**
```python
# Initialize swarm coordinator
coordinator = SwarmCoordinator("redis://localhost:6379")
await coordinator.connect()

# Delegate a task
task_id = await coordinator.delegate_task(
    task_type="text_analysis",
    payload={
        "text": "Large document to analyze...",
        "analysis_type": "sentiment"
    },
    priority=2,
    required_capabilities=["nlp", "sentiment_analysis"]
)

# Check task status
result = await coordinator.get_task_result(task_id)
print(f"Task result: {result}")

# Get swarm status
status = await coordinator.get_swarm_status()
print(f"Active nodes: {status['active_nodes']}")
```

### Security & Secrets Management

#### Secrets Manager

Located in `src/hivemind/secrets_manager.py`:

```python
from enum import Enum
from typing import Optional, Dict, Any
import os
import json
import logging

class SecretProvider(Enum):
    """Supported secret providers."""
    ENVIRONMENT = "environment"
    FILE = "file"
    VAULT = "vault"
    AWS_SECRETS_MANAGER = "aws_secrets_manager"

class SecretsManager:
    """Centralized secrets management with multiple provider support."""
    
    def __init__(self, provider: SecretProvider = SecretProvider.ENVIRONMENT):
        self.provider = provider
        self.logger = logging.getLogger(__name__)
        self._cache: Dict[str, Any] = {}
        
    async def get_secret(self, key: str, default: Any = None) -> Any:
        """Retrieve a secret by key."""
        # Check cache first
        if key in self._cache:
            return self._cache[key]
        
        try:
            if self.provider == SecretProvider.ENVIRONMENT:
                value = os.getenv(key, default)
            elif self.provider == SecretProvider.FILE:
                value = await self._get_from_file(key, default)
            elif self.provider == SecretProvider.VAULT:
                value = await self._get_from_vault(key, default)
            elif self.provider == SecretProvider.AWS_SECRETS_MANAGER:
                value = await self._get_from_aws(key, default)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
            
            # Cache the result
            if value is not None:
                self._cache[key] = value
            
            return value
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve secret '{key}': {e}")
            return default
    
    async def set_secret(self, key: str, value: Any) -> bool:
        """Store a secret."""
        try:
            if self.provider == SecretProvider.ENVIRONMENT:
                os.environ[key] = str(value)
            elif self.provider == SecretProvider.FILE:
                await self._set_to_file(key, value)
            elif self.provider == SecretProvider.VAULT:
                await self._set_to_vault(key, value)
            elif self.provider == SecretProvider.AWS_SECRETS_MANAGER:
                await self._set_to_aws(key, value)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
            
            # Update cache
            self._cache[key] = value
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store secret '{key}': {e}")
            return False
    
    async def delete_secret(self, key: str) -> bool:
        """Delete a secret."""
        try:
            if self.provider == SecretProvider.ENVIRONMENT:
                os.environ.pop(key, None)
            elif self.provider == SecretProvider.FILE:
                await self._delete_from_file(key)
            # ... other providers
            
            # Remove from cache
            self._cache.pop(key, None)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete secret '{key}': {e}")
            return False
    
    async def list_secrets(self) -> list[str]:
        """List available secret keys (names only)."""
        try:
            if self.provider == SecretProvider.ENVIRONMENT:
                return list(os.environ.keys())
            elif self.provider == SecretProvider.FILE:
                return await self._list_from_file()
            # ... other providers
            
        except Exception as e:
            self.logger.error(f"Failed to list secrets: {e}")
            return []

    def clear_cache(self) -> None:
        """Clear the secrets cache."""
        self._cache.clear()
```

**Usage Example:**
```python
# Initialize secrets manager
secrets = SecretsManager(SecretProvider.ENVIRONMENT)

# Get a secret
api_key = await secrets.get_secret("OPENAI_API_KEY")

# Set a secret
await secrets.set_secret("NEW_API_KEY", "sk-...")

# List secrets
secret_names = await secrets.list_secrets()
```

### Caching System

#### Semantic Cache

Located in `src/hivemind/cache/semantic_cache.py`:

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Any, List
import time
import hashlib
import json

class CacheStrategy(Enum):
    """Cache eviction strategies."""
    LRU = "lru"
    TTL = "ttl"
    SEMANTIC_SIMILARITY = "semantic_similarity"

@dataclass
class CacheEntry:
    """Represents a cached item with metadata."""
    key: str
    value: Any
    created_at: float
    accessed_at: float
    access_count: int
    ttl: Optional[float] = None
    similarity_threshold: float = 0.9
    embedding: Optional[List[float]] = None
    metadata: Optional[dict] = None

class SemanticCache:
    """High-performance semantic cache with multiple eviction strategies."""
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[float] = 3600,  # 1 hour
        strategy: CacheStrategy = CacheStrategy.SEMANTIC_SIMILARITY
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.strategy = strategy
        self._cache: dict[str, CacheEntry] = {}
        self._access_order: list[str] = []  # For LRU
        
    def _generate_key(self, prompt: str, model: str, **kwargs) -> str:
        """Generate a cache key from input parameters."""
        key_data = {
            "prompt": prompt,
            "model": model,
            **kwargs
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if a cache entry has expired."""
        if entry.ttl is None:
            return False
        return time.time() - entry.created_at > entry.ttl
    
    async def get(
        self, 
        prompt: str, 
        model: str, 
        similarity_threshold: float = 0.9,
        **kwargs
    ) -> Optional[Any]:
        """Retrieve from cache with semantic similarity matching."""
        key = self._generate_key(prompt, model, **kwargs)
        
        # Exact match first
        if key in self._cache:
            entry = self._cache[key]
            if not self._is_expired(entry):
                # Update access metadata
                entry.accessed_at = time.time()
                entry.access_count += 1
                self._update_access_order(key)
                return entry.value
            else:
                # Remove expired entry
                del self._cache[key]
        
        # Semantic similarity search
        if self.strategy == CacheStrategy.SEMANTIC_SIMILARITY:
            return await self._semantic_search(
                prompt, model, similarity_threshold, **kwargs
            )
        
        return None
    
    async def set(
        self, 
        prompt: str, 
        model: str, 
        value: Any,
        ttl: Optional[float] = None,
        embedding: Optional[List[float]] = None,
        **kwargs
    ) -> None:
        """Store in cache with optional semantic embedding."""
        key = self._generate_key(prompt, model, **kwargs)
        
        # Check if we need to evict
        if len(self._cache) >= self.max_size:
            await self._evict()
        
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            accessed_at=time.time(),
            access_count=1,
            ttl=ttl or self.default_ttl,
            embedding=embedding,
            metadata={"prompt": prompt, "model": model, **kwargs}
        )
        
        self._cache[key] = entry
        self._update_access_order(key)
    
    async def _semantic_search(
        self, 
        prompt: str, 
        model: str, 
        threshold: float,
        **kwargs
    ) -> Optional[Any]:
        """Search for semantically similar cached entries."""
        if not hasattr(self, '_embeddings_client'):
            return None  # No embedding service available
        
        # Generate embedding for the query
        query_embedding = await self._generate_embedding(prompt)
        
        best_match = None
        best_similarity = 0.0
        
        for entry in self._cache.values():
            if (entry.embedding is not None and 
                entry.metadata.get("model") == model and
                not self._is_expired(entry)):
                
                similarity = self._cosine_similarity(query_embedding, entry.embedding)
                
                if similarity > threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_match = entry
        
        if best_match:
            # Update access metadata
            best_match.accessed_at = time.time()
            best_match.access_count += 1
            self._update_access_order(best_match.key)
            return best_match.value
        
        return None
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        
        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = math.sqrt(sum(x * x for x in a))
        magnitude_b = math.sqrt(sum(x * x for x in b))
        
        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0
        
        return dot_product / (magnitude_a * magnitude_b)
    
    async def _evict(self) -> None:
        """Evict entries based on the configured strategy."""
        if self.strategy == CacheStrategy.LRU:
            # Remove least recently used
            oldest_key = self._access_order[0]
            del self._cache[oldest_key]
            self._access_order.remove(oldest_key)
            
        elif self.strategy == CacheStrategy.TTL:
            # Remove expired entries first
            expired_keys = [
                key for key, entry in self._cache.items()
                if self._is_expired(entry)
            ]
            for key in expired_keys:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
            
            # If still over capacity, use LRU
            if len(self._cache) >= self.max_size:
                oldest_key = self._access_order[0]
                del self._cache[oldest_key]
                self._access_order.remove(oldest_key)
    
    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self._cache)
        expired_entries = sum(1 for entry in self._cache.values() if self._is_expired(entry))
        
        return {
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "active_entries": total_entries - expired_entries,
            "max_size": self.max_size,
            "utilization": total_entries / self.max_size,
            "strategy": self.strategy.value,
            "total_access_count": sum(entry.access_count for entry in self._cache.values())
        }
```

**Usage Example:**
```python
# Initialize semantic cache
cache = SemanticCache(
    max_size=1000,
    default_ttl=3600,
    strategy=CacheStrategy.SEMANTIC_SIMILARITY
)

# Store in cache
await cache.set(
    prompt="What is machine learning?",
    model="gpt-4o",
    value={"response": "Machine learning is..."},
    embedding=embedding_vector
)

# Retrieve from cache
result = await cache.get(
    prompt="What is ML?",  # Semantically similar
    model="gpt-4o",
    similarity_threshold=0.8
)

# Get cache statistics
stats = cache.get_stats()
print(f"Cache utilization: {stats['utilization']:.2%}")
```

## API Development

### FastAPI Application Structure

Main server located in `src/unified_runtime/server.py`:

```python
from fastapi import FastAPI, WebSocket, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from pydantic import BaseModel
import logging

# Initialize FastAPI app
app = FastAPI(
    title="Liquid-Hive-Upgrade API",
    description="Oracle Provider Router with Swarm Intelligence",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Dependency injection
async def get_current_user(token: str = Depends(security)):
    """Validate API token and return user info."""
    # Implement token validation logic
    return {"user_id": "user_123"}

# Health check endpoint
@app.get("/api/healthz")
async def health_check():
    """System health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {
            "database": "healthy",
            "redis": "healthy",
            "providers": await check_providers_health()
        }
    }

# Chat endpoint
@app.post("/api/chat")
async def chat_endpoint(
    q: str,
    user: dict = Depends(get_current_user)
):
    """Send a chat message to the AI system."""
    try:
        # Route to appropriate provider
        provider = await select_optimal_provider(q)
        
        # Generate response
        response = await provider.generate(q)
        
        # Store in cache
        await cache.set(q, provider.name, response)
        
        return {
            "message": response["content"],
            "model_used": response["model"],
            "provider": provider.name,
            "tokens_used": response.get("usage", {}),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# WebSocket endpoint for streaming
@app.websocket("/api/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time streaming chat."""
    await websocket.accept()
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            message = data.get("message", "")
            stream = data.get("stream", True)
            
            if stream:
                await handle_streaming_generation(websocket, message)
            else:
                await handle_non_streaming_generation(websocket, message)
                
    except WebSocketDisconnect:
        logging.info("WebSocket client disconnected")
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        await websocket.send_json({"error": str(e)})

async def handle_streaming_generation(websocket: WebSocket, query: str):
    """Handle streaming response generation."""
    provider = await select_optimal_provider(query)
    
    async for token in provider.stream_generate(query):
        await websocket.send_json({
            "type": "token",
            "content": token,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    await websocket.send_json({
        "type": "end",
        "timestamp": datetime.utcnow().isoformat()
    })
```

### Request/Response Models

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., min_length=1, max_length=10000)
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=4000)
    stream: bool = False

class ChatResponse(BaseModel):
    """Chat response model."""
    message: str
    model_used: str
    provider: str
    tokens_used: Dict[str, int]
    cost: Optional[float] = None
    reasoning: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    timestamp: datetime

class ArenaSubmitRequest(BaseModel):
    """Arena task submission request."""
    input: str = Field(..., min_length=1)
    reference: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ArenaSubmitResponse(BaseModel):
    """Arena task submission response."""
    task_id: str
    status: str
    estimated_completion: datetime
    models_to_evaluate: List[str]

class SwarmTaskRequest(BaseModel):
    """Swarm task delegation request."""
    task_type: str
    payload: Dict[str, Any]
    priority: int = Field(1, ge=1, le=10)
    timeout_seconds: int = Field(300, ge=10, le=3600)
    required_capabilities: Optional[List[str]] = None

class SwarmTaskResponse(BaseModel):
    """Swarm task delegation response."""
    task_id: str
    status: str
    estimated_completion: datetime
    assigned_nodes: List[str]
    created_at: datetime
```

## Development Setup

### Prerequisites

- Python 3.11+
- Redis 6+
- PostgreSQL 13+ (optional)

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### Environment Configuration

Create `.env` file:
```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true

# Database
DATABASE_URL=postgresql://user:pass@localhost/liquid_hive
REDIS_URL=redis://localhost:6379

# Oracle Provider API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...

# Security
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Running the Server

```bash
# Development server with auto-reload
uvicorn src.unified_runtime.server:app --reload --host 0.0.0.0 --port 8000

# Production server
uvicorn src.unified_runtime.server:app --host 0.0.0.0 --port 8000 --workers 4
```

## Testing

### Unit Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_oracle_providers.py

# Run with verbose output
pytest -v
```

### Integration Tests

```bash
# Run integration tests (requires running services)
pytest tests/integration/ -m integration

# Run API tests
pytest tests/api/ -m api
```

### Example Test

```python
import pytest
from fastapi.testclient import TestClient
from src.unified_runtime.server import app

client = TestClient(app)

def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/api/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

@pytest.mark.asyncio
async def test_swarm_coordinator():
    """Test swarm coordination functionality."""
    from src.hivemind.swarm_protocol import SwarmCoordinator
    
    coordinator = SwarmCoordinator("redis://localhost:6379")
    await coordinator.connect()
    
    # Test task delegation
    task_id = await coordinator.delegate_task(
        task_type="test",
        payload={"data": "test"},
        priority=1
    )
    
    assert task_id.startswith("task_")
    
    # Test task retrieval
    result = await coordinator.get_task_result(task_id)
    assert result is not None
```

## Deployment

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/healthz || exit 1

# Start application
CMD ["uvicorn", "src.unified_runtime.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: liquid-hive-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: liquid-hive-backend
  template:
    metadata:
      labels:
        app: liquid-hive-backend
    spec:
      containers:
      - name: backend
        image: liquid-hive/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /api/healthz
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/healthz
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Production Configuration

```python
# config/production.py
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    
    # Database
    database_url: str
    redis_url: str
    
    # Security
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Oracle Providers
    openai_api_key: str
    anthropic_api_key: str
    deepseek_api_key: str
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Performance
    worker_processes: int = 4
    max_connections: int = 1000
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

## Best Practices

### Code Organization

1. **Follow domain-driven design patterns**
2. **Use dependency injection for services**
3. **Implement proper error handling**
4. **Use type hints throughout**
5. **Follow PEP 8 style guidelines**

### Performance

1. **Use async/await for I/O operations**
2. **Implement connection pooling**
3. **Use caching strategically**
4. **Monitor resource usage**
5. **Implement proper logging**

### Security

1. **Validate all input data**
2. **Use proper authentication/authorization**
3. **Secure secret management**
4. **Implement rate limiting**
5. **Regular security audits**

### Monitoring

1. **Implement health checks**
2. **Use structured logging**
3. **Monitor key metrics**
4. **Set up alerting**
5. **Performance profiling**

## Troubleshooting

### Common Issues

**Redis Connection Errors:**
- Check Redis server status
- Verify connection string
- Check network connectivity

**Provider API Failures:**
- Verify API keys
- Check rate limits
- Monitor provider status

**Performance Issues:**
- Check database query performance
- Monitor memory usage
- Review caching strategy

**WebSocket Connection Issues:**
- Verify WebSocket endpoint
- Check CORS configuration
- Monitor connection lifecycle