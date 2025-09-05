# SDK Documentation

This guide covers the official SDKs for the Liquid-Hive-Upgrade API, providing easy-to-use client libraries for different programming languages.

## Available SDKs

- [Python SDK](#python-sdk)
- [JavaScript/Node.js SDK](#javascriptnodejs-sdk)

---

## Python SDK

### Installation

```bash
pip install liquid-hive-client
```

Or install from source:
```bash
git clone https://github.com/liquid-hive/upgrade.git
cd upgrade/sdks/python
pip install -e .
```

### Quick Start

```python
import asyncio
from liquid_hive import LiquidHiveClient

async def main():
    # Initialize client
    client = LiquidHiveClient(
        base_url="https://api.liquid-hive.dev",
        api_key="your-api-key-here"
    )
    
    # Check system health
    health = await client.health()
    print(f"System status: {health}")
    
    # Send a chat message
    response = await client.chat("What is machine learning?")
    print(f"AI Response: {response}")

# Run the async function
asyncio.run(main())
```

### Class Reference

#### LiquidHiveClient

The main client class for interacting with the Liquid-Hive API.

**Constructor:**
```python
LiquidHiveClient(base_url: str | None = None, api_key: str | None = None)
```

**Parameters:**
- `base_url` (str, optional): API base URL. Defaults to `BASE_URL` environment variable or `http://localhost:8000`
- `api_key` (str, optional): API key for authentication. Defaults to `API_KEY` environment variable

**Methods:**

##### `async health() -> dict`

Check system health and availability.

**Returns:**
```python
{
    "status": "healthy",
    "timestamp": "2024-01-01T00:00:00Z",
    "version": "1.0.0",
    "uptime": 86400
}
```

**Example:**
```python
health_status = await client.health()
if health_status["status"] == "healthy":
    print("System is operational")
```

##### `async chat(q: str) -> dict`

Send a chat message to the AI system.

**Parameters:**
- `q` (str): The user's message or question

**Returns:**
```python
{
    "message": "AI response here...",
    "model_used": "gpt-4o",
    "provider": "openai",
    "tokens_used": {"input": 12, "output": 28, "total": 40},
    "cost": 0.0024
}
```

**Example:**
```python
response = await client.chat("Explain quantum computing")
print(f"AI says: {response['message']}")
print(f"Cost: ${response['cost']:.4f}")
```

##### `async arena_submit(task_input: str, reference: str | None = None, metadata: dict | None = None) -> dict`

Submit a task for evaluation in the model arena.

**Parameters:**
- `task_input` (str): The input task or prompt
- `reference` (str, optional): Reference output for comparison
- `metadata` (dict, optional): Additional task metadata

**Returns:**
```python
{
    "task_id": "task_abc123",
    "status": "submitted",
    "estimated_completion": "2024-01-01T00:05:00Z"
}
```

**Example:**
```python
task = await client.arena_submit(
    task_input="Write a Python function to sort a list",
    reference="def sort_list(lst): return sorted(lst)",
    metadata={"language": "python", "difficulty": "easy"}
)
print(f"Task submitted: {task['task_id']}")
```

##### `async arena_compare(task_id: str, model_a: str, model_b: str, output_a: str, output_b: str, winner: str | None = None) -> dict`

Compare outputs from two models for a specific task.

**Parameters:**
- `task_id` (str): ID of the task being compared
- `model_a` (str): Name of the first model
- `model_b` (str): Name of the second model
- `output_a` (str): Output from the first model
- `output_b` (str): Output from the second model
- `winner` (str, optional): Which model won ("model_a" or "model_b")

**Example:**
```python
comparison = await client.arena_compare(
    task_id="task_abc123",
    model_a="gpt-4o",
    model_b="claude-3-sonnet",
    output_a="def sort_list(lst): return sorted(lst)",
    output_b="def sort_list(lst): return list(sorted(lst))",
    winner="model_a"
)
```

##### `async arena_leaderboard() -> dict`

Get the current model performance leaderboard.

**Returns:**
```python
{
    "leaderboard": [
        {
            "model": "claude-3-sonnet",
            "elo_rating": 1547,
            "rank": 1,
            "win_rate": 0.68
        }
    ]
}
```

### Error Handling

The Python SDK raises specific exceptions for different error conditions:

```python
from liquid_hive import LiquidHiveClient, LiquidHiveError, RateLimitError, AuthenticationError

async def robust_chat():
    client = LiquidHiveClient()
    
    try:
        response = await client.chat("Hello!")
        return response
    except AuthenticationError:
        print("Invalid API key")
    except RateLimitError as e:
        print(f"Rate limited. Retry after {e.retry_after} seconds")
    except LiquidHiveError as e:
        print(f"API error: {e.message}")
    except Exception as e:
        print(f"Unexpected error: {e}")
```

### Environment Variables

The SDK supports these environment variables:

```bash
# API Configuration
BASE_URL=https://api.liquid-hive.dev
API_KEY=your-api-key-here

# Optional: Timeout settings
LIQUID_HIVE_TIMEOUT=30
LIQUID_HIVE_RETRY_ATTEMPTS=3
```

---

## JavaScript/Node.js SDK

### Installation

```bash
npm install @liquid-hive/client
```

Or with Yarn:
```bash
yarn add @liquid-hive/client
```

### Quick Start

```javascript
import { LiquidHiveClient } from '@liquid-hive/client';

const client = new LiquidHiveClient({
  baseUrl: 'https://api.liquid-hive.dev',
  apiKey: 'your-api-key-here'
});

async function main() {
  try {
    // Check system health
    const health = await client.health();
    console.log('System status:', health);
    
    // Send a chat message
    const response = await client.chat('What is machine learning?');
    console.log('AI Response:', response.message);
    
  } catch (error) {
    console.error('Error:', error.message);
  }
}

main();
```

### Class Reference

#### LiquidHiveClient

The main client class for JavaScript/Node.js applications.

**Constructor:**
```javascript
new LiquidHiveClient(options)
```

**Options:**
```javascript
{
  baseUrl: 'https://api.liquid-hive.dev',  // API base URL
  apiKey: 'your-api-key',                   // API key for authentication
  timeout: 30000,                           // Request timeout in milliseconds
  retries: 3                                // Number of retry attempts
}
```

**Methods:**

##### `async health()`

Check system health and availability.

```javascript
const health = await client.health();
console.log(health);
// Output: { status: 'healthy', timestamp: '2024-01-01T00:00:00Z', ... }
```

##### `async chat(message)`

Send a chat message to the AI system.

```javascript
const response = await client.chat('Explain quantum computing');
console.log(response.message);
console.log(`Cost: $${response.cost}`);
```

##### `async arenaSubmit(input, reference, metadata)`

Submit a task for model evaluation.

```javascript
const task = await client.arenaSubmit(
  'Write a JavaScript function to reverse a string',
  'function reverse(str) { return str.split("").reverse().join(""); }',
  { language: 'javascript', difficulty: 'easy' }
);
console.log(`Task ID: ${task.task_id}`);
```

##### `async arenaCompare(taskId, modelA, modelB, outputA, outputB, winner)`

Compare model outputs.

```javascript
const comparison = await client.arenaCompare(
  'task_abc123',
  'gpt-4o',
  'claude-3-sonnet',
  'function reverse(str) { return str.split("").reverse().join(""); }',
  'const reverse = str => [...str].reverse().join("");',
  'model_b'
);
```

##### `async arenaLeaderboard()`

Get the model leaderboard.

```javascript
const leaderboard = await client.arenaLeaderboard();
console.log('Top model:', leaderboard.leaderboard[0]);
```

### Error Handling

The JavaScript SDK provides structured error handling:

```javascript
import { LiquidHiveClient, LiquidHiveError, RateLimitError, AuthenticationError } from '@liquid-hive/client';

const client = new LiquidHiveClient({ apiKey: 'your-key' });

try {
  const response = await client.chat('Hello!');
  console.log(response.message);
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.error('Authentication failed:', error.message);
  } else if (error instanceof RateLimitError) {
    console.error(`Rate limited. Retry after ${error.retryAfter} seconds`);
  } else if (error instanceof LiquidHiveError) {
    console.error('API error:', error.message, error.code);
  } else {
    console.error('Unexpected error:', error);
  }
}
```

### Browser Usage

The SDK works in browser environments:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Liquid-Hive Demo</title>
</head>
<body>
    <script type="module">
        import { LiquidHiveClient } from 'https://unpkg.com/@liquid-hive/client@latest/dist/index.esm.js';
        
        const client = new LiquidHiveClient({
          baseUrl: 'https://api.liquid-hive.dev',
          apiKey: 'your-api-key'
        });
        
        document.getElementById('chat-btn').onclick = async () => {
          const input = document.getElementById('message').value;
          const response = await client.chat(input);
          document.getElementById('response').textContent = response.message;
        };
    </script>
    
    <input id="message" placeholder="Type your message...">
    <button id="chat-btn">Send</button>
    <div id="response"></div>
</body>
</html>
```

### TypeScript Support

The JavaScript SDK includes TypeScript definitions:

```typescript
import { LiquidHiveClient, ChatResponse, ArenaSubmitResponse } from '@liquid-hive/client';

const client = new LiquidHiveClient({
  baseUrl: 'https://api.liquid-hive.dev',
  apiKey: process.env.API_KEY!
});

async function typedChat(message: string): Promise<ChatResponse> {
  return await client.chat(message);
}

async function typedArenaSubmit(input: string): Promise<ArenaSubmitResponse> {
  return await client.arenaSubmit(input);
}
```

### Environment Variables

The SDK supports environment variables:

```bash
# API Configuration
BASE_URL=https://api.liquid-hive.dev
API_KEY=your-api-key-here

# Optional settings
LIQUID_HIVE_TIMEOUT=30000
LIQUID_HIVE_RETRIES=3
```

---

## Advanced Usage

### Custom HTTP Clients

Both SDKs allow custom HTTP client configuration:

#### Python
```python
import httpx
from liquid_hive import LiquidHiveClient

# Custom HTTP client with proxy
custom_client = httpx.AsyncClient(
    proxies="http://proxy.example.com:8080",
    timeout=60.0
)

client = LiquidHiveClient(
    base_url="https://api.liquid-hive.dev",
    api_key="your-key",
    http_client=custom_client
)
```

#### JavaScript
```javascript
import { LiquidHiveClient } from '@liquid-hive/client';

const client = new LiquidHiveClient({
  baseUrl: 'https://api.liquid-hive.dev',
  apiKey: 'your-key',
  fetch: customFetchImplementation,  // Custom fetch function
  timeout: 60000,
  headers: {
    'User-Agent': 'MyApp/1.0'
  }
});
```

### Streaming Responses

For real-time streaming (WebSocket support coming soon):

```javascript
// WebSocket streaming (planned feature)
const stream = client.streamChat('Tell me about AI');
stream.on('token', (token) => {
  console.log('New token:', token);
});
stream.on('complete', (response) => {
  console.log('Complete response:', response);
});
```

### Batch Operations

Process multiple requests efficiently:

```python
import asyncio

async def batch_chat():
    client = LiquidHiveClient()
    
    questions = [
        "What is AI?",
        "Explain machine learning",
        "What is deep learning?"
    ]
    
    # Process in parallel
    tasks = [client.chat(q) for q in questions]
    responses = await asyncio.gather(*tasks)
    
    for q, r in zip(questions, responses):
        print(f"Q: {q}")
        print(f"A: {r['message']}\n")
```

## Migration Guide

### From v1.0 to v2.0

Key changes in v2.0:
- Async/await required for all operations
- New authentication method
- Updated response formats

```python
# v1.0 (deprecated)
client = LiquidHiveClient()
response = client.chat_sync("Hello")

# v2.0 (current)
client = LiquidHiveClient()
response = await client.chat("Hello")
```

## Support and Resources

- **GitHub Repository**: [https://github.com/liquid-hive/upgrade](https://github.com/liquid-hive/upgrade)
- **SDK Issues**: [Report SDK-specific issues](https://github.com/liquid-hive/upgrade/issues)
- **API Documentation**: [Complete API reference](endpoints.md)
- **Examples**: [Integration examples](../user-guide/integration-examples.md)
- **Community**: [Discord server](https://discord.gg/liquid-hive)