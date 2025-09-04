"""Hybrid Retriever for LIQUID-HIVE
===============================

A hybrid retriever that can work with both FAISS and Qdrant,
enabling gradual migration and fallback capabilities.
"""

from __future__ import annotations

import asyncio
import logging
import os
from enum import Enum
from typing import Any, Optional

from hivemind.config import Settings

from .retriever import Document, Retriever  # Original FAISS-based retriever

try:
    from .qdrant_retriever import QdrantRetriever

    QDRANT_AVAILABLE = True
except ImportError:
    QdrantRetriever = None
    QDRANT_AVAILABLE = False

log = logging.getLogger(__name__)


class RetrievalMode(Enum):
    """Retrieval mode for hybrid operation."""

    FAISS_ONLY = "faiss_only"
    QDRANT_ONLY = "qdrant_only"
    HYBRID = "hybrid"
    AUTO = "auto"


class HybridRetriever:
    """Hybrid retriever supporting both FAISS and Qdrant backends.

    Features:
    - Automatic fallback between backends
    - Result fusion from multiple sources
    - Gradual migration support
    - Performance monitoring
    """

    def __init__(
        self,
        faiss_index_dir: str = None,
        embed_model_id: str = None,
        qdrant_url: str = None,
        mode: RetrievalMode = RetrievalMode.AUTO,
    ):
        self.mode = mode
        self.faiss_retriever: Optional[Retriever] = None
        self.qdrant_retriever: Optional[QdrantRetriever] = None
        self.is_ready = False

        # Performance tracking
        self.retrieval_stats = {
            "faiss_searches": 0,
            "qdrant_searches": 0,
            "hybrid_searches": 0,
            "fallback_used": 0,
            "total_searches": 0,
        }

        self._initialize_retrievers(faiss_index_dir, embed_model_id, qdrant_url)

    def _initialize_retrievers(self, faiss_index_dir: str, embed_model_id: str, qdrant_url: str):
        """Initialize both FAISS and Qdrant retrievers based on availability."""
        # Initialize FAISS retriever
        if faiss_index_dir and embed_model_id:
            try:
                self.faiss_retriever = Retriever(faiss_index_dir, embed_model_id)
                if self.faiss_retriever.is_ready:
                    log.info("✅ FAISS retriever initialized successfully")
                else:
                    log.warning("⚠️ FAISS retriever not ready")
            except Exception as e:
                log.error(f"Failed to initialize FAISS retriever: {e}")

        # Initialize Qdrant retriever
        if QDRANT_AVAILABLE and qdrant_url:
            try:
                self.qdrant_retriever = QdrantRetriever(
                    embed_model_id=embed_model_id, qdrant_url=qdrant_url
                )
                if self.qdrant_retriever.is_ready:
                    log.info("✅ Qdrant retriever initialized successfully")
                else:
                    log.warning("⚠️ Qdrant retriever not ready")
            except Exception as e:
                log.error(f"Failed to initialize Qdrant retriever: {e}")

        # Determine operational mode
        self._determine_mode()

    def _determine_mode(self):
        """Determine the best operational mode based on available retrievers."""
        faiss_ready = self.faiss_retriever and self.faiss_retriever.is_ready
        qdrant_ready = self.qdrant_retriever and self.qdrant_retriever.is_ready

        if self.mode == RetrievalMode.AUTO:
            if qdrant_ready and faiss_ready:
                self.mode = RetrievalMode.HYBRID
                log.info("🔗 Operating in HYBRID mode (both FAISS and Qdrant available)")
            elif qdrant_ready:
                self.mode = RetrievalMode.QDRANT_ONLY
                log.info("🎯 Operating in QDRANT_ONLY mode")
            elif faiss_ready:
                self.mode = RetrievalMode.FAISS_ONLY
                log.info("🗂️ Operating in FAISS_ONLY mode")
            else:
                log.error("❌ No retrievers available!")
                return

        self.is_ready = (
            self.mode in [RetrievalMode.FAISS_ONLY, RetrievalMode.HYBRID] and faiss_ready
        ) or (self.mode in [RetrievalMode.QDRANT_ONLY, RetrievalMode.HYBRID] and qdrant_ready)

        log.info(f"📊 Hybrid retriever ready: {self.is_ready}, mode: {self.mode.value}")

    async def search(
        self,
        query: str,
        k: int = 5,
        metadata_filter: Optional[dict[str, Any]] = None,
        prefer_qdrant: bool = True,
    ) -> list[Document]:
        """Perform hybrid search across available backends.

        Args:
            query: Search query
            k: Number of results to return
            metadata_filter: Optional metadata filtering (Qdrant only)
            prefer_qdrant: Whether to prefer Qdrant over FAISS

        Returns:
            List of Document objects
        """
        if not self.is_ready:
            log.warning("Hybrid retriever not ready")
            return []

        self.retrieval_stats["total_searches"] += 1

        try:
            if self.mode == RetrievalMode.QDRANT_ONLY:
                return await self._search_qdrant_only(query, k, metadata_filter)

            elif self.mode == RetrievalMode.FAISS_ONLY:
                return await self._search_faiss_only(query, k)

            elif self.mode == RetrievalMode.HYBRID:
                return await self._search_hybrid(query, k, metadata_filter, prefer_qdrant)

            else:
                log.error(f"Unknown retrieval mode: {self.mode}")
                return []

        except Exception as e:
            log.error(f"Hybrid search failed for query '{query[:50]}...': {e}")
            return await self._fallback_search(query, k)

    async def _search_qdrant_only(
        self, query: str, k: int, metadata_filter: Optional[dict[str, Any]]
    ) -> list[Document]:
        """Search using Qdrant only."""
        if not self.qdrant_retriever or not self.qdrant_retriever.is_ready:
            return []

        self.retrieval_stats["qdrant_searches"] += 1
        return await self.qdrant_retriever.search(query, k, metadata_filter)

    async def _search_faiss_only(self, query: str, k: int) -> list[Document]:
        """Search using FAISS only."""
        if not self.faiss_retriever or not self.faiss_retriever.is_ready:
            return []

        self.retrieval_stats["faiss_searches"] += 1
        return await self.faiss_retriever.search(query, k)

    async def _search_hybrid(
        self, query: str, k: int, metadata_filter: Optional[dict[str, Any]], prefer_qdrant: bool
    ) -> list[Document]:
        """Perform hybrid search using both backends."""
        self.retrieval_stats["hybrid_searches"] += 1

        # Determine search strategy
        qdrant_k = max(1, int(k * 0.7)) if prefer_qdrant else max(1, int(k * 0.4))
        faiss_k = k - qdrant_k

        # Perform searches concurrently
        qdrant_task = None
        faiss_task = None

        if self.qdrant_retriever and self.qdrant_retriever.is_ready:
            qdrant_task = asyncio.create_task(
                self.qdrant_retriever.search(query, qdrant_k, metadata_filter)
            )

        if self.faiss_retriever and self.faiss_retriever.is_ready:
            faiss_task = asyncio.create_task(self.faiss_retriever.search(query, faiss_k))

        # Collect results
        qdrant_results = []
        faiss_results = []

        if qdrant_task:
            try:
                qdrant_results = await qdrant_task
            except Exception as e:
                log.warning(f"Qdrant search failed: {e}")

        if faiss_task:
            try:
                faiss_results = await faiss_task
            except Exception as e:
                log.warning(f"FAISS search failed: {e}")

        # Fuse results
        return self._fuse_results(qdrant_results, faiss_results, k)

    def _fuse_results(
        self, qdrant_results: list[Document], faiss_results: list[Document], k: int
    ) -> list[Document]:
        """Fuse results from multiple backends."""
        # Simple fusion: interleave results with deduplication
        fused = []
        seen_content = set()

        # Interleave results
        max_len = max(len(qdrant_results), len(faiss_results))

        for i in range(max_len):
            # Add Qdrant result if available
            if i < len(qdrant_results):
                doc = qdrant_results[i]
                content_hash = hash(doc.page_content[:100])  # Hash first 100 chars

                if content_hash not in seen_content:
                    doc.metadata["source_backend"] = "qdrant"
                    fused.append(doc)
                    seen_content.add(content_hash)

                    if len(fused) >= k:
                        break

            # Add FAISS result if available
            if i < len(faiss_results) and len(fused) < k:
                doc = faiss_results[i]
                content_hash = hash(doc.page_content[:100])

                if content_hash not in seen_content:
                    doc.metadata["source_backend"] = "faiss"
                    fused.append(doc)
                    seen_content.add(content_hash)

                    if len(fused) >= k:
                        break

        return fused[:k]

    async def _fallback_search(self, query: str, k: int) -> list[Document]:
        """Fallback search when primary methods fail."""
        self.retrieval_stats["fallback_used"] += 1

        # Try Qdrant first if available
        if self.qdrant_retriever and self.qdrant_retriever.is_ready:
            try:
                return await self.qdrant_retriever.search(query, k)
            except Exception as e:
                log.warning(f"Qdrant fallback failed: {e}")

        # Try FAISS if available
        if self.faiss_retriever and self.faiss_retriever.is_ready:
            try:
                return await self.faiss_retriever.search(query, k)
            except Exception as e:
                log.warning(f"FAISS fallback failed: {e}")

        log.error("All retrieval backends failed")
        return []

    async def add_documents(
        self,
        file_paths: list[str],
        metadata: Optional[dict[str, Any]] = None,
        use_qdrant: bool = True,
    ) -> dict[str, Any]:
        """Add documents to the preferred backend."""
        if use_qdrant and self.qdrant_retriever and self.qdrant_retriever.is_ready:
            log.info(f"Adding {len(file_paths)} documents to Qdrant")
            return await self.qdrant_retriever.add_documents(file_paths, metadata)

        elif self.faiss_retriever and self.faiss_retriever.is_ready:
            log.info(f"Adding {len(file_paths)} documents to FAISS")
            return await self.faiss_retriever.add_documents(file_paths)

        else:
            return {"error": "No backend available for document indexing"}

    def format_context(self, documents: list[Document]) -> str:
        """Format context with backend information."""
        if not documents:
            return ""

        # Use Qdrant formatter if available (more advanced)
        if self.qdrant_retriever:
            return self.qdrant_retriever.format_context(documents)
        elif self.faiss_retriever:
            return self.faiss_retriever.format_context(documents)
        else:
            # Basic fallback formatting
            context_lines = []
            for i, doc in enumerate(documents):
                source = doc.metadata.get("source", "unknown")
                backend = doc.metadata.get("source_backend", "unknown")
                snippet = doc.page_content[:200].strip() + (
                    "..." if len(doc.page_content) > 200 else ""
                )
                context_lines.append(f"[{i+1}] Source: {source} (Backend: {backend})\n{snippet}")

            return "\n\n".join(context_lines)

    def get_status(self) -> dict[str, Any]:
        """Get comprehensive status of the hybrid retriever."""
        status = {
            "is_ready": self.is_ready,
            "mode": self.mode.value,
            "stats": self.retrieval_stats.copy(),
        }

        # Add backend-specific status
        if self.faiss_retriever:
            status["faiss"] = {
                "ready": self.faiss_retriever.is_ready,
                "doc_count": len(self.faiss_retriever.doc_store)
                if self.faiss_retriever.doc_store
                else 0,
            }

        if self.qdrant_retriever:
            status["qdrant"] = self.qdrant_retriever.get_health_status()

        return status

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on all backends."""
        health = {
            "overall_status": "healthy" if self.is_ready else "unhealthy",
            "mode": self.mode.value,
            "backends": {},
        }

        # Check FAISS health
        if self.faiss_retriever:
            try:
                # Simple test search
                test_results = await self.faiss_retriever.search("test", k=1)
                health["backends"]["faiss"] = {
                    "status": "healthy" if self.faiss_retriever.is_ready else "unhealthy",
                    "ready": self.faiss_retriever.is_ready,
                    "test_search": "passed" if test_results is not None else "failed",
                }
            except Exception as e:
                health["backends"]["faiss"] = {"status": "unhealthy", "error": str(e)}

        # Check Qdrant health
        if self.qdrant_retriever:
            try:
                qdrant_health = self.qdrant_retriever.get_health_status()
                test_results = await self.qdrant_retriever.search("test", k=1)

                health["backends"]["qdrant"] = {
                    **qdrant_health,
                    "test_search": "passed" if test_results is not None else "failed",
                }
            except Exception as e:
                health["backends"]["qdrant"] = {"status": "unhealthy", "error": str(e)}

        return health


# Factory function for easy initialization
def create_hybrid_retriever(settings: Settings = None) -> HybridRetriever:
    """Create hybrid retriever from settings."""
    if settings is None:
        settings = Settings()

    return HybridRetriever(
        faiss_index_dir=settings.rag_index,
        embed_model_id=settings.embed_model,
        qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        mode=RetrievalMode.AUTO,
    )
