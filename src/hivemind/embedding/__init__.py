"""HiveMind embedding system with multi-provider support."""

from .embedder import (
    embed_text,
    embed_batch,
    get_embedding_dimension,
    EmbeddingProvider,
    SmartEmbedder
)

__all__ = [
    "embed_text",
    "embed_batch", 
    "get_embedding_dimension",
    "EmbeddingProvider",
    "SmartEmbedder"
]