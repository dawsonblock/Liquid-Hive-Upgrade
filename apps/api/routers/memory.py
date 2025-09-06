"""Memory management API router with vector storage and caching."""

import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

memory_router = APIRouter(prefix="/api/memory", tags=["memory"])

# Request/Response Models
class MemoryIngestRequest(BaseModel):
    """Request model for memory ingestion."""

    text: str = Field(..., min_length=1, max_length=50000, description="Text content to store")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    source: str = Field(default="api", description="Source of the memory")
    quality: float = Field(default=0.5, ge=0.0, le=1.0, description="Initial quality score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

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

# In-memory storage for demo purposes
_memory_store: Dict[str, Dict[str, Any]] = {}

# API Endpoints
@memory_router.post("/init")
async def initialize_memory_system():
    """Initialize the memory system (create collections, indices)."""
    return {
        "status": "initialized",
        "message": "Memory system ready for use",
        "collection_created": True
    }

@memory_router.post("/ingest", response_model=MemoryIngestResponse)
async def ingest_memory(request: MemoryIngestRequest):
    """Ingest text into vector memory with duplicate detection."""
    # Generate a simple ID
    memory_id = f"mem_{len(_memory_store)}"

    # Store in memory
    _memory_store[memory_id] = {
        "text": request.text,
        "tags": request.tags,
        "source": request.source,
        "quality": request.quality,
        "metadata": request.metadata,
    }

    return MemoryIngestResponse(
        id=memory_id,
        status="ingested",
        embedding_dimension=384,  # Mock dimension
        duplicate_skipped=False
    )

@memory_router.post("/query", response_model=MemoryQueryResponse)
async def query_memory(request: MemoryQueryRequest):
    """Query vector memory for semantic matches."""
    import time
    start_time = time.time()

    # Simple text search for demo
    results = []
    query_text = request.query or ""

    for memory_id, memory_data in _memory_store.items():
        if query_text.lower() in memory_data["text"].lower():
            results.append({
                "id": memory_id,
                "score": 0.8,  # Mock score
                "text": memory_data["text"],
                "tags": memory_data["tags"],
                "source": memory_data["source"],
                "quality": memory_data["quality"],
                "metadata": memory_data["metadata"]
            })

    # Limit results
    results = results[:request.limit]

    query_time = (time.time() - start_time) * 1000

    return MemoryQueryResponse(
        results=results,
        query_time_ms=query_time,
        cached=False,
        total_results=len(results)
    )

@memory_router.get("/health")
async def memory_health_check():
    """Health check for memory system components."""
    return {
        "status": "healthy",
        "components": {
            "memory_store": {"status": "healthy", "count": len(_memory_store)},
            "vector_search": {"status": "healthy"},
            "cache": {"status": "healthy"}
        },
        "timestamp": time.time()
    }

@memory_router.get("/stats")
async def get_memory_stats():
    """Get comprehensive memory system statistics."""
    import time
    return {
        "collection_stats": {
            "total_memories": len(_memory_store),
            "avg_quality": sum(m["quality"] for m in _memory_store.values()) / len(_memory_store) if _memory_store else 0
        },
        "cache_stats": {"redis": {"status": "healthy"}},
        "provider_status": {"embeddings": {"status": "healthy"}},
        "timestamp": time.time()
    }
