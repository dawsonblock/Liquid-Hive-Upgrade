# API Endpoints Reference

This document provides comprehensive documentation for all REST API endpoints in the Liquid-Hive-Upgrade system.

## Table of Contents

- [Health & Status](#health--status)
- [Chat & Inference](#chat--inference)
- [Vision & Multimodal](#vision--multimodal)
- [Oracle Provider Management](#oracle-provider-management)
- [Arena & Evaluation](#arena--evaluation)
- [Swarm Intelligence](#swarm-intelligence)
- [Configuration & Admin](#configuration--admin)
- [Security & Secrets](#security--secrets)

## Health & Status

### GET /api/healthz

Check system health and availability.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "1.0.0",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "providers": {
      "openai": "healthy",
      "anthropic": "healthy",
      "deepseek": "degraded"
    }
  },
  "uptime": 86400
}
```

**Example:**
```bash
curl -X GET "https://api.liquid-hive.dev/api/healthz" \
  -H "x-api-key: your-api-key"
```

---

## Chat & Inference

### POST /api/chat

Send a chat message to the AI system.

**Parameters:**
- `q` (query parameter): The user's message/question

**Request:**
```http
POST /api/chat?q=Hello%20world
Content-Type: application/json
x-api-key: your-api-key
```

**Response:**
```json
{
  "message": "Hello! How can I assist you today?",
  "model_used": "gpt-4o",
  "provider": "openai",
  "tokens_used": {
    "input": 12,
    "output": 28,
    "total": 40
  },
  "cost": 0.0024,
  "reasoning": "User provided a greeting, responding with helpful acknowledgment",
  "context": {
    "session_id": "sess_123",
    "conversation_length": 1
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

**Example:**
```python
import httpx

async def chat_example():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.liquid-hive.dev/api/chat",
            params={"q": "What is machine learning?"},
            headers={"x-api-key": "your-api-key"}
        )
        return response.json()
```

### WebSocket /ws/chat

Real-time streaming chat interface.

**Connection:**
```javascript
const ws = new WebSocket('wss://api.liquid-hive.dev/ws/chat');
```

**Message Format:**
```json
{
  "type": "chat",
  "message": "Your question here",
  "stream": true,
  "model": "gpt-4o",
  "temperature": 0.7,
  "max_tokens": 2000
}
```

**Response Stream:**
```json
{"type": "token", "content": "Hello"}
{"type": "token", "content": "!"}
{"type": "token", "content": " How"}
{"type": "end", "total_tokens": 150, "cost": 0.003}
```

---

## Vision & Multimodal

### POST /api/vision

Analyze images with AI vision capabilities.

**Parameters:**
- `grounding_required` (query parameter): Whether to include object detection/grounding

**Request:**
```http
POST /api/vision?grounding_required=true
Content-Type: multipart/form-data
x-api-key: your-api-key

--boundary
Content-Disposition: form-data; name="image"; filename="image.jpg"
Content-Type: image/jpeg

[binary image data]
--boundary
Content-Disposition: form-data; name="prompt"

Describe what you see in this image
--boundary--
```

**Response:**
```json
{
  "description": "This image shows a bustling city street with tall buildings...",
  "objects_detected": [
    {
      "label": "car",
      "confidence": 0.95,
      "bbox": [100, 200, 300, 400]
    },
    {
      "label": "person",
      "confidence": 0.88,
      "bbox": [150, 100, 200, 350]
    }
  ],
  "model_used": "gpt-4-vision",
  "processing_time": 2.3,
  "cost": 0.015
}
```

**Example:**
```python
async def vision_example():
    async with httpx.AsyncClient() as client:
        with open("image.jpg", "rb") as f:
            files = {"image": f}
            data = {"prompt": "What's in this image?"}
            response = await client.post(
                "https://api.liquid-hive.dev/api/vision",
                params={"grounding_required": "true"},
                files=files,
                data=data,
                headers={"x-api-key": "your-api-key"}
            )
        return response.json()
```

---

## Oracle Provider Management

### GET /api/providers

List all available oracle providers and their status.

**Response:**
```json
{
  "providers": [
    {
      "name": "openai-gpt4o",
      "kind": "openai",
      "status": "healthy",
      "model": "gpt-4o",
      "cost_per_token": 0.00006,
      "max_tokens": 4096,
      "capabilities": ["text", "vision", "function_calling"],
      "latency_avg": 1200,
      "success_rate": 0.995
    },
    {
      "name": "anthropic-claude",
      "kind": "anthropic",
      "status": "healthy",
      "model": "claude-3-sonnet",
      "cost_per_token": 0.000045,
      "max_tokens": 4096,
      "capabilities": ["text", "function_calling"],
      "latency_avg": 800,
      "success_rate": 0.998
    }
  ],
  "routing_policy": "cost_optimized",
  "total_requests_today": 15420
}
```

### GET /api/providers/{provider_name}/health

Check health of a specific provider.

**Response:**
```json
{
  "provider": "openai-gpt4o",
  "status": "healthy",
  "last_check": "2024-01-01T00:00:00Z",
  "response_time": 1200,
  "error_rate": 0.005,
  "quota_remaining": 95000,
  "next_reset": "2024-01-02T00:00:00Z"
}
```

---

## Arena & Evaluation

### POST /api/arena/submit

Submit a task for model evaluation in the arena.

**Request:**
```json
{
  "input": "Write a Python function to calculate fibonacci numbers",
  "reference": "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
  "metadata": {
    "task_type": "code_generation",
    "difficulty": "medium",
    "language": "python"
  }
}
```

**Response:**
```json
{
  "task_id": "task_abc123",
  "status": "submitted",
  "estimated_completion": "2024-01-01T00:05:00Z",
  "models_to_evaluate": ["gpt-4o", "claude-3-sonnet", "deepseek-coder"]
}
```

### POST /api/arena/compare

Compare outputs from two models for a given task.

**Request:**
```json
{
  "task_id": "task_abc123",
  "model_a": "gpt-4o",
  "model_b": "claude-3-sonnet",
  "output_a": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
  "output_b": "def fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a",
  "winner": "model_b"
}
```

**Response:**
```json
{
  "comparison_id": "comp_xyz789",
  "recorded": true,
  "elo_changes": {
    "model_a": -12,
    "model_b": +12
  }
}
```

### GET /api/arena/leaderboard

Get the current model performance leaderboard.

**Response:**
```json
{
  "leaderboard": [
    {
      "model": "claude-3-sonnet",
      "elo_rating": 1547,
      "rank": 1,
      "total_comparisons": 2840,
      "win_rate": 0.68,
      "categories": {
        "code_generation": 1580,
        "text_analysis": 1520,
        "reasoning": 1540
      }
    },
    {
      "model": "gpt-4o",
      "elo_rating": 1523,
      "rank": 2,
      "total_comparisons": 3120,
      "win_rate": 0.64,
      "categories": {
        "code_generation": 1510,
        "text_analysis": 1540,
        "reasoning": 1520
      }
    }
  ],
  "last_updated": "2024-01-01T00:00:00Z"
}
```

---

## Swarm Intelligence

### POST /api/swarm/delegate

Delegate a task to the swarm for distributed processing.

**Request:**
```json
{
  "task_type": "analysis",
  "payload": {
    "text": "Large document to analyze...",
    "analysis_type": "sentiment_and_topics"
  },
  "priority": 2,
  "timeout_seconds": 300,
  "required_capabilities": ["nlp", "sentiment_analysis"]
}
```

**Response:**
```json
{
  "task_id": "swarm_task_456",
  "status": "queued",
  "estimated_completion": "2024-01-01T00:05:00Z",
  "assigned_nodes": [],
  "created_at": "2024-01-01T00:00:00Z"
}
```

### GET /api/swarm/task/{task_id}

Get status and results of a swarm task.

**Response:**
```json
{
  "task_id": "swarm_task_456",
  "status": "completed",
  "result": {
    "sentiment": "positive",
    "confidence": 0.85,
    "topics": ["technology", "innovation", "future"],
    "summary": "The document discusses positive technological innovations..."
  },
  "assigned_to": "node_worker_3",
  "processing_time": 45.2,
  "completed_at": "2024-01-01T00:00:45Z"
}
```

### GET /api/swarm/status

Get overall swarm health and statistics.

**Response:**
```json
{
  "total_nodes": 12,
  "active_nodes": 10,
  "pending_tasks": 23,
  "completed_tasks_today": 1547,
  "average_response_time": 32.5,
  "node_utilization": 0.75,
  "nodes": [
    {
      "node_id": "node_worker_1",
      "status": "active",
      "capabilities": ["nlp", "vision", "code_analysis"],
      "current_load": 0.8,
      "tasks_completed": 156
    }
  ]
}
```

---

## Configuration & Admin

### GET /api/config/governor

Get current governor (rate limiting) configuration.

**Response:**
```json
{
  "enabled": true,
  "force_deepseek_r1": false,
  "rate_limits": {
    "chat": 100,
    "vision": 50,
    "arena": 200
  },
  "cost_controls": {
    "daily_limit": 500.0,
    "per_request_limit": 10.0
  }
}
```

### POST /api/config/governor

Update governor configuration.

**Request:**
```json
{
  "enabled": true,
  "force_deepseek_r1": true,
  "rate_limits": {
    "chat": 150,
    "vision": 75
  }
}
```

### GET /api/adapters/state

Get current adapter states and configurations.

**Response:**
```json
{
  "adapters": [
    {
      "role": "code_reviewer",
      "status": "active",
      "model": "claude-3-sonnet",
      "performance_score": 0.92,
      "last_promoted": "2024-01-01T00:00:00Z"
    }
  ],
  "promotion_candidates": [
    {
      "role": "data_analyst",
      "candidate_model": "gpt-4o",
      "confidence_score": 0.88
    }
  ]
}
```

---

## Security & Secrets

### GET /api/secrets

List available secrets (names only, not values).

**Response:**
```json
{
  "secrets": [
    {
      "name": "openai_api_key",
      "last_updated": "2024-01-01T00:00:00Z",
      "expires_at": "2025-01-01T00:00:00Z"
    },
    {
      "name": "database_password",
      "last_updated": "2024-01-01T00:00:00Z",
      "expires_at": null
    }
  ]
}
```

### POST /api/secrets

Create or update a secret.

**Request:**
```json
{
  "name": "new_api_key",
  "value": "secret-value-here",
  "expires_at": "2025-01-01T00:00:00Z",
  "description": "API key for external service"
}
```

**Response:**
```json
{
  "name": "new_api_key",
  "created": true,
  "expires_at": "2025-01-01T00:00:00Z"
}
```

### DELETE /api/secrets/{secret_name}

Delete a secret.

**Response:**
```json
{
  "deleted": true,
  "name": "old_api_key"
}
```

---

## Error Responses

All endpoints may return these common error responses:

### 400 Bad Request
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
      "field": "q",
      "issue": "Query parameter is required"
    }
  }
}
```

### 401 Unauthorized
```json
{
  "error": {
    "code": "INVALID_API_KEY",
    "message": "API key is missing or invalid"
  }
}
```

### 429 Too Many Requests
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded",
    "details": {
      "limit": 100,
      "window": "1 minute",
      "retry_after": 45
    }
  }
}
```

### 503 Service Unavailable
```json
{
  "error": {
    "code": "PROVIDER_UNAVAILABLE",
    "message": "All oracle providers are currently unavailable",
    "details": {
      "available_providers": [],
      "estimated_recovery": "2024-01-01T00:05:00Z"
    }
  }
}
```

## Rate Limiting Headers

All responses include rate limiting headers:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
X-RateLimit-Window: 60
```

## Pagination

Endpoints that return lists support pagination:

```http
GET /api/arena/tasks?page=2&limit=50
```

Response includes pagination metadata:
```json
{
  "data": [...],
  "pagination": {
    "page": 2,
    "limit": 50,
    "total": 1000,
    "pages": 20,
    "has_next": true,
    "has_prev": true
  }
}
```