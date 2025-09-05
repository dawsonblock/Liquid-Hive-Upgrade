"""Memory management API router with vector storage and caching."""

import hashlib
import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field, validator
import structlog

from src.hivemind.clients.qdrant_store import (
    ensure_collection, upsert_embeddings, semantic_search,
    soft_delete, hard_delete, get_collection_stats, health_check as qdrant_health
)
from src.hivemind.clients.redis_cache import (
    kv_set, kv_get, rate_limit, cache_query_result, get_cached_query,
    health_check as redis_health
)
from src.hivemind.embedding.embedder import embed_text, embed_batch, get_provider_status
from src.hivemind.maintenance.memory_gc import run_gc, update_quality_scores

logger = structlog.get_logger(__name__)

memory_router = APIRouter(prefix="/api/memory", tags=["memory"])

# Request/Response Models
class MemoryIngestRequest(BaseModel):
    """Request model for memory ingestion."""
    
    text: str = Field(..., min_length=1, max_length=50000, description="Text content to store")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    source: str = Field(default="api", description="Source of the memory")
    quality: float = Field(default=0.5, ge=0.0, le=1.0, description="Initial quality score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('tags')
    def validate_tags(cls, v):
        """Validate tags format."""
        if len(v) > 20:
            raise ValueError("Maximum 20 tags allowed")
        for tag in v:
            if not isinstance(tag, str) or len(tag) > 50:
                raise ValueError("Tags must be strings with max length 50")
        return v

class MemoryIngestResponse(BaseModel):
    """Response model for memory ingestion."""
    
    id: str = Field(..., description="Unique identifier for stored memory")
    status: str = Field(..., description="Ingestion status")
    embedding_dimension: int = Field(..., description="Embedding vector dimension")
    duplicate_skipped: bool = Field(False, description="Whether duplicate was skipped")

class MemoryQueryRequest(BaseModel):
    """Request model for memory queries."""
    
    query: Optional[str] = Field(None, description="Text query for semantic search")
    vector: Optional[List[float]] = Field(None, description="Pre-computed query vector")
    limit: int = Field(default=8, ge=1, le=100, description="Maximum results to return")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score")
    include_deleted: bool = Field(default=False, description="Include soft-deleted memories")
    tags_filter: Optional[List[str]] = Field(None, description="Filter by tags")
    source_filter: Optional[str] = Field(None, description="Filter by source")

class MemoryQueryResponse(BaseModel):
    """Response model for memory queries."""
    
    results: List[Dict[str, Any]] = Field(..., description="Search results")
    query_time_ms: float = Field(..., description="Query execution time")
    cached: bool = Field(False, description="Whether results were cached")
    total_results: int = Field(..., description="Number of results returned")

class MemoryStatsResponse(BaseModel):
    """Response model for memory statistics."""
    
    collection_stats: Dict[str, Any]
    cache_stats: Dict[str, Any] 
    provider_status: Dict[str, Any]
    timestamp: float

class GCRequest(BaseModel):
    """Request model for garbage collection."""
    
    force: bool = Field(default=False, description="Force GC even if not scheduled")
    dry_run: bool = Field(default=False, description="Show what would be deleted")

class GCResponse(BaseModel):
    """Response model for garbage collection."""
    
    status: str
    stats: Dict[str, Any]
    duration_seconds: float

# Utility functions
def _generate_query_hash(query: str, limit: int, filters: Dict[str, Any]) -> str:
    """Generate hash for query caching."""
    query_data = f"{query}:{limit}:{str(sorted(filters.items()))}"
    return hashlib.md5(query_data.encode()).hexdigest()

def _build_qdrant_filter(
    include_deleted: bool = False,
    tags_filter: Optional[List[str]] = None,
    source_filter: Optional[str] = None
) -> Optional[Any]:
    """Build Qdrant filter from request parameters."""
    try:
        from qdrant_client.http import models as qm
        
        conditions = []
        
        # Deleted filter
        if not include_deleted:
            conditions.append(
                qm.FieldCondition(
                    key="deleted", 
                    match=qm.MatchValue(value=False)
                )
            )
        
        # Tags filter
        if tags_filter:
            for tag in tags_filter:
                conditions.append(
                    qm.FieldCondition(
                        key="tags",
                        match=qm.MatchValue(value=tag)
                    )
                )
        
        # Source filter
        if source_filter:
            conditions.append(
                qm.FieldCondition(
                    key="source",
                    match=qm.MatchValue(value=source_filter)
                )
            )
        
        return qm.Filter(must=conditions) if conditions else None
        
    except Exception as e:
        logger.error("Failed to build filter", error=str(e))
        return None

# Rate limiting dependency
def check_rate_limit(client_ip: str = "unknown") -> bool:
    """Check rate limit for API calls."""
    return rate_limit(f"memory_api:{client_ip}", limit=100, window_sec=60)

# API Endpoints
@memory_router.post("/init")
async def initialize_memory_system():
    """Initialize the memory system (create collections, indices)."""
    try:
        logger.info("Initializing memory system")
        
        # Ensure Qdrant collection exists
        success = ensure_collection()
        
        if success:
            logger.info("Memory system initialized successfully")
            return {
                "status": "initialized",
                "message": "Memory system ready for use",
                "collection_created": True
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize Qdrant collection"
            )
            
    except Exception as e:
        logger.error("Memory system initialization failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Initialization failed: {str(e)}"
        )

@memory_router.post("/ingest", response_model=MemoryIngestResponse)
async def ingest_memory(request: MemoryIngestRequest):
    """Ingest text into vector memory with duplicate detection."""
    try:
        # Check rate limit
        if not check_rate_limit():
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        logger.info("Ingesting memory",
                   text_length=len(request.text),
                   tags=request.tags,
                   source=request.source)
        
        # Generate embedding
        try:
            embedding = embed_text(request.text)
        except Exception as e:
            logger.error("Embedding generation failed", error=str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate embedding: {str(e)}"
            )
        
        # Check for near duplicates
        try:
            from src.hivemind.clients.qdrant_store import near_duplicates
            
            duplicates = near_duplicates(embedding, k=5, threshold=0.985)
            
            if duplicates:
                # Duplicate found - update usage instead of inserting
                duplicate_id = str(duplicates[0].id)
                
                from src.hivemind.clients.qdrant_store import update_usage
                update_usage([duplicate_id], quality_bump=0.02)
                
                logger.info("Duplicate detected, updated existing memory",
                           duplicate_id=duplicate_id,
                           similarity=duplicates[0].score)
                
                return MemoryIngestResponse(
                    id=duplicate_id,
                    status="duplicate_updated",
                    embedding_dimension=len(embedding),
                    duplicate_skipped=True
                )
        except Exception as e:
            logger.warning("Duplicate check failed", error=str(e))
            # Continue with ingestion if duplicate check fails
        
        # Prepare payload
        payload = {
            "text": request.text,
            "tags": request.tags,
            "source": request.source,
            "quality": request.quality,
            "metadata": request.metadata,
        }
        
        # Ingest into Qdrant
        success = upsert_embeddings([embedding], [payload])
        
        if success:
            # Generate ID for response (would be handled by Qdrant in real implementation)
            memory_id = hashlib.sha256(request.text.encode()).hexdigest()[:16]
            
            return MemoryIngestResponse(
                id=memory_id,
                status="ingested",
                embedding_dimension=len(embedding),
                duplicate_skipped=False
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to store memory in vector database"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Memory ingestion failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}"
        )

@memory_router.post("/query", response_model=MemoryQueryResponse)
async def query_memory(request: MemoryQueryRequest):
    """Query vector memory for semantic matches."""
    start_time = time.time()
    
    try:
        # Validate request
        if not request.query and not request.vector:
            raise HTTPException(
                status_code=400,
                detail="Must provide either 'query' text or 'vector'"
            )
        
        # Check rate limit
        if not check_rate_limit():
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Generate query vector if needed
        if request.vector:
            query_vector = request.vector
            query_text = "vector_query"
        else:
            query_text = request.query
            try:
                query_vector = embed_text(query_text)
            except Exception as e:
                logger.error("Query embedding generation failed", error=str(e))
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate query embedding: {str(e)}"
                )
        
        # Check cache first
        filters = {
            "include_deleted": request.include_deleted,
            "tags_filter": request.tags_filter,
            "source_filter": request.source_filter,
            "min_score": request.min_score
        }
        
        query_hash = _generate_query_hash(query_text, request.limit, filters)
        cached_results = get_cached_query(query_hash)
        
        if cached_results is not None:
            query_time = (time.time() - start_time) * 1000
            
            return MemoryQueryResponse(
                results=cached_results,
                query_time_ms=query_time,
                cached=True,
                total_results=len(cached_results)
            )
        
        # Build search filter
        search_filter = _build_qdrant_filter(
            include_deleted=request.include_deleted,
            tags_filter=request.tags_filter,
            source_filter=request.source_filter
        )
        
        # Perform vector search
        try:
            search_results = semantic_search(
                query_vector=query_vector,
                limit=request.limit,
                where=search_filter,
                score_threshold=request.min_score if request.min_score > 0 else None
            )
        except Exception as e:
            logger.error("Vector search failed", error=str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Vector search failed: {str(e)}"
            )
        
        # Format results
        formatted_results = []
        point_ids = []
        
        for hit in search_results:
            result = {
                "id": str(hit.id),
                "score": hit.score,
                "text": hit.payload.get("text", ""),
                "tags": hit.payload.get("tags", []),
                "source": hit.payload.get("source", ""),
                "quality": hit.payload.get("quality", 0.0),
                "uses": hit.payload.get("uses", 0),
                "created_at": hit.payload.get("created_at"),
                "metadata": hit.payload.get("metadata", {})
            }
            formatted_results.append(result)
            point_ids.append(str(hit.id))
        
        # Update usage statistics
        if point_ids:
            try:
                from src.hivemind.clients.qdrant_store import update_usage
                update_usage(point_ids, quality_bump=0.01)
            except Exception as e:
                logger.warning("Failed to update usage stats", error=str(e))
        
        # Cache results
        try:
            cache_query_result(query_hash, formatted_results, ttl_sec=1800)
        except Exception as e:
            logger.warning("Failed to cache query results", error=str(e))
        
        query_time = (time.time() - start_time) * 1000
        
        logger.info("Memory query completed",
                   query_length=len(query_text),
                   results_count=len(formatted_results),
                   query_time_ms=query_time)
        
        return MemoryQueryResponse(
            results=formatted_results,
            query_time_ms=query_time,
            cached=False,
            total_results=len(formatted_results)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Memory query failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )

@memory_router.post("/ingest/batch")
async def ingest_memory_batch(requests: List[MemoryIngestRequest]):
    """Ingest multiple memories in batch."""
    try:
        if len(requests) > 100:
            raise HTTPException(
                status_code=400,
                detail="Maximum 100 items per batch"
            )
        
        logger.info("Batch memory ingestion started", batch_size=len(requests))
        
        # Extract texts for batch embedding
        texts = [req.text for req in requests]
        
        # Generate embeddings in batch
        try:
            embeddings = embed_batch(texts, batch_size=50)
        except Exception as e:
            logger.error("Batch embedding failed", error=str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Batch embedding failed: {str(e)}"
            )
        
        # Prepare payloads
        payloads = []
        for req in requests:
            payload = {
                "text": req.text,
                "tags": req.tags,
                "source": req.source,
                "quality": req.quality,
                "metadata": req.metadata,
            }
            payloads.append(payload)
        
        # Batch upsert
        success = upsert_embeddings(embeddings, payloads)
        
        if success:
            return {
                "status": "batch_ingested",
                "count": len(requests),
                "embedding_dimension": len(embeddings[0]) if embeddings else 0
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to store batch memories"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Batch ingestion failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Batch ingestion failed: {str(e)}"
        )

@memory_router.post("/gc/run", response_model=GCResponse)
async def run_garbage_collection(
    request: GCRequest,
    background_tasks: BackgroundTasks
):
    """Run memory garbage collection."""
    try:
        logger.info("Garbage collection requested", 
                   force=request.force,
                   dry_run=request.dry_run)
        
        if request.dry_run:
            # For dry run, just analyze what would be deleted
            from src.hivemind.maintenance.memory_gc import (
                find_expired_memories,
                find_low_value_memories,
                find_soft_to_hard_candidates
            )
            
            expired_ids = find_expired_memories()
            low_value_ids = find_low_value_memories() 
            hard_delete_ids = find_soft_to_hard_candidates()
            
            return GCResponse(
                status="dry_run_completed",
                stats={
                    "would_soft_delete_expired": len(expired_ids),
                    "would_soft_delete_low_value": len(low_value_ids),
                    "would_hard_delete": len(hard_delete_ids),
                    "dry_run": True
                },
                duration_seconds=0.0
            )
        else:
            # Run actual GC in background
            background_tasks.add_task(run_gc)
            
            return GCResponse(
                status="gc_started",
                stats={"message": "Garbage collection started in background"},
                duration_seconds=0.0
            )
        
    except Exception as e:
        logger.error("Garbage collection request failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"GC failed: {str(e)}"
        )

@memory_router.get("/stats", response_model=MemoryStatsResponse)
async def get_memory_stats():
    """Get comprehensive memory system statistics."""
    try:
        # Get collection stats
        collection_stats = get_collection_stats()
        
        # Get cache stats
        cache_stats = {
            "redis": redis_health(),
            "cache_info": {}
        }
        
        # Get provider status
        provider_status = get_provider_status()
        
        return MemoryStatsResponse(
            collection_stats=collection_stats,
            cache_stats=cache_stats,
            provider_status=provider_status,
            timestamp=time.time()
        )
        
    except Exception as e:
        logger.error("Failed to get memory stats", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Stats retrieval failed: {str(e)}"
        )

@memory_router.get("/health")
async def memory_health_check():
    """Health check for memory system components."""
    try:
        # Check Qdrant
        qdrant_status = qdrant_health()
        
        # Check Redis  
        redis_status = redis_health()
        
        # Check embedding system
        embedding_status = {}
        try:
            from src.hivemind.embedding.embedder import health_check as embedding_health
            embedding_status = embedding_health()
        except Exception as e:
            embedding_status = {"status": "error", "error": str(e)}
        
        # Overall health assessment
        all_healthy = (
            qdrant_status.get("status") == "healthy" and
            redis_status.get("status") == "healthy" and
            embedding_status.get("status") == "healthy"
        )
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "components": {
                "qdrant": qdrant_status,
                "redis": redis_status,
                "embeddings": embedding_status
            },
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error("Memory health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }

@memory_router.post("/quality/update")
async def update_memory_quality(background_tasks: BackgroundTasks):
    """Trigger quality score updates for stored memories."""
    try:
        background_tasks.add_task(update_quality_scores, 1000)
        
        return {
            "status": "quality_update_started",
            "message": "Quality score update started in background"
        }
        
    except Exception as e:
        logger.error("Quality update request failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Quality update failed: {str(e)}"
        )

@memory_router.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str, hard_delete_flag: bool = False):
    """Delete a specific memory."""
    try:
        if hard_delete_flag:
            success = hard_delete([memory_id])
            action = "hard_deleted"
        else:
            success = soft_delete([memory_id])
            action = "soft_deleted"
        
        if success:
            logger.info("Memory deleted",
                       memory_id=memory_id,
                       action=action)
            
            return {
                "status": action,
                "memory_id": memory_id
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete memory {memory_id}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Memory deletion failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Deletion failed: {str(e)}"
        )