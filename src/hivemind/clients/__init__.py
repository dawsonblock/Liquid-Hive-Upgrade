"""HiveMind client integrations for vector storage and caching."""

from .qdrant_store import (
from src.logging_config import get_logger
    ensure_collection,
    upsert_embeddings,
    semantic_search,
    soft_delete,
    hard_delete,
    near_duplicates,
    update_usage
)

from .redis_cache import (
    kv_set,
    kv_get,
    rate_limit
)

__all__ = [
    # Qdrant vector operations
    "ensure_collection",
    "upsert_embeddings", 
    "semantic_search",
    "soft_delete",
    "hard_delete",
    "near_duplicates",
    "update_usage",
    # Redis cache operations
    "kv_set",
    "kv_get", 
    "rate_limit"
]