"""Enhanced Qdrant-based Retriever for LIQUID-HIVE
=============================================

Production-grade vector database retriever using Qdrant with advanced features:
- Metadata filtering and hybrid search
- Real-time document ingestion
- Performance optimization
- Automatic scaling and sharding
- Advanced similarity metrics
"""

from __future__ import annotations

import hashlib
import logging
import os
import pathlib
import time
import uuid
from datetime import datetime
from typing import Any, Optional

try:
    import numpy as np
    from pypdf import PdfReader
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Batch,
        CollectionInfo,
        Distance,
        FieldCondition,
        Filter,
        MatchValue,
        OptimizersConfigDiff,
        PointStruct,
        Range,
        SearchRequest,
        UpdateCollection,
        UpdateStatus,
        VectorParams,
    )
    from sentence_transformers import SentenceTransformer

    DEPS_AVAILABLE = True
except ImportError as e:
    # Fallback types for when dependencies are not available
    QdrantClient = None
    VectorParams = Distance = PointStruct = None
    Filter = FieldCondition = Range = MatchValue = None
    np = SentenceTransformer = PdfReader = None
    DEPS_AVAILABLE = False
    logging.getLogger(__name__).warning(f"Qdrant dependencies not available: {e}")

from capsule_brain.security.input_sanitizer import sanitize_input

log = logging.getLogger(__name__)


class Document:
    """Enhanced document representation with metadata support."""

    def __init__(self, page_content: str, metadata: dict[str, Any]):
        self.page_content = page_content
        self.metadata = metadata
        self.id = metadata.get("id", str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "page_content": self.page_content, "metadata": self.metadata}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Document:
        return cls(data["page_content"], data["metadata"])


class QdrantRetriever:
    """Enhanced production-grade retriever using Qdrant vector database."""

    def __init__(
        self,
        collection_name: str = "liquid_hive_knowledge",
        embed_model_id: str = None,
        qdrant_url: str = None,
    ):
        self.collection_name = collection_name
        self.embed_model_id = embed_model_id or "all-MiniLM-L6-v2"
        self.qdrant_url = qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333")

        # Initialize components
        self.embedding_model: Optional[SentenceTransformer] = None
        self.qdrant_client: Optional[QdrantClient] = None
        self.is_ready = False
        self.embedding_dimension = None

        # Performance settings
        self.batch_size = 100
        self.max_retries = 3
        self.timeout = 30

        # Document processing settings
        self.chunk_size = 1000
        self.chunk_overlap = 200
        self.max_document_size = 10 * 1024 * 1024  # 10MB

        if DEPS_AVAILABLE:
            self._initialize()
        else:
            log.error("Cannot initialize QdrantRetriever: dependencies not available")

    def _initialize(self):
        """Initialize Qdrant client and embedding model."""
        try:
            # Initialize embedding model
            log.info(f"Loading embedding model: {self.embed_model_id}")
            self.embedding_model = SentenceTransformer(self.embed_model_id)
            self.embedding_dimension = self.embedding_model.get_sentence_embedding_dimension()

            # Initialize Qdrant client
            log.info(f"Connecting to Qdrant at: {self.qdrant_url}")
            self.qdrant_client = QdrantClient(url=self.qdrant_url, timeout=self.timeout)

            # Test connection
            collections = self.qdrant_client.get_collections()
            log.info(f"Connected to Qdrant. Available collections: {len(collections.collections)}")

            # Initialize collection
            self._ensure_collection_exists()

            self.is_ready = True
            log.info(
                f"QdrantRetriever initialized successfully with collection: {self.collection_name}"
            )

        except Exception as e:
            log.error(f"Failed to initialize QdrantRetriever: {e}")
            self.is_ready = False

    def _ensure_collection_exists(self):
        """Ensure the collection exists with proper configuration."""
        try:
            # Check if collection exists
            collections = self.qdrant_client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name in collection_names:
                log.info(f"Collection '{self.collection_name}' already exists")

                # Verify collection configuration
                collection_info = self.qdrant_client.get_collection(self.collection_name)
                actual_dimension = collection_info.config.params.vectors.size

                if actual_dimension != self.embedding_dimension:
                    log.warning(
                        f"Collection dimension mismatch: expected {self.embedding_dimension}, got {actual_dimension}"
                    )
                    return

            else:
                # Create new collection with optimized settings
                log.info(f"Creating new collection: {self.collection_name}")

                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dimension,
                        distance=Distance.COSINE,
                    ),
                    optimizers_config=OptimizersConfigDiff(
                        default_segment_number=2,
                        max_segment_size=20000,
                        memmap_threshold=20000,
                        indexing_threshold=20000,
                    ),
                    hnsw_config={
                        "m": 16,
                        "ef_construct": 200,
                        "full_scan_threshold": 10000,
                        "max_indexing_threads": 2,
                    },
                )
                log.info(
                    f"Created collection '{self.collection_name}' with dimension {self.embedding_dimension}"
                )

        except Exception as e:
            log.error(f"Failed to ensure collection exists: {e}")
            raise

    def get_collection_info(self) -> dict[str, Any]:
        """Get detailed collection information."""
        if not self.is_ready or not self.qdrant_client:
            return {"error": "Retriever not ready"}

        try:
            collection_info = self.qdrant_client.get_collection(self.collection_name)

            return {
                "name": self.collection_name,
                "status": collection_info.status,
                "optimizer_status": collection_info.optimizer_status,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "points_count": collection_info.points_count,
                "segments_count": len(collection_info.segments) if collection_info.segments else 0,
                "config": {
                    "vector_size": collection_info.config.params.vectors.size,
                    "distance": collection_info.config.params.vectors.distance.name,
                },
            }
        except Exception as e:
            return {"error": str(e)}

    async def add_documents(
        self, file_paths: list[str], metadata: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Add documents to Qdrant with enhanced processing and metadata."""
        if not self.is_ready:
            return {"error": "Retriever not ready", "indexed_files": []}

        results = {
            "indexed_files": [],
            "failed_files": [],
            "total_chunks": 0,
            "total_vectors": 0,
            "processing_time": 0,
            "errors": [],
        }

        start_time = time.time()

        try:
            all_points = []

            for file_path in file_paths:
                try:
                    file_results = await self._process_document(file_path, metadata)

                    if file_results["success"]:
                        all_points.extend(file_results["points"])
                        results["indexed_files"].append(file_path)
                        results["total_chunks"] += file_results["chunks"]
                    else:
                        results["failed_files"].append(
                            {"file": file_path, "error": file_results["error"]}
                        )
                        results["errors"].append(f"{file_path}: {file_results['error']}")

                except Exception as e:
                    error_msg = f"Failed to process {file_path}: {e!s}"
                    results["failed_files"].append({"file": file_path, "error": error_msg})
                    results["errors"].append(error_msg)
                    log.error(error_msg)

            # Batch upload points to Qdrant
            if all_points:
                results["total_vectors"] = await self._batch_upload_points(all_points)

            results["processing_time"] = time.time() - start_time

            log.info(
                f"Document indexing complete: {len(results['indexed_files'])} files, "
                f"{results['total_vectors']} vectors, {results['processing_time']:.2f}s"
            )

            return results

        except Exception as e:
            error_msg = f"Document indexing failed: {e!s}"
            results["errors"].append(error_msg)
            results["processing_time"] = time.time() - start_time
            log.error(error_msg)
            return results

    async def _process_document(
        self, file_path: str, base_metadata: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Process a single document into chunks with embeddings."""
        try:
            path = pathlib.Path(file_path)

            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}

            # Check file size
            file_size = path.stat().st_size
            if file_size > self.max_document_size:
                return {"success": False, "error": f"File too large: {file_size} bytes"}

            # Extract content based on file type
            content = self._extract_content(path)
            if not content:
                return {"success": False, "error": "Empty or unreadable content"}

            # Create chunks
            chunks = self._create_chunks(content)

            # Generate embeddings and create points
            points = []
            doc_hash = hashlib.md5(content.encode()).hexdigest()

            for i, chunk in enumerate(chunks):
                try:
                    # Generate embedding
                    embedding = self.embedding_model.encode(chunk)

                    # Create metadata
                    chunk_metadata = {
                        "source": str(path),
                        "filename": path.name,
                        "file_extension": path.suffix,
                        "file_size": file_size,
                        "document_hash": doc_hash,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "chunk_size": len(chunk),
                        "created_at": datetime.utcnow().isoformat(),
                        "content_type": self._detect_content_type(path, chunk),
                    }

                    # Add base metadata if provided
                    if base_metadata:
                        chunk_metadata.update(base_metadata)

                    # Create point
                    point = PointStruct(
                        id=str(uuid.uuid4()),
                        vector=embedding.tolist(),
                        payload={"content": chunk, "metadata": chunk_metadata},
                    )

                    points.append(point)

                except Exception as e:
                    log.warning(f"Failed to process chunk {i} of {file_path}: {e}")
                    continue

            return {
                "success": True,
                "points": points,
                "chunks": len(chunks),
                "content_size": len(content),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _extract_content(self, path: pathlib.Path) -> str:
        """Extract content from various file formats."""
        try:
            if path.suffix.lower() == ".pdf" and PdfReader:
                reader = PdfReader(str(path))
                content = ""
                for page in reader.pages:
                    content += page.extract_text() + "\n"
                return content

            elif path.suffix.lower() in [
                ".txt",
                ".md",
                ".py",
                ".js",
                ".html",
                ".css",
                ".json",
                ".yaml",
                ".yml",
            ]:
                return path.read_text(encoding="utf-8", errors="replace")

            else:
                # Try to read as text
                return path.read_text(encoding="utf-8", errors="replace")

        except Exception as e:
            log.error(f"Failed to extract content from {path}: {e}")
            return ""

    def _create_chunks(self, content: str) -> list[str]:
        """Create overlapping chunks from content."""
        # Sanitize content
        content = sanitize_input(content)

        if len(content) <= self.chunk_size:
            return [content]

        chunks = []
        start = 0

        while start < len(content):
            end = start + self.chunk_size
            chunk = content[start:end]

            # Try to break at sentence boundary
            if end < len(content):
                last_sentence = max(
                    chunk.rfind("."), chunk.rfind("!"), chunk.rfind("?"), chunk.rfind("\n")
                )
                if last_sentence > self.chunk_size // 2:
                    chunk = chunk[: last_sentence + 1]
                    end = start + last_sentence + 1

            chunks.append(chunk.strip())
            start = end - self.chunk_overlap

            if start >= len(content):
                break

        return [chunk for chunk in chunks if chunk.strip()]

    def _detect_content_type(self, path: pathlib.Path, content: str) -> str:
        """Detect content type for better categorization."""
        extension = path.suffix.lower()

        content_types = {
            ".py": "python_code",
            ".js": "javascript_code",
            ".html": "html_markup",
            ".css": "css_stylesheet",
            ".json": "json_data",
            ".md": "markdown_text",
            ".pdf": "pdf_document",
            ".txt": "plain_text",
        }

        detected = content_types.get(extension, "unknown")

        # Additional content-based detection
        if detected == "plain_text" or detected == "unknown":
            content_lower = content.lower()
            if any(
                keyword in content_lower for keyword in ["def ", "import ", "class ", "return "]
            ):
                detected = "code"
            elif any(keyword in content_lower for keyword in ["# ", "## ", "### "]):
                detected = "markdown_text"

        return detected

    async def _batch_upload_points(self, points: list[PointStruct]) -> int:
        """Upload points to Qdrant in batches."""
        uploaded_count = 0

        for i in range(0, len(points), self.batch_size):
            batch = points[i : i + self.batch_size]

            try:
                operation_info = self.qdrant_client.upsert(
                    collection_name=self.collection_name, wait=True, points=batch
                )

                if operation_info.status == UpdateStatus.COMPLETED:
                    uploaded_count += len(batch)
                    log.debug(f"Uploaded batch {i//self.batch_size + 1}: {len(batch)} points")
                else:
                    log.warning(
                        f"Batch upload {i//self.batch_size + 1} status: {operation_info.status}"
                    )

            except Exception as e:
                log.error(f"Failed to upload batch {i//self.batch_size + 1}: {e}")
                continue

        return uploaded_count

    async def search(
        self,
        query: str,
        k: int = 5,
        metadata_filter: Optional[dict[str, Any]] = None,
        score_threshold: float = 0.0,
    ) -> list[Document]:
        """Enhanced search with metadata filtering and scoring."""
        if not self.is_ready:
            log.warning("Retriever not ready for search")
            return []

        if not query.strip():
            return []

        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query)

            # Build filter if metadata_filter provided
            search_filter = None
            if metadata_filter:
                search_filter = self._build_filter(metadata_filter)

            # Perform search
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding.tolist(),
                limit=k,
                score_threshold=score_threshold,
                query_filter=search_filter,
                with_payload=True,
                with_vectors=False,  # Don't return vectors to save bandwidth
            )

            # Convert to Document objects
            documents = []
            for result in search_results:
                try:
                    content = result.payload.get("content", "")
                    metadata = result.payload.get("metadata", {})

                    # Add search-specific metadata
                    metadata["search_score"] = result.score
                    metadata["search_query"] = query
                    metadata["search_timestamp"] = datetime.utcnow().isoformat()

                    documents.append(Document(content, metadata))

                except Exception as e:
                    log.warning(f"Failed to process search result: {e}")
                    continue

            log.debug(f"Search for '{query[:50]}...' returned {len(documents)} results")
            return documents

        except Exception as e:
            log.error(f"Search failed for query '{query[:50]}...': {e}")
            return []

    def _build_filter(self, metadata_filter: dict[str, Any]) -> Filter:
        """Build Qdrant filter from metadata conditions."""
        conditions = []

        for key, value in metadata_filter.items():
            field_key = f"metadata.{key}"

            if isinstance(value, dict):
                # Handle range queries
                if "gte" in value:
                    conditions.append(FieldCondition(key=field_key, range=Range(gte=value["gte"])))
                if "lte" in value:
                    conditions.append(FieldCondition(key=field_key, range=Range(lte=value["lte"])))
                if "gt" in value:
                    conditions.append(FieldCondition(key=field_key, range=Range(gt=value["gt"])))
                if "lt" in value:
                    conditions.append(FieldCondition(key=field_key, range=Range(lt=value["lt"])))
            else:
                # Handle exact match
                conditions.append(FieldCondition(key=field_key, match=MatchValue(value=value)))

        return Filter(must=conditions) if conditions else None

    async def hybrid_search(self, query: str, k: int = 5, alpha: float = 0.7) -> list[Document]:
        """Hybrid search combining semantic and keyword matching."""
        # This is a simplified implementation
        # In production, you might want to implement full-text search integration

        # Semantic search (primary)
        semantic_results = await self.search(query, k=k)

        # For now, return semantic results
        # TODO: Implement keyword search and fusion
        return semantic_results

    async def delete_by_metadata(self, metadata_filter: dict[str, Any]) -> dict[str, Any]:
        """Delete documents matching metadata criteria."""
        if not self.is_ready:
            return {"error": "Retriever not ready"}

        try:
            search_filter = self._build_filter(metadata_filter)

            result = self.qdrant_client.delete(
                collection_name=self.collection_name, points_selector=search_filter
            )

            return {"status": "success", "operation_id": result.operation_id, "deleted": True}

        except Exception as e:
            return {"error": str(e)}

    async def update_collection_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Update collection configuration for optimization."""
        if not self.is_ready:
            return {"error": "Retriever not ready"}

        try:
            # Update optimizer configuration
            if "optimizers_config" in config:
                optimizers = OptimizersConfigDiff(**config["optimizers_config"])

                self.qdrant_client.update_collection(
                    collection_name=self.collection_name, optimizers_config=optimizers
                )

            return {"status": "success", "updated": True}

        except Exception as e:
            return {"error": str(e)}

    def format_context(self, documents: list[Document]) -> str:
        """Format retrieved documents as context with enhanced metadata."""
        if not documents:
            return ""

        context_parts = []
        for i, doc in enumerate(documents):
            source = doc.metadata.get("source", "unknown")
            content_type = doc.metadata.get("content_type", "text")
            score = doc.metadata.get("search_score", 0.0)

            # Truncate content for display
            content = doc.page_content
            if len(content) > 300:
                content = content[:300] + "..."

            context_parts.append(
                f"[{i+1}] Source: {source} (Type: {content_type}, Score: {score:.3f})\n{content}"
            )

        return "\n\n".join(context_parts)

    def get_health_status(self) -> dict[str, Any]:
        """Get comprehensive health status of the retriever."""
        status = {
            "is_ready": self.is_ready,
            "embedding_model": self.embed_model_id,
            "embedding_dimension": self.embedding_dimension,
            "qdrant_url": self.qdrant_url,
            "collection_name": self.collection_name,
        }

        if self.is_ready and self.qdrant_client:
            try:
                collection_info = self.get_collection_info()
                status.update(collection_info)
                status["status"] = "healthy"
            except Exception as e:
                status["status"] = "unhealthy"
                status["error"] = str(e)
        else:
            status["status"] = "not_ready"

        return status
