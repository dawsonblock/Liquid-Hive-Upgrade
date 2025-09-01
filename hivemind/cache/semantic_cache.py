"""
Semantic Cache for LIQUID-HIVE
=============================

An intelligent semantic caching system that uses embedding similarity
to cache and retrieve responses for semantically similar queries.

Features:
- Semantic similarity matching using embeddings
- Redis-based storage with TTL support
- Query preprocessing and normalization
- Cache hit/miss analytics
- Configurable similarity thresholds
- Cache warming and management
"""

import json
import hashlib
import time
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import redis.asyncio as redis
    import numpy as np
    from sentence_transformers import SentenceTransformer
    DEPS_AVAILABLE = True
except ImportError as e:
    redis = None
    np = None
    SentenceTransformer = None
    DEPS_AVAILABLE = False
    logging.getLogger(__name__).warning(f"Semantic cache dependencies not available: {e}")

log = logging.getLogger(__name__)

class CacheStrategy(Enum):
    """Cache strategy for different types of queries."""
    AGGRESSIVE = "aggressive"  # Cache almost everything
    CONSERVATIVE = "conservative"  # Only cache high-confidence matches
    SELECTIVE = "selective"  # Cache based on query patterns
    DISABLED = "disabled"  # Disable caching

@dataclass
class CacheEntry:
    """Represents a cached response entry."""
    query: str
    query_hash: str
    embedding: List[float]
    response: Dict[str, Any]
    created_at: float
    accessed_count: int = 0
    last_accessed: float = 0.0
    ttl_seconds: int = 3600
    similarity_threshold: float = 0.95
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheEntry':
        return cls(**data)
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.created_at > self.ttl_seconds
    
    def update_access(self):
        """Update access statistics."""
        self.accessed_count += 1
        self.last_accessed = time.time()

class SemanticCache:
    """
    Semantic cache using Redis and embeddings for intelligent query matching.
    
    This cache goes beyond exact string matching to understand semantic similarity
    between queries, enabling cache hits for paraphrased or similar questions.
    """
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379",
                 embedding_model: str = "all-MiniLM-L6-v2",
                 similarity_threshold: float = 0.95,
                 default_ttl: int = 3600,
                 strategy: CacheStrategy = CacheStrategy.CONSERVATIVE):
        
        self.redis_url = redis_url
        self.embedding_model_name = embedding_model
        self.similarity_threshold = similarity_threshold
        self.default_ttl = default_ttl
        self.strategy = strategy
        
        # Initialize components
        self.redis_client: Optional[redis.Redis] = None
        self.embedding_model: Optional[SentenceTransformer] = None
        self.is_ready = False
        
        # Cache configuration
        self.cache_key_prefix = "semantic_cache"
        self.vector_key_prefix = f"{self.cache_key_prefix}:vectors"
        self.metadata_key_prefix = f"{self.cache_key_prefix}:metadata"
        self.analytics_key = f"{self.cache_key_prefix}:analytics"
        
        # Performance settings
        self.max_cache_size = 10000  # Maximum number of cached entries
        self.batch_size = 50  # Batch size for similarity comparisons
        self.cleanup_interval = 3600  # Cleanup expired entries every hour
        
        # Analytics
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "total_queries": 0,
            "average_similarity": 0.0,
            "last_cleanup": time.time()
        }
        
        if DEPS_AVAILABLE:
            asyncio.create_task(self._initialize())
    
    async def _initialize(self):
        """Initialize Redis client and embedding model."""
        try:
            # Initialize Redis client
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            log.info(f"✅ Connected to Redis at {self.redis_url}")
            
            # Initialize embedding model
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            log.info(f"✅ Loaded embedding model: {self.embedding_model_name}")
            
            # Load existing analytics
            await self._load_analytics()
            
            self.is_ready = True
            log.info("🧠 Semantic cache initialized successfully")
            
            # Start background cleanup task
            asyncio.create_task(self._periodic_cleanup())
            
        except Exception as e:
            log.error(f"Failed to initialize semantic cache: {e}")
            self.is_ready = False
    
    async def get(self, query: str, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Get cached response for a semantically similar query.
        
        Args:
            query: The query to search for
            context: Optional context for more precise matching
            
        Returns:
            Cached response if found, None otherwise
        """
        if not self.is_ready or self.strategy == CacheStrategy.DISABLED:
            return None
        
        self.stats["total_queries"] += 1
        
        try:
            # Normalize and preprocess query
            normalized_query = self._normalize_query(query)
            if not normalized_query:
                return None
            
            # Generate embedding
            query_embedding = self._get_embedding(normalized_query)
            if query_embedding is None:
                return None
            
            # Search for similar cached queries
            similar_entry = await self._find_similar_entry(query_embedding, normalized_query, context)
            
            if similar_entry:
                # Update access statistics
                similar_entry.update_access()
                await self._update_cache_entry(similar_entry)
                
                self.stats["cache_hits"] += 1
                
                # Add cache metadata to response
                response = similar_entry.response.copy()
                response["cache_hit"] = True
                response["cache_similarity"] = getattr(similar_entry, 'last_similarity', 1.0)
                response["cache_original_query"] = similar_entry.query
                response["cache_accessed_count"] = similar_entry.accessed_count
                
                log.debug(f"Cache hit for query '{query[:50]}...', similarity: {getattr(similar_entry, 'last_similarity', 1.0):.3f}")
                
                return response
            else:
                self.stats["cache_misses"] += 1
                log.debug(f"Cache miss for query '{query[:50]}...'")
                return None
                
        except Exception as e:
            log.error(f"Cache get failed for query '{query[:50]}...': {e}")
            return None
    
    async def set(self, query: str, response: Dict[str, Any], 
                 context: Optional[Dict[str, Any]] = None,
                 ttl: Optional[int] = None) -> bool:
        """
        Cache a response for a query.
        
        Args:
            query: The original query
            response: The response to cache
            context: Optional context for the query
            ttl: Time-to-live in seconds (uses default if not specified)
            
        Returns:
            True if cached successfully, False otherwise
        """
        if not self.is_ready or self.strategy == CacheStrategy.DISABLED:
            return False
        
        try:
            # Check if we should cache this query based on strategy
            if not self._should_cache_query(query, response, context):
                return False
            
            # Normalize query
            normalized_query = self._normalize_query(query)
            if not normalized_query:
                return False
            
            # Generate embedding
            query_embedding = self._get_embedding(normalized_query)
            if query_embedding is None:
                return False
            
            # Create cache entry
            query_hash = self._hash_query(normalized_query)
            ttl = ttl or self._get_adaptive_ttl(response)
            
            cache_entry = CacheEntry(
                query=normalized_query,
                query_hash=query_hash,
                embedding=query_embedding.tolist(),
                response=self._sanitize_response(response),
                created_at=time.time(),
                ttl_seconds=ttl,
                similarity_threshold=self._get_similarity_threshold(query, context)
            )
            
            # Store in Redis
            success = await self._store_cache_entry(cache_entry)
            
            if success:
                log.debug(f"Cached response for query '{query[:50]}...', TTL: {ttl}s")
            
            return success
            
        except Exception as e:
            log.error(f"Cache set failed for query '{query[:50]}...': {e}")
            return False
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for consistent caching."""
        if not query or not query.strip():
            return ""
        
        # Basic normalization
        normalized = query.strip().lower()
        
        # Remove extra whitespace
        normalized = " ".join(normalized.split())
        
        # Remove common stop words for better semantic matching
        # (In production, you might want more sophisticated preprocessing)
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        words = normalized.split()
        
        # Only remove stop words if query is long enough
        if len(words) > 3:
            words = [word for word in words if word not in stop_words]
            normalized = " ".join(words)
        
        return normalized
    
    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding for text."""
        if not self.embedding_model:
            return None
        
        try:
            return self.embedding_model.encode(text)
        except Exception as e:
            log.warning(f"Failed to generate embedding: {e}")
            return None
    
    async def _find_similar_entry(self, query_embedding: np.ndarray, 
                                 query: str, context: Optional[Dict[str, Any]]) -> Optional[CacheEntry]:
        """Find the most similar cached entry."""
        try:
            # Get all cached entries (in production, you'd want more efficient similarity search)
            cached_entries = await self._get_cached_entries_sample()
            
            if not cached_entries:
                return None
            
            best_entry = None
            best_similarity = 0.0
            
            for entry in cached_entries:
                if entry.is_expired():
                    continue
                
                # Calculate similarity
                similarity = self._calculate_similarity(query_embedding, np.array(entry.embedding))
                
                # Check if similarity meets threshold
                if similarity >= entry.similarity_threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_entry = entry
            
            # Store similarity for debugging
            if best_entry:
                best_entry.last_similarity = best_similarity
                
                # Update average similarity stat
                self.stats["average_similarity"] = (
                    (self.stats["average_similarity"] * self.stats["cache_hits"] + best_similarity) / 
                    (self.stats["cache_hits"] + 1)
                )
            
            return best_entry
            
        except Exception as e:
            log.error(f"Failed to find similar entry: {e}")
            return None
    
    def _calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between embeddings."""
        try:
            # Cosine similarity
            dot_product = np.dot(embedding1, embedding2)
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot_product / (norm1 * norm2)
            
        except Exception:
            return 0.0
    
    async def _get_cached_entries_sample(self, limit: int = 1000) -> List[CacheEntry]:
        """Get a sample of cached entries for similarity comparison."""
        try:
            # Get all cache keys
            pattern = f"{self.metadata_key_prefix}:*"
            keys = await self.redis_client.keys(pattern)
            
            # Limit to prevent memory issues
            if len(keys) > limit:
                keys = keys[:limit]
            
            entries = []
            for key in keys:
                try:
                    entry_data = await self.redis_client.get(key)
                    if entry_data:
                        entry_dict = json.loads(entry_data)
                        entry = CacheEntry.from_dict(entry_dict)
                        entries.append(entry)
                except Exception:
                    continue
            
            return entries
            
        except Exception as e:
            log.error(f"Failed to get cached entries sample: {e}")
            return []
    
    async def _store_cache_entry(self, entry: CacheEntry) -> bool:
        """Store cache entry in Redis."""
        try:
            # Store metadata
            metadata_key = f"{self.metadata_key_prefix}:{entry.query_hash}"
            await self.redis_client.setex(
                metadata_key, 
                entry.ttl_seconds,
                json.dumps(entry.to_dict())
            )
            
            # Store vector separately for efficient similarity search
            # (In production, you'd use a vector database or Redis modules like RediSearch)
            vector_key = f"{self.vector_key_prefix}:{entry.query_hash}"
            await self.redis_client.setex(
                vector_key,
                entry.ttl_seconds,
                json.dumps(entry.embedding)
            )
            
            # Manage cache size
            await self._manage_cache_size()
            
            return True
            
        except Exception as e:
            log.error(f"Failed to store cache entry: {e}")
            return False
    
    async def _update_cache_entry(self, entry: CacheEntry):
        """Update an existing cache entry with new access statistics."""
        try:
            metadata_key = f"{self.metadata_key_prefix}:{entry.query_hash}"
            await self.redis_client.setex(
                metadata_key,
                entry.ttl_seconds,
                json.dumps(entry.to_dict())
            )
        except Exception as e:
            log.warning(f"Failed to update cache entry: {e}")
    
    def _should_cache_query(self, query: str, response: Dict[str, Any], 
                           context: Optional[Dict[str, Any]]) -> bool:
        """Determine if a query should be cached based on strategy and content."""
        
        if self.strategy == CacheStrategy.DISABLED:
            return False
        
        # Don't cache very short queries
        if len(query.strip()) < 10:
            return False
        
        # Don't cache if response indicates an error
        if response.get("error") or not response.get("answer"):
            return False
        
        # Don't cache very short responses (likely not useful)
        answer = response.get("answer", "")
        if len(answer) < 20:
            return False
        
        if self.strategy == CacheStrategy.AGGRESSIVE:
            return True
        
        elif self.strategy == CacheStrategy.CONSERVATIVE:
            # Only cache if response seems high-quality
            return (
                len(answer) > 50 and
                len(query.strip()) > 20 and
                not any(uncertainty in answer.lower() 
                       for uncertainty in ["i don't know", "unclear", "uncertain"])
            )
        
        elif self.strategy == CacheStrategy.SELECTIVE:
            # Cache based on query patterns
            query_lower = query.lower()
            cache_patterns = [
                "what is", "how to", "explain", "define", "describe",
                "difference between", "pros and cons", "advantages",
                "best practices", "tutorial", "guide"
            ]
            
            return any(pattern in query_lower for pattern in cache_patterns)
        
        return False
    
    def _get_adaptive_ttl(self, response: Dict[str, Any]) -> int:
        """Get adaptive TTL based on response characteristics."""
        base_ttl = self.default_ttl
        
        # Longer TTL for longer, more comprehensive responses
        answer = response.get("answer", "")
        if len(answer) > 500:
            base_ttl *= 2
        elif len(answer) > 1000:
            base_ttl *= 3
        
        # Shorter TTL for responses that might become outdated quickly
        time_sensitive_keywords = ["latest", "recent", "current", "today", "now", "2024", "2025"]
        if any(keyword in answer.lower() for keyword in time_sensitive_keywords):
            base_ttl = min(base_ttl, 1800)  # 30 minutes max
        
        return base_ttl
    
    def _get_similarity_threshold(self, query: str, context: Optional[Dict[str, Any]]) -> float:
        """Get adaptive similarity threshold based on query and context."""
        base_threshold = self.similarity_threshold
        
        # Lower threshold for longer queries (more context)
        if len(query) > 100:
            base_threshold -= 0.05
        
        # Higher threshold for short queries (less context, need closer match)
        elif len(query) < 30:
            base_threshold += 0.02
        
        return max(0.85, min(0.98, base_threshold))
    
    def _sanitize_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize response before caching to remove sensitive data."""
        # Create a copy and remove potentially sensitive fields
        sanitized = response.copy()
        
        # Remove fields that shouldn't be cached
        sensitive_fields = [
            "request_id", "user_id", "session_id", "timestamp", 
            "execution_time", "provider_metadata", "internal_metadata"
        ]
        
        for field in sensitive_fields:
            sanitized.pop(field, None)
        
        # Add cache metadata
        sanitized["cached_at"] = datetime.utcnow().isoformat()
        
        return sanitized
    
    def _hash_query(self, query: str) -> str:
        """Generate hash for query."""
        return hashlib.sha256(query.encode()).hexdigest()[:16]
    
    async def _manage_cache_size(self):
        """Manage cache size by removing least recently used entries."""
        try:
            # Count current entries
            pattern = f"{self.metadata_key_prefix}:*"
            keys = await self.redis_client.keys(pattern)
            
            if len(keys) <= self.max_cache_size:
                return
            
            # Get all entries with access info
            entries_with_access = []
            for key in keys:
                try:
                    entry_data = await self.redis_client.get(key)
                    if entry_data:
                        entry_dict = json.loads(entry_data)
                        entries_with_access.append((key, entry_dict))
                except Exception:
                    continue
            
            # Sort by last accessed time (oldest first)
            entries_with_access.sort(key=lambda x: x[1].get("last_accessed", 0))
            
            # Remove oldest entries
            entries_to_remove = len(entries_with_access) - self.max_cache_size + 100  # Remove extra for buffer
            
            for i in range(min(entries_to_remove, len(entries_with_access))):
                key, entry_dict = entries_with_access[i]
                query_hash = entry_dict.get("query_hash", "")
                
                # Remove metadata and vector
                await self.redis_client.delete(key)
                if query_hash:
                    vector_key = f"{self.vector_key_prefix}:{query_hash}"
                    await self.redis_client.delete(vector_key)
            
            log.info(f"Cleaned up {entries_to_remove} old cache entries")
            
        except Exception as e:
            log.error(f"Failed to manage cache size: {e}")
    
    async def _periodic_cleanup(self):
        """Periodically clean up expired entries and update analytics."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                if not self.is_ready:
                    continue
                
                # Clean up expired entries
                await self._cleanup_expired_entries()
                
                # Save analytics
                await self._save_analytics()
                
                # Update last cleanup time
                self.stats["last_cleanup"] = time.time()
                
            except Exception as e:
                log.error(f"Periodic cleanup failed: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _cleanup_expired_entries(self):
        """Clean up expired cache entries."""
        try:
            pattern = f"{self.metadata_key_prefix}:*"
            keys = await self.redis_client.keys(pattern)
            
            cleaned_count = 0
            current_time = time.time()
            
            for key in keys:
                try:
                    entry_data = await self.redis_client.get(key)
                    if not entry_data:
                        continue
                    
                    entry_dict = json.loads(entry_data)
                    created_at = entry_dict.get("created_at", 0)
                    ttl_seconds = entry_dict.get("ttl_seconds", self.default_ttl)
                    
                    if current_time - created_at > ttl_seconds:
                        # Remove expired entry
                        query_hash = entry_dict.get("query_hash", "")
                        await self.redis_client.delete(key)
                        
                        if query_hash:
                            vector_key = f"{self.vector_key_prefix}:{query_hash}"
                            await self.redis_client.delete(vector_key)
                        
                        cleaned_count += 1
                        
                except Exception:
                    continue
            
            if cleaned_count > 0:
                log.info(f"Cleaned up {cleaned_count} expired cache entries")
                
        except Exception as e:
            log.error(f"Failed to cleanup expired entries: {e}")
    
    async def _load_analytics(self):
        """Load analytics from Redis."""
        try:
            analytics_data = await self.redis_client.get(self.analytics_key)
            if analytics_data:
                saved_stats = json.loads(analytics_data)
                self.stats.update(saved_stats)
                log.debug("Loaded cache analytics from Redis")
        except Exception:
            pass  # Use default stats
    
    async def _save_analytics(self):
        """Save analytics to Redis."""
        try:
            await self.redis_client.setex(
                self.analytics_key,
                86400,  # 24 hours
                json.dumps(self.stats)
            )
        except Exception as e:
            log.warning(f"Failed to save analytics: {e}")
    
    async def get_analytics(self) -> Dict[str, Any]:
        """Get comprehensive cache analytics."""
        try:
            # Get current cache size
            pattern = f"{self.metadata_key_prefix}:*"
            keys = await self.redis_client.keys(pattern)
            current_size = len(keys)
            
            # Calculate hit rate
            total_requests = self.stats["cache_hits"] + self.stats["cache_misses"]
            hit_rate = (self.stats["cache_hits"] / total_requests) if total_requests > 0 else 0
            
            # Get memory usage (approximate)
            memory_usage = await self._estimate_memory_usage()
            
            return {
                "is_ready": self.is_ready,
                "strategy": self.strategy.value,
                "similarity_threshold": self.similarity_threshold,
                "current_size": current_size,
                "max_size": self.max_cache_size,
                "cache_hits": self.stats["cache_hits"],
                "cache_misses": self.stats["cache_misses"],
                "total_queries": self.stats["total_queries"],
                "hit_rate": hit_rate,
                "average_similarity": self.stats["average_similarity"],
                "memory_usage_mb": memory_usage,
                "last_cleanup": datetime.fromtimestamp(self.stats["last_cleanup"]).isoformat(),
                "ttl_seconds": self.default_ttl
            }
            
        except Exception as e:
            log.error(f"Failed to get analytics: {e}")
            return {"error": str(e)}
    
    async def _estimate_memory_usage(self) -> float:
        """Estimate memory usage of cache in MB."""
        try:
            # Get memory usage info from Redis
            info = await self.redis_client.info("memory")
            used_memory = info.get("used_memory", 0)
            
            # This is total Redis memory, not just our cache
            # In production, you'd want more precise measurement
            return used_memory / (1024 * 1024)  # Convert to MB
            
        except Exception:
            return 0.0
    
    async def clear_cache(self, pattern: Optional[str] = None) -> Dict[str, Any]:
        """Clear cache entries matching pattern."""
        try:
            if pattern:
                keys = await self.redis_client.keys(f"{self.metadata_key_prefix}:*{pattern}*")
            else:
                keys = await self.redis_client.keys(f"{self.metadata_key_prefix}:*")
            
            # Also clear corresponding vector keys
            vector_keys = []
            for key in keys:
                # Extract query hash from metadata key
                query_hash = key.split(":")[-1]
                vector_key = f"{self.vector_key_prefix}:{query_hash}"
                vector_keys.append(vector_key)
            
            # Delete all keys
            all_keys = keys + vector_keys
            if all_keys:
                await self.redis_client.delete(*all_keys)
            
            # Reset stats if clearing all
            if not pattern:
                self.stats = {
                    "cache_hits": 0,
                    "cache_misses": 0, 
                    "total_queries": 0,
                    "average_similarity": 0.0,
                    "last_cleanup": time.time()
                }
                await self._save_analytics()
            
            return {
                "cleared_entries": len(keys),
                "pattern": pattern or "all"
            }
            
        except Exception as e:
            log.error(f"Failed to clear cache: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on semantic cache."""
        health = {
            "status": "healthy" if self.is_ready else "unhealthy",
            "redis_connected": False,
            "embedding_model_loaded": False,
            "last_error": None
        }
        
        try:
            # Test Redis connection
            if self.redis_client:
                await self.redis_client.ping()
                health["redis_connected"] = True
            
            # Test embedding model
            if self.embedding_model:
                test_embedding = self._get_embedding("test query")
                health["embedding_model_loaded"] = test_embedding is not None
            
            if health["redis_connected"] and health["embedding_model_loaded"]:
                health["status"] = "healthy"
            
        except Exception as e:
            health["last_error"] = str(e)
            health["status"] = "unhealthy"
        
        return health

# Global semantic cache instance
_semantic_cache: Optional[SemanticCache] = None

async def get_semantic_cache(redis_url: str = "redis://localhost:6379",
                           embedding_model: str = "all-MiniLM-L6-v2",
                           similarity_threshold: float = 0.95) -> Optional[SemanticCache]:
    """Get global semantic cache instance."""
    global _semantic_cache
    
    if _semantic_cache is None:
        _semantic_cache = SemanticCache(
            redis_url=redis_url,
            embedding_model=embedding_model,
            similarity_threshold=similarity_threshold
        )
        # Give it time to initialize
        await asyncio.sleep(2)
    
    return _semantic_cache