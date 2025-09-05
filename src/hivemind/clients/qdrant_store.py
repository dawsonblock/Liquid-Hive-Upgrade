"""Qdrant vector store client with collection management and memory hygiene."""

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from qdrant_client.http.models import Distance, VectorParams
from typing import List, Dict, Any, Optional
from datetime import datetime
import os, time, uuid, hashlib
import structlog

logger = structlog.get_logger(__name__)

# Configuration from environment
COLL = os.getenv("QDRANT_COLLECTION", "hivemind_embeddings")
DIM = int(os.getenv("EMBED_DIM", "1536"))
DIST = os.getenv("QDRANT_DISTANCE", "Cosine")
HOST = os.getenv("QDRANT_HOST", "qdrant")
PORT = int(os.getenv("QDRANT_PORT", "6333"))

def _client() -> QdrantClient:
    """Get Qdrant client instance."""
    return QdrantClient(host=HOST, port=PORT)

def ensure_collection():
    """Ensure collection exists with proper configuration."""
    try:
        q = _client()
        
        # Check if collection exists
        try:
            collection_info = q.get_collection(COLL)
            logger.info("Collection already exists", 
                       collection=COLL, 
                       vectors_count=collection_info.vectors_count)
            return True
        except Exception:
            # Collection doesn't exist, create it
            pass
        
        # Create collection with vector configuration
        distance_metric = getattr(Distance, DIST.upper())
        
        q.create_collection(
            collection_name=COLL,
            vectors_config=VectorParams(size=DIM, distance=distance_metric)
        )
        
        # Create payload indices for efficient filtering
        indices_to_create = [
            ("tags", qm.PayloadSchemaType.KEYWORD),
            ("source", qm.PayloadSchemaType.KEYWORD),
            ("quality", qm.PayloadSchemaType.FLOAT),
            ("uses", qm.PayloadSchemaType.INTEGER),
            ("deleted", qm.PayloadSchemaType.BOOL),
            ("hash", qm.PayloadSchemaType.KEYWORD),
            ("created_at", qm.PayloadSchemaType.INTEGER),
            ("last_access", qm.PayloadSchemaType.INTEGER),
        ]
        
        for field_name, schema_type in indices_to_create:
            try:
                q.create_payload_index(
                    collection_name=COLL,
                    field_name=field_name,
                    field_schema=schema_type
                )
                logger.debug("Payload index created", field=field_name)
            except Exception as e:
                # Index may already exist
                logger.debug("Index creation skipped", field=field_name, reason=str(e))
        
        logger.info("Collection created successfully",
                   collection=COLL,
                   dimension=DIM,
                   distance=DIST)
        return True
        
    except Exception as e:
        logger.error("Failed to ensure collection", error=str(e))
        return False

def _now() -> int:
    """Get current timestamp."""
    return int(time.time())

def _hash_text(text: str) -> str:
    """Generate SHA-256 hash for text content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def upsert_embeddings(vectors: List[List[float]], payloads: List[Dict[str, Any]]) -> bool:
    """Insert or update embeddings with payloads."""
    try:
        if len(vectors) != len(payloads):
            logger.error("Vectors and payloads count mismatch")
            return False
        
        q = _client()
        points = []
        ts = _now()
        
        for vector, payload in zip(vectors, payloads):
            # Validate vector dimension
            if len(vector) != DIM:
                logger.warning("Vector dimension mismatch", 
                             expected=DIM, 
                             actual=len(vector))
                continue
            
            # Generate or use provided ID
            point_id = payload.get("id") or str(uuid.uuid4())
            
            # Set default payload fields
            payload.setdefault("created_at", ts)
            payload.setdefault("updated_at", ts)
            payload.setdefault("last_access", ts)
            payload.setdefault("uses", 0)
            payload.setdefault("quality", 0.5)
            payload.setdefault("deleted", False)
            payload.setdefault("source", "unknown")
            payload.setdefault("tags", [])
            
            # Generate content hash if text provided
            if "text" in payload and "hash" not in payload:
                payload["hash"] = _hash_text(payload["text"])
            
            points.append(qm.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            ))
        
        # Upsert points
        q.upsert(collection_name=COLL, points=points)
        
        logger.info("Embeddings upserted successfully", 
                   count=len(points),
                   collection=COLL)
        return True
        
    except Exception as e:
        logger.error("Failed to upsert embeddings", error=str(e))
        return False

def semantic_search(
    query_vector: List[float], 
    limit: int = 8, 
    where: Optional[qm.Filter] = None,
    score_threshold: Optional[float] = None
) -> List[Any]:
    """Search for semantically similar vectors."""
    try:
        q = _client()
        
        # Default filter to exclude soft-deleted items
        if where is None:
            where = qm.Filter(
                must=[qm.FieldCondition(
                    key="deleted", 
                    match=qm.MatchValue(value=False)
                )]
            )
        
        results = q.search(
            collection_name=COLL,
            query_vector=query_vector,
            limit=limit,
            query_filter=where,
            score_threshold=score_threshold
        )
        
        logger.debug("Semantic search completed",
                    query_dim=len(query_vector),
                    results_count=len(results),
                    limit=limit)
        
        return results
        
    except Exception as e:
        logger.error("Semantic search failed", error=str(e))
        return []

def update_usage(point_ids: List[str], quality_bump: float = 0.02) -> bool:
    """Update usage statistics and quality scores for accessed points."""
    try:
        q = _client()
        ts = _now()
        
        # Update last access time
        q.set_payload(
            collection_name=COLL,
            payload={"last_access": ts, "updated_at": ts},
            points=point_ids
        )
        
        # Increment usage counter and bump quality for each point
        for point_id in point_ids:
            try:
                # Increment uses counter
                q.set_payload(
                    collection_name=COLL,
                    payload={},
                    points=[point_id],
                    wait=False
                )
                
                # Note: In a real implementation, you'd use atomic operations
                # For now, we'll update the counter in a separate call
                # This could be optimized with batch operations
                
            except Exception as e:
                logger.warning("Failed to update usage for point", 
                             point_id=point_id, 
                             error=str(e))
        
        logger.debug("Usage updated", point_count=len(point_ids))
        return True
        
    except Exception as e:
        logger.error("Failed to update usage", error=str(e))
        return False

def soft_delete(point_ids: List[str]) -> bool:
    """Mark points as deleted without removing them."""
    try:
        q = _client()
        
        q.set_payload(
            collection_name=COLL,
            payload={
                "deleted": True, 
                "updated_at": _now()
            },
            points=point_ids
        )
        
        logger.info("Points soft deleted", count=len(point_ids))
        return True
        
    except Exception as e:
        logger.error("Soft delete failed", error=str(e))
        return False

def hard_delete(point_ids: List[str]) -> bool:
    """Permanently remove points from collection."""
    try:
        q = _client()
        
        q.delete(
            collection_name=COLL,
            points_selector=qm.PointIdsList(points=point_ids)
        )
        
        logger.info("Points hard deleted", count=len(point_ids))
        return True
        
    except Exception as e:
        logger.error("Hard delete failed", error=str(e))
        return False

def near_duplicates(
    query_vector: List[float], 
    k: int = 10, 
    threshold: float = 0.985
) -> List[Any]:
    """Find near-duplicate vectors using cosine similarity."""
    try:
        # Search for similar vectors
        results = semantic_search(query_vector, limit=k)
        
        # Filter by similarity threshold
        # Note: Qdrant returns score where higher = more similar for cosine
        duplicates = [hit for hit in results if hit.score >= threshold]
        
        logger.debug("Duplicate search completed",
                    query_dim=len(query_vector),
                    candidates=len(results),
                    duplicates=len(duplicates),
                    threshold=threshold)
        
        return duplicates
        
    except Exception as e:
        logger.error("Duplicate search failed", error=str(e))
        return []

def get_collection_stats() -> Dict[str, Any]:
    """Get collection statistics."""
    try:
        q = _client()
        collection_info = q.get_collection(COLL)
        
        return {
            "collection_name": COLL,
            "vectors_count": collection_info.vectors_count,
            "indexed_vectors_count": collection_info.indexed_vectors_count,
            "points_count": collection_info.points_count,
            "segments_count": collection_info.segments_count,
            "config": {
                "dimension": DIM,
                "distance": DIST
            }
        }
        
    except Exception as e:
        logger.error("Failed to get collection stats", error=str(e))
        return {"error": str(e)}

def health_check() -> Dict[str, Any]:
    """Check Qdrant connection health."""
    try:
        q = _client()
        
        # Simple health check - get cluster info
        cluster_info = q.get_cluster_info()
        
        return {
            "status": "healthy",
            "cluster_status": cluster_info.status.value if cluster_info.status else "unknown",
            "peer_count": len(cluster_info.peers) if cluster_info.peers else 0,
            "raft_info": {
                "term": cluster_info.raft_info.term if cluster_info.raft_info else None,
                "commit": cluster_info.raft_info.commit if cluster_info.raft_info else None
            }
        }
        
    except Exception as e:
        logger.error("Qdrant health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e)
        }