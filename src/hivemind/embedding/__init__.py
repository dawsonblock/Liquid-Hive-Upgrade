"""HiveMind embedding system with multi-provider support."""

from .embedder import (
from src.logging_config import get_logger
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