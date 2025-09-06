from src.logging_config import get_logger
"""RAG (Retrieval-Augmented Generation) Module
==========================================

This module provides document retrieval and context formatting capabilities
for the LIQUID-HIVE system. It includes:

- Document indexing with FAISS vector store
- Semantic search using sentence transformers
- Context formatting for LLM prompts
"""

from .citations import format_context
from .retriever import Document, Retriever

__all__ = ["Retriever", "Document", "format_context"]
