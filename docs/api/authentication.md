# Authentication Guide

This guide covers authentication methods, API key management, and security best practices for the Liquid-Hive-Upgrade API.

## Table of Contents

- [Authentication Methods](#authentication-methods)
- [API Key Management](#api-key-management)
- [Security Best Practices](#security-best-practices)
- [Rate Limiting](#rate-limiting)
- [Error Handling](#error-handling)
- [SDK Configuration](#sdk-configuration)

## Authentication Methods

### API Key Authentication

The primary authentication method is API key-based authentication using the `x-api-key` header.

**Header Format:**
```http
x-api-key: your-api-key-here
```

**Example Request:**
```bash
curl -X GET "https://api.liquid-hive.dev/api/healthz" \
  -H "x-api-key: lh_1234567890abcdef1234567890abcdef"
```

### API Key Format

API keys follow this format:
- **Prefix**: `lh_` (identifies Liquid-Hive keys)
- **Key Body**: 32 hexadecimal characters
- **Total Length**: 35 characters

**Example**: `lh_1234567890abcdef1234567890abcdef`

## API Key Management

### Creating API Keys

API keys can be created through:

1. **Web Dashboard** (Recommended)
2. **Admin API** (For programmatic access)
3. **CLI Tools** (For development)

#### Web Dashboard

1. Log in to the [Liquid-Hive Dashboard](https://dashboard.liquid-hive.dev)
2. Navigate to **API Keys** section
3. Click **Create New Key**
4. Set permissions and expiration
5. Copy the generated key (shown only once)

#### Admin API

```python
import httpx

async def create_api_key():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.liquid-hive.dev/api/admin/keys",
            headers={
                "x-api-key": "your-admin-key",
                "Content-Type": "application/json"
            },
            json={
                "name": "My Application Key",
                "permissions": ["chat", "vision", "arena"],
                "expires_at": "2025-12-31T23:59:59Z",
                "rate_limit": {
                    "requests_per_minute": 100
                }
            }
        )
        return response.json()

# Usage
key_info = await create_api_key()
print(f"New API Key: {key_info['api_key']}")
```

### Key Permissions

API keys support granular permissions:

| Permission | Description | Endpoints |
|------------|-------------|-----------|
| `chat` | Basic chat functionality | `/api/chat`, `/api/ws/chat` |
| `vision` | Image analysis | `/api/vision` |
| `arena` | Model evaluation | `/api/arena/*` |
| `swarm` | Swarm intelligence | `/api/swarm/*` |
| `admin` | Administrative access | `/api/admin/*`, `/api/config/*` |
| `secrets` | Secrets management | `/api/secrets/*` |

**Example Permission Configuration:**
```json
{
  "permissions": ["chat", "vision"],
  "restrictions": {
    "allowed_models": ["gpt-4o", "claude-3-sonnet"],
    "max_tokens_per_request": 2000,
    "allowed_ips": ["192.168.1.0/24"]
  }
}
```

### Key Rotation

Regular key rotation is recommended for security:

```python
async def rotate_api_key(old_key: str) -> str:
    """Rotate an API key while maintaining service availability."""

    # Step 1: Create new key
    new_key_response = await create_api_key_with_same_permissions(old_key)
    new_key = new_key_response['api_key']

    # Step 2: Update your applications to use new key
    # (This should be done gradually)

    # Step 3: Monitor usage to ensure old key is no longer used
    await monitor_key_usage(old_key, duration_minutes=60)

    # Step 4: Deactivate old key
    await deactivate_api_key(old_key)

    return new_key

async def create_api_key_with_same_permissions(reference_key: str) -> dict:
    """Create a new API key with the same permissions as an existing key."""
    # Get current key info
    key_info = await get_api_key_info(reference_key)

    # Create new key with same permissions
    return await create_api_key_with_config(key_info['config'])
```

### Key Monitoring

Monitor API key usage and security:

```python
async def monitor_api_key_usage(api_key: str) -> dict:
    """Get usage statistics for an API key."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.liquid-hive.dev/api/admin/keys/{api_key}/usage",
            headers={"x-api-key": "your-admin-key"}
        )
        return response.json()

# Example response
{
    "key_id": "lh_1234567890abcdef1234567890abcdef",
    "usage": {
        "requests_today": 1547,
        "requests_this_month": 45230,
        "total_requests": 123456
    },
    "last_used": "2024-01-01T12:34:56Z",
    "last_ip": "192.168.1.100",
    "rate_limit_status": {
        "limit": 100,
        "remaining": 87,
        "reset_at": "2024-01-01T12:35:00Z"
    }
}
```

## Security Best Practices

### Environment Variables

**Never hardcode API keys in your source code.** Use environment variables:

```bash
# .env file
LIQUID_HIVE_API_KEY=lh_1234567890abcdef1234567890abcdef
LIQUID_HIVE_BASE_URL=https://api.liquid-hive.dev
```

```python
import os
from liquid_hive import LiquidHiveClient

# Correct way
client = LiquidHiveClient(
    api_key=os.getenv('LIQUID_HIVE_API_KEY'),
    base_url=os.getenv('LIQUID_HIVE_BASE_URL')
)

# WRONG - Never do this
# client = LiquidHiveClient(api_key='lh_1234567890abcdef1234567890abcdef')
```

### Key Storage

#### Production Applications

Use secure secret management services:

**AWS Secrets Manager:**
```python
import boto3
import json

def get_api_key_from_aws():
    client = boto3.client('secretsmanager', region_name='us-west-2')
    response = client.get_secret_value(SecretId='liquid-hive/api-key')
    secret = json.loads(response['SecretString'])
    return secret['api_key']

api_key = get_api_key_from_aws()
```

**HashiCorp Vault:**
```python
import hvac

def get_api_key_from_vault():
    client = hvac.Client(url='https://vault.example.com')
    client.token = os.getenv('VAULT_TOKEN')

    response = client.secrets.kv.v2.read_secret_version(
        path='liquid-hive/api-key'
    )
    return response['data']['data']['api_key']
```

**Kubernetes Secrets:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: liquid-hive-secret
type: Opaque
data:
  api-key: bGhfMTIzNDU2Nzg5MGFiY2RlZjEyMzQ1Njc4OTBhYmNkZWY=  # base64 encoded
```

```python
# In your application
api_key = os.getenv('LIQUID_HIVE_API_KEY')  # Injected from secret
```

### Network Security

#### HTTPS Only

Always use HTTPS in production:

```python
# Correct
client = LiquidHiveClient(base_url='https://api.liquid-hive.dev')

# WRONG - Never use HTTP in production
# client = LiquidHiveClient(base_url='http://api.liquid-hive.dev')
```

#### IP Whitelisting

Restrict API key usage to specific IP addresses:

```python
async def create_restricted_api_key():
    return await create_api_key({
        "name": "Production Server Key",
        "permissions": ["chat", "vision"],
        "restrictions": {
            "allowed_ips": [
                "203.0.113.0/24",  # Your server subnet
                "198.51.100.50"     # Specific server IP
            ]
        }
    })
```

#### Request Signing (Advanced)

For highly sensitive applications, implement request signing:

```python
import hmac
import hashlib
import time
from urllib.parse import urlencode

def sign_request(method: str, path: str, body: str, secret: str) -> dict:
    """Generate request signature for additional security."""
    timestamp = str(int(time.time()))

    # Create string to sign
    string_to_sign = f"{method}\n{path}\n{body}\n{timestamp}"

    # Generate signature
    signature = hmac.new(
        secret.encode(),
        string_to_sign.encode(),
        hashlib.sha256
    ).hexdigest()

    return {
        "x-timestamp": timestamp,
        "x-signature": signature
    }

# Usage
headers = sign_request("POST", "/api/chat", '{"message": "Hello"}', "your-secret")
```

## Rate Limiting

### Understanding Rate Limits

Each API key has rate limits based on:
- **Requests per minute**
- **Requests per hour**
- **Daily request quota**
- **Monthly request quota**

### Rate Limit Headers

All API responses include rate limiting information:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
X-RateLimit-Window: 60
X-RateLimit-Retry-After: 45
```

### Handling Rate Limits

#### Exponential Backoff

```python
import asyncio
import random

async def api_call_with_backoff(client, message, max_retries=5):
    """Make API call with exponential backoff on rate limit."""

    for attempt in range(max_retries):
        try:
            return await client.chat(message)

        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise  # Final attempt failed

            # Calculate backoff time
            base_delay = 2 ** attempt  # Exponential: 1, 2, 4, 8, 16 seconds
            jitter = random.uniform(0, 1)  # Add randomness
            delay = base_delay + jitter

            print(f"Rate limited. Retrying in {delay:.1f} seconds...")
            await asyncio.sleep(delay)

    raise Exception("Max retries exceeded")
```

#### Rate Limit Monitoring

```python
class RateLimitMonitor:
    def __init__(self):
        self.limits = {}

    def update_from_headers(self, headers: dict):
        """Update rate limit info from response headers."""
        self.limits = {
            'limit': int(headers.get('X-RateLimit-Limit', 0)),
            'remaining': int(headers.get('X-RateLimit-Remaining', 0)),
            'reset': int(headers.get('X-RateLimit-Reset', 0)),
            'window': int(headers.get('X-RateLimit-Window', 60))
        }

    def should_throttle(self, threshold: float = 0.1) -> bool:
        """Check if we should throttle requests."""
        if not self.limits:
            return False

        utilization = 1 - (self.limits['remaining'] / self.limits['limit'])
        return utilization > (1 - threshold)  # Throttle if > 90% utilized

    def time_until_reset(self) -> int:
        """Seconds until rate limit resets."""
        if not self.limits:
            return 0

        return max(0, self.limits['reset'] - int(time.time()))

# Usage
monitor = RateLimitMonitor()

async def monitored_api_call(client, message):
    # Check if we should throttle
    if monitor.should_throttle():
        wait_time = monitor.time_until_reset()
        print(f"Throttling for {wait_time} seconds...")
        await asyncio.sleep(wait_time)

    # Make the call
    response = await client.chat(message)

    # Update monitoring info
    # (This would need to be extracted from the actual response headers)
    monitor.update_from_headers(response.get('headers', {}))

    return response
```

## Error Handling

### Authentication Errors

```python
from liquid_hive import LiquidHiveClient, AuthenticationError

async def handle_auth_errors():
    client = LiquidHiveClient(api_key="invalid-key")

    try:
        response = await client.chat("Hello")
    except AuthenticationError as e:
        print(f"Authentication failed: {e}")
        # Handle by:
        # 1. Check if API key is correct
        # 2. Verify key hasn't expired
        # 3. Check key permissions
        # 4. Rotate key if necessary
    except Exception as e:
        print(f"Unexpected error: {e}")
```

### Common Error Codes

| HTTP Status | Error Code | Description | Action |
|-------------|------------|-------------|---------|
| 401 | `INVALID_API_KEY` | API key is missing or invalid | Check key format and validity |
| 401 | `EXPIRED_API_KEY` | API key has expired | Rotate to new key |
| 403 | `INSUFFICIENT_PERMISSIONS` | Key lacks required permissions | Update key permissions |
| 403 | `IP_NOT_ALLOWED` | Request from unauthorized IP | Update IP whitelist |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many requests | Implement backoff |
| 429 | `QUOTA_EXCEEDED` | Monthly/daily quota exceeded | Upgrade plan or wait |

### Error Response Format

```json
{
  "error": {
    "code": "INVALID_API_KEY",
    "message": "The provided API key is invalid or malformed",
    "details": {
      "key_format": "API keys should start with 'lh_' followed by 32 hex characters",
      "documentation": "https://docs.liquid-hive.dev/api/authentication"
    }
  },
  "request_id": "req_1234567890",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## SDK Configuration

### Python SDK

```python
from liquid_hive import LiquidHiveClient
import os

# Basic configuration
client = LiquidHiveClient(
    api_key=os.getenv('LIQUID_HIVE_API_KEY'),
    base_url='https://api.liquid-hive.dev'
)

# Advanced configuration
client = LiquidHiveClient(
    api_key=os.getenv('LIQUID_HIVE_API_KEY'),
    base_url='https://api.liquid-hive.dev',
    timeout=30.0,
    max_retries=3,
    retry_delay=1.0,
    verify_ssl=True,
    user_agent='MyApp/1.0'
)
```

### JavaScript SDK

```javascript
import { LiquidHiveClient } from '@liquid-hive/client';

// Basic configuration
const client = new LiquidHiveClient({
  apiKey: process.env.LIQUID_HIVE_API_KEY,
  baseUrl: 'https://api.liquid-hive.dev'
});

// Advanced configuration
const client = new LiquidHiveClient({
  apiKey: process.env.LIQUID_HIVE_API_KEY,
  baseUrl: 'https://api.liquid-hive.dev',
  timeout: 30000,
  maxRetries: 3,
  retryDelay: 1000,
  headers: {
    'User-Agent': 'MyApp/1.0'
  }
});
```

### Environment-based Configuration

Create different configurations for different environments:

```python
import os
from enum import Enum

class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

def get_client_config(env: Environment) -> dict:
    configs = {
        Environment.DEVELOPMENT: {
            "base_url": "http://localhost:8000",
            "timeout": 60.0,
            "verify_ssl": False
        },
        Environment.STAGING: {
            "base_url": "https://staging-api.liquid-hive.dev",
            "timeout": 30.0,
            "verify_ssl": True
        },
        Environment.PRODUCTION: {
            "base_url": "https://api.liquid-hive.dev",
            "timeout": 10.0,
            "verify_ssl": True
        }
    }
    return configs[env]

# Usage
env = Environment(os.getenv('ENVIRONMENT', 'development'))
config = get_client_config(env)

client = LiquidHiveClient(
    api_key=os.getenv('LIQUID_HIVE_API_KEY'),
    **config
)
```

## Testing Authentication

### Unit Tests

```python
import pytest
from unittest.mock import patch, AsyncMock
from liquid_hive import LiquidHiveClient, AuthenticationError

@pytest.mark.asyncio
async def test_valid_api_key():
    """Test successful authentication with valid API key."""
    client = LiquidHiveClient(api_key="lh_validkey123456789012345678901234")

    with patch.object(client, '_make_request', new=AsyncMock()) as mock_request:
        mock_request.return_value = {"status": "healthy"}

        result = await client.health()
        assert result["status"] == "healthy"

        # Verify correct headers were sent
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]['headers']['x-api-key'] == "lh_validkey123456789012345678901234"

@pytest.mark.asyncio
async def test_invalid_api_key():
    """Test authentication failure with invalid API key."""
    client = LiquidHiveClient(api_key="invalid-key")

    with patch.object(client, '_make_request', new=AsyncMock()) as mock_request:
        mock_request.side_effect = AuthenticationError("Invalid API key")

        with pytest.raises(AuthenticationError):
            await client.health()

@pytest.mark.asyncio
async def test_missing_api_key():
    """Test behavior with missing API key."""
    with pytest.raises(ValueError, match="API key is required"):
        LiquidHiveClient(api_key=None)
```

### Integration Tests

```python
@pytest.mark.integration
async def test_real_authentication():
    """Test authentication against real API (requires valid key)."""
    api_key = os.getenv('TEST_API_KEY')
    if not api_key:
        pytest.skip("TEST_API_KEY not set")

    client = LiquidHiveClient(api_key=api_key)

    # This should succeed with valid key
    health = await client.health()
    assert health['status'] == 'healthy'

    # Test with invalid key should fail
    invalid_client = LiquidHiveClient(api_key="lh_invalid123456789012345678901234")

    with pytest.raises(AuthenticationError):
        await invalid_client.health()
```

This authentication guide provides comprehensive coverage of security best practices, key management, and practical implementation examples for secure API integration.
