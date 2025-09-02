"""
FAISS to Qdrant Migration Utility
===============================

Utility to migrate existing FAISS indexes to Qdrant vector database
while preserving document metadata and search functionality.
"""

import asyncio
import json
import logging
import os
import pathlib
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer

    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from hivemind.rag.qdrant_retriever import Document, QdrantRetriever

log = logging.getLogger(__name__)


class FaissToQdrantMigrator:
    """Migrate FAISS indexes to Qdrant with enhanced metadata."""

    def __init__(self, faiss_index_dir: str, qdrant_retriever: QdrantRetriever):
        self.faiss_index_dir = pathlib.Path(faiss_index_dir)
        self.qdrant_retriever = qdrant_retriever
        self.logger = logging.getLogger(__name__)

    async def migrate(self, backup_faiss: bool = True) -> Dict[str, Any]:
        """
        Migrate FAISS index to Qdrant.

        Args:
            backup_faiss: Whether to create a backup of FAISS index

        Returns:
            Migration results and statistics
        """
        if not FAISS_AVAILABLE:
            return {"error": "FAISS not available for migration"}

        results = {
            "status": "started",
            "faiss_documents": 0,
            "qdrant_documents": 0,
            "migrated_documents": 0,
            "failed_documents": 0,
            "backup_created": False,
            "migration_time": 0,
            "errors": [],
        }

        start_time = asyncio.get_event_loop().time()

        try:
            # Backup FAISS index if requested
            if backup_faiss:
                await self._backup_faiss_index()
                results["backup_created"] = True

            # Load FAISS index and documents
            faiss_data = await self._load_faiss_data()
            if not faiss_data["success"]:
                results["errors"].append(
                    f"Failed to load FAISS data: {faiss_data['error']}"
                )
                return results

            results["faiss_documents"] = len(faiss_data["documents"])

            # Convert FAISS documents to Qdrant format
            qdrant_documents = await self._convert_documents(
                faiss_data["documents"], faiss_data["vectors"]
            )

            # Upload to Qdrant
            upload_results = await self._upload_to_qdrant(qdrant_documents)
            results.update(upload_results)

            results["migration_time"] = asyncio.get_event_loop().time() - start_time
            results["status"] = (
                "completed" if not results["errors"] else "completed_with_errors"
            )

            self.logger.info(
                f"Migration completed: {results['migrated_documents']} documents migrated"
            )

        except Exception as e:
            error_msg = f"Migration failed: {str(e)}"
            results["errors"].append(error_msg)
            results["status"] = "failed"
            self.logger.error(error_msg)

        return results

    async def _backup_faiss_index(self):
        """Create backup of existing FAISS index."""
        try:
            backup_dir = (
                self.faiss_index_dir.parent
                / f"faiss_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            backup_dir.mkdir(exist_ok=True)

            # Copy index files
            for file_path in self.faiss_index_dir.glob("*"):
                if file_path.is_file():
                    import shutil

                    shutil.copy2(file_path, backup_dir / file_path.name)

            self.logger.info(f"FAISS backup created at: {backup_dir}")

        except Exception as e:
            self.logger.warning(f"Failed to create FAISS backup: {e}")

    async def _load_faiss_data(self) -> Dict[str, Any]:
        """Load FAISS index and document store."""
        try:
            index_path = self.faiss_index_dir / "faiss_index.bin"
            doc_store_path = self.faiss_index_dir / "doc_store.json"

            if not index_path.exists() or not doc_store_path.exists():
                return {
                    "success": False,
                    "error": "FAISS index or document store not found",
                }

            # Load FAISS index
            faiss_index = faiss.read_index(str(index_path))

            # Load document store
            with open(doc_store_path, "r", encoding="utf-8") as f:
                doc_data = json.load(f)

            # Convert to Document objects
            documents = []
            for doc_dict in doc_data:
                if isinstance(doc_dict, dict):
                    if "page_content" in doc_dict and "metadata" in doc_dict:
                        documents.append(Document.from_dict(doc_dict))
                    else:
                        # Handle old format
                        documents.append(
                            Document(
                                page_content=doc_dict.get("content", ""),
                                metadata=doc_dict.get("metadata", {}),
                            )
                        )

            # Extract vectors
            vectors = []
            for i in range(faiss_index.ntotal):
                vector = faiss_index.reconstruct(i)
                vectors.append(vector)

            return {
                "success": True,
                "documents": documents,
                "vectors": vectors,
                "index_info": {
                    "total_vectors": faiss_index.ntotal,
                    "dimension": faiss_index.d,
                    "metric_type": "L2",  # FAISS default
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _convert_documents(
        self, documents: List[Document], vectors: List[np.ndarray]
    ) -> List[Dict[str, Any]]:
        """Convert FAISS documents to Qdrant format with enhanced metadata."""
        converted_docs = []

        for i, (doc, vector) in enumerate(zip(documents, vectors)):
            try:
                # Enhance metadata with migration info
                enhanced_metadata = doc.metadata.copy()
                enhanced_metadata.update(
                    {
                        "migrated_from": "faiss",
                        "migration_timestamp": datetime.utcnow().isoformat(),
                        "original_index": i,
                        "faiss_vector_id": i,
                        "content_length": len(doc.page_content),
                        "content_hash": hash(doc.page_content),
                    }
                )

                # Ensure required fields
                if "source" not in enhanced_metadata:
                    enhanced_metadata["source"] = "unknown"
                if "created_at" not in enhanced_metadata:
                    enhanced_metadata["created_at"] = enhanced_metadata[
                        "migration_timestamp"
                    ]

                converted_docs.append(
                    {
                        "id": str(uuid.uuid4()),
                        "content": doc.page_content,
                        "vector": vector.tolist(),
                        "metadata": enhanced_metadata,
                    }
                )

            except Exception as e:
                self.logger.warning(f"Failed to convert document {i}: {e}")
                continue

        return converted_docs

    async def _upload_to_qdrant(
        self, documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Upload converted documents to Qdrant."""
        results = {"migrated_documents": 0, "failed_documents": 0, "errors": []}

        try:
            from qdrant_client.models import PointStruct

            # Convert to Qdrant points
            points = []
            for doc in documents:
                try:
                    point = PointStruct(
                        id=doc["id"],
                        vector=doc["vector"],
                        payload={
                            "content": doc["content"],
                            "metadata": doc["metadata"],
                        },
                    )
                    points.append(point)

                except Exception as e:
                    results["failed_documents"] += 1
                    results["errors"].append(f"Failed to create point: {e}")
                    continue

            # Batch upload to Qdrant
            if points:
                uploaded_count = await self.qdrant_retriever._batch_upload_points(
                    points
                )
                results["migrated_documents"] = uploaded_count
                results["qdrant_documents"] = uploaded_count

        except Exception as e:
            error_msg = f"Failed to upload to Qdrant: {str(e)}"
            results["errors"].append(error_msg)
            self.logger.error(error_msg)

        return results

    async def verify_migration(
        self, sample_queries: List[str] = None
    ) -> Dict[str, Any]:
        """Verify migration by comparing search results."""
        if not sample_queries:
            sample_queries = [
                "artificial intelligence",
                "machine learning",
                "neural networks",
                "python programming",
                "data science",
            ]

        verification_results = {
            "total_queries": len(sample_queries),
            "successful_searches": 0,
            "failed_searches": 0,
            "average_results_per_query": 0,
            "sample_results": [],
            "errors": [],
        }

        total_results = 0

        for query in sample_queries:
            try:
                results = await self.qdrant_retriever.search(query, k=5)

                verification_results["successful_searches"] += 1
                total_results += len(results)

                if len(verification_results["sample_results"]) < 3:
                    verification_results["sample_results"].append(
                        {
                            "query": query,
                            "results_count": len(results),
                            "sample_content": (
                                results[0].page_content[:200] if results else None
                            ),
                        }
                    )

            except Exception as e:
                verification_results["failed_searches"] += 1
                verification_results["errors"].append(f"Query '{query}' failed: {e}")

        if verification_results["successful_searches"] > 0:
            verification_results["average_results_per_query"] = (
                total_results / verification_results["successful_searches"]
            )

        return verification_results


async def run_migration(
    faiss_index_dir: str = "/app/rag_index",
    qdrant_url: str = "http://localhost:6333",
    embed_model: str = "all-MiniLM-L6-v2",
) -> Dict[str, Any]:
    """Convenience function to run complete migration."""

    # Initialize Qdrant retriever
    qdrant_retriever = QdrantRetriever(
        collection_name="liquid_hive_knowledge",
        embed_model_id=embed_model,
        qdrant_url=qdrant_url,
    )

    # Wait for initialization
    await asyncio.sleep(2)

    if not qdrant_retriever.is_ready:
        return {"error": "Qdrant retriever not ready"}

    # Create migrator and run migration
    migrator = FaissToQdrantMigrator(faiss_index_dir, qdrant_retriever)

    print("🔄 Starting FAISS to Qdrant migration...")
    migration_results = await migrator.migrate(backup_faiss=True)

    print(f"📊 Migration Results:")
    print(f"   - Status: {migration_results['status']}")
    print(f"   - Migrated: {migration_results['migrated_documents']} documents")
    print(f"   - Failed: {migration_results['failed_documents']} documents")
    print(f"   - Time: {migration_results['migration_time']:.2f}s")

    if migration_results["errors"]:
        print(f"   - Errors: {len(migration_results['errors'])}")

    # Verify migration
    if migration_results["migrated_documents"] > 0:
        print("\n🔍 Verifying migration...")
        verification = await migrator.verify_migration()
        print(
            f"   - Successful searches: {verification['successful_searches']}/{verification['total_queries']}"
        )
        print(
            f"   - Average results per query: {verification['average_results_per_query']:.1f}"
        )

    return migration_results


if __name__ == "__main__":
    import sys

    # Run migration
    try:
        results = asyncio.run(run_migration())

        if results.get("status") in ["completed", "completed_with_errors"]:
            print("\n✅ Migration completed successfully!")
            sys.exit(0)
        else:
            print(f"\n❌ Migration failed: {results.get('errors', ['Unknown error'])}")
            sys.exit(1)

    except Exception as e:
        print(f"\n💥 Migration crashed: {e}")
        sys.exit(1)
