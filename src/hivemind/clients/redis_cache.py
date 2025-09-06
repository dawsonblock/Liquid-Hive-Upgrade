"""Redis hot cache for query results and rate limiting."""

import os
import time
import json
from typing import Any, Optional, Dict, List
import structlog
from src.logging_config import get_logger

try:
    import redis
except ImportError:
    redis = None

logger = structlog.get_logger(__name__)

def _now() -> int:
    """Get current timestamp."""
    return int(time.time())

# Configuration from environment
HOST = os.getenv("REDIS_HOST", "redis")
PORT = int(os.getenv("REDIS_PORT", "6379"))
DB = int(os.getenv("REDIS_DB", "0"))
PASSWORD = os.getenv("REDIS_PASSWORD")

# Connection pool
_redis_client: Optional[Any] = None

def _get_redis() -> Any:
    """Get Redis client with connection pooling."""
    global _redis_client
    
    if redis is None:
        logger.warning("Redis not available - using no-op cache")
        return None
    
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=HOST,
                port=PORT,
                db=DB,
                password=PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            _redis_client.ping()
            
            logger.info("Redis connection established",
                       host=HOST,
                       port=PORT,
                       db=DB)
            
        except Exception as e:
            logger.error("Redis connection failed", error=str(e))
            _redis_client = None
    
    return _redis_client

def kv_set(key: str, value: Any, ttl_sec: int = 900) -> bool:
    """Set a key-value pair with TTL."""
    try:
        r = _get_redis()
        if r is None:
            return False
        
        serialized_value = json.dumps(value, default=str)
        result = r.set(key, serialized_value, ex=ttl_sec)
        
        logger.debug("Cache set", key=key, ttl=ttl_sec)
        return bool(result)
        
    except Exception as e:
        logger.error("Cache set failed", key=key, error=str(e))
        return False

def kv_get(key: str) -> Any:
    """Get value by key."""
    try:
        r = _get_redis()
        if r is None:
            return None
        
        value = r.get(key)
        if value is None:
            return None
        
        result = json.loads(value)
        logger.debug("Cache hit", key=key)
        return result
        
    except Exception as e:
        logger.error("Cache get failed", key=key, error=str(e))
        return None

def kv_delete(key: str) -> bool:
    """Delete a key."""
    try:
        r = _get_redis()
        if r is None:
            return False
        
        result = r.delete(key)
        logger.debug("Cache delete", key=key)
        return bool(result)
        
    except Exception as e:
        logger.error("Cache delete failed", key=key, error=str(e))
        return False

def kv_exists(key: str) -> bool:
    """Check if key exists."""
    try:
        r = _get_redis()
        if r is None:
            return False
        
        return bool(r.exists(key))
        
    except Exception as e:
        logger.error("Cache exists check failed", key=key, error=str(e))
        return False

def incr(key: str, ttl_sec: int = 3600) -> int:
    """Increment counter with TTL."""
    try:
        r = _get_redis()
        if r is None:
            return 0
        
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl_sec)
        results = pipe.execute()
        
        counter_value = results[0] if results else 0
        logger.debug("Counter incremented", key=key, value=counter_value)
        return int(counter_value)
        
    except Exception as e:
        logger.error("Counter increment failed", key=key, error=str(e))
        return 0

def rate_limit(key: str, limit: int, window_sec: int) -> bool:
    """Check rate limit using sliding window counter."""
    try:
        now = int(time.time())
        bucket = f"rl:{key}:{now // window_sec}"
        
        current_count = incr(bucket, window_sec)
        
        is_allowed = current_count <= limit
        
        if not is_allowed:
            logger.warning("Rate limit exceeded",
                          key=key,
                          count=current_count,
                          limit=limit,
                          window=window_sec)
        
        return is_allowed
        
    except Exception as e:
        logger.error("Rate limit check failed", key=key, error=str(e))
        return True  # Fail open for availability

def cache_query_result(query_hash: str, results: List[Dict[str, Any]], ttl_sec: int = 1800):
    """Cache query results for faster retrieval."""
    try:
        cache_key = f"query_cache:{query_hash}"
        
        cached_data = {
            "results": results,
            "cached_at": _now(),
            "result_count": len(results)
        }
        
        return kv_set(cache_key, cached_data, ttl_sec)
        
    except Exception as e:
        logger.error("Failed to cache query result", error=str(e))
        return False

def get_cached_query(query_hash: str) -> Optional[List[Dict[str, Any]]]:
    """Retrieve cached query results."""
    try:
        cache_key = f"query_cache:{query_hash}"
        
        cached_data = kv_get(cache_key)
        if cached_data is None:
            return None
        
        # Check if cache is still fresh (additional validation)
        cached_at = cached_data.get("cached_at", 0)
        age_minutes = (time.time() - cached_at) / 60
        
        if age_minutes > 30:  # 30 minute max age
            kv_delete(cache_key)
            return None
        
        logger.debug("Query cache hit", 
                    query_hash=query_hash[:8],
                    result_count=cached_data.get("result_count", 0),
                    age_minutes=age_minutes)
        
        return cached_data.get("results", [])
        
    except Exception as e:
        logger.error("Failed to get cached query", error=str(e))
        return None

def clear_cache_pattern(pattern: str) -> int:
    """Clear cache keys matching pattern."""
    try:
        r = _get_redis()
        if r is None:
            return 0
        
        keys = r.keys(pattern)
        if keys:
            deleted_count = r.delete(*keys)
            logger.info("Cache cleared", pattern=pattern, deleted=deleted_count)
            return int(deleted_count)
        
        return 0
        
    except Exception as e:
        logger.error("Failed to clear cache pattern", pattern=pattern, error=str(e))
        return 0

def get_cache_stats() -> Dict[str, Any]:
    """Get Redis cache statistics."""
    try:
        r = _get_redis()
        if r is None:
            return {"status": "unavailable"}
        
        info = r.info()
        
        return {
            "status": "connected",
            "used_memory": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
            "total_commands_processed": info.get("total_commands_processed"),
            "keyspace_hits": info.get("keyspace_hits"),
            "keyspace_misses": info.get("keyspace_misses"),
            "hit_rate": (
                info.get("keyspace_hits", 0) / 
                max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
            ),
            "uptime_seconds": info.get("uptime_in_seconds"),
            "redis_version": info.get("redis_version")
        }
        
    except Exception as e:
        logger.error("Failed to get cache stats", error=str(e))
        return {"status": "error", "error": str(e)}

def health_check() -> Dict[str, Any]:
    """Check Redis connection health."""
    try:
        r = _get_redis()
        if r is None:
            return {"status": "unavailable", "error": "Redis not installed"}
        
        # Test basic operations
        test_key = "health_check_test"
        r.set(test_key, "test", ex=10)
        value = r.get(test_key)
        r.delete(test_key)
        
        if value == "test":
            return {"status": "healthy"}
        else:
            return {"status": "unhealthy", "error": "Read/write test failed"}
        
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return {"status": "unhealthy", "error": str(e)}