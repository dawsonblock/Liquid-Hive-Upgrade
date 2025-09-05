"""Prometheus metrics for Liquid Hive memory system."""

import os
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import structlog

logger = structlog.get_logger(__name__)

# Metrics namespace
NAMESPACE = os.getenv("METRICS_NS", "hivemind_memory")

# Memory operation metrics
memory_ingest_total = Counter(
    f"{NAMESPACE}_ingest_total",
    "Total memory ingestion operations",
    ["status", "provider", "source"]
)

memory_query_total = Counter(
    f"{NAMESPACE}_query_total", 
    "Total memory query operations",
    ["status", "cached"]
)

memory_soft_deleted_total = Counter(
    f"{NAMESPACE}_soft_deleted_total",
    "Total soft deleted memories",
    ["reason"]
)

memory_hard_deleted_total = Counter(
    f"{NAMESPACE}_hard_deleted_total",
    "Total hard deleted memories"
)

memory_duplicate_skips_total = Counter(
    f"{NAMESPACE}_dedupe_skips_total",
    "Total duplicate ingestion attempts skipped"
)

# Current state metrics
memory_collection_size = Gauge(
    f"{NAMESPACE}_collection_size",
    "Current number of vectors in collection"
)

memory_cache_size = Gauge(
    f"{NAMESPACE}_cache_size", 
    "Current number of cached queries"
)

memory_avg_quality = Gauge(
    f"{NAMESPACE}_avg_quality",
    "Average quality score of memories"
)

# Performance metrics
embedding_generation_duration = Histogram(
    f"{NAMESPACE}_embedding_duration_seconds",
    "Time spent generating embeddings",
    ["provider"]
)

query_duration = Histogram(
    f"{NAMESPACE}_query_duration_seconds", 
    "Memory query duration",
    ["cached"]
)

gc_duration = Histogram(
    f"{NAMESPACE}_gc_duration_seconds",
    "Garbage collection duration"
)

# System health metrics
system_health = Gauge(
    f"{NAMESPACE}_system_health",
    "Overall memory system health (0=unhealthy, 1=healthy)",
    ["component"]
)

def record_ingest(status: str, provider: str = "unknown", source: str = "unknown"):
    """Record memory ingestion operation."""
    try:
        memory_ingest_total.labels(status=status, provider=provider, source=source).inc()
        logger.debug("Ingestion metric recorded", status=status, provider=provider)
    except Exception as e:
        logger.warning("Failed to record ingestion metric", error=str(e))

def record_query(status: str, cached: bool = False):
    """Record memory query operation."""
    try:
        memory_query_total.labels(status=status, cached=str(cached).lower()).inc()
        logger.debug("Query metric recorded", status=status, cached=cached)
    except Exception as e:
        logger.warning("Failed to record query metric", error=str(e))

def record_soft_delete(count: int, reason: str = "expired"):
    """Record soft deletion operations."""
    try:
        memory_soft_deleted_total.labels(reason=reason).inc(count)
        logger.debug("Soft delete metric recorded", count=count, reason=reason)
    except Exception as e:
        logger.warning("Failed to record soft delete metric", error=str(e))

def record_hard_delete(count: int):
    """Record hard deletion operations.""" 
    try:
        memory_hard_deleted_total.inc(count)
        logger.debug("Hard delete metric recorded", count=count)
    except Exception as e:
        logger.warning("Failed to record hard delete metric", error=str(e))

def record_duplicate_skip():
    """Record duplicate ingestion skip."""
    try:
        memory_duplicate_skips_total.inc()
        logger.debug("Duplicate skip metric recorded")
    except Exception as e:
        logger.warning("Failed to record duplicate skip metric", error=str(e))

def update_collection_size(size: int):
    """Update collection size gauge."""
    try:
        memory_collection_size.set(size)
        logger.debug("Collection size metric updated", size=size)
    except Exception as e:
        logger.warning("Failed to update collection size metric", error=str(e))

def update_avg_quality(quality: float):
    """Update average quality gauge."""
    try:
        memory_avg_quality.set(quality)
        logger.debug("Average quality metric updated", quality=quality)
    except Exception as e:
        logger.warning("Failed to update quality metric", error=str(e))

def record_embedding_duration(duration: float, provider: str):
    """Record embedding generation duration."""
    try:
        embedding_generation_duration.labels(provider=provider).observe(duration)
        logger.debug("Embedding duration recorded", duration=duration, provider=provider)
    except Exception as e:
        logger.warning("Failed to record embedding duration", error=str(e))

def record_query_duration(duration: float, cached: bool = False):
    """Record query duration."""
    try:
        query_duration.labels(cached=str(cached).lower()).observe(duration)
        logger.debug("Query duration recorded", duration=duration, cached=cached)
    except Exception as e:
        logger.warning("Failed to record query duration", error=str(e))

def record_gc_duration(duration: float):
    """Record garbage collection duration."""
    try:
        gc_duration.observe(duration)
        logger.debug("GC duration recorded", duration=duration)
    except Exception as e:
        logger.warning("Failed to record GC duration", error=str(e))

def update_system_health(component: str, healthy: bool):
    """Update system health status."""
    try:
        system_health.labels(component=component).set(1.0 if healthy else 0.0)
        logger.debug("System health updated", component=component, healthy=healthy)
    except Exception as e:
        logger.warning("Failed to update system health", error=str(e))

def get_metrics_response() -> Response:
    """Generate Prometheus metrics response."""
    try:
        metrics_output = generate_latest()
        return Response(content=metrics_output, media_type=CONTENT_TYPE_LATEST)
    except Exception as e:
        logger.error("Failed to generate metrics", error=str(e))
        return Response(content="# Metrics generation failed\n", media_type="text/plain")

# Health check functions
def check_and_update_component_health():
    """Check and update health status for all components."""
    try:
        # Check Qdrant health
        from src.hivemind.clients.qdrant_store import health_check as qdrant_health
        qdrant_status = qdrant_health()
        update_system_health("qdrant", qdrant_status.get("status") == "healthy")
        
        # Check Redis health  
        from src.hivemind.clients.redis_cache import health_check as redis_health
        redis_status = redis_health()
        update_system_health("redis", redis_status.get("status") == "healthy")
        
        # Check embedding system
        from src.hivemind.embedding.embedder import health_check as embedding_health
        embedding_status = embedding_health()
        update_system_health("embeddings", embedding_status.get("status") == "healthy")
        
        logger.debug("Component health updated")
        
    except Exception as e:
        logger.error("Failed to update component health", error=str(e))

def get_metrics_summary() -> dict:
    """Get summary of key metrics for debugging."""
    try:
        from prometheus_client import REGISTRY
        
        summary = {}
        
        for collector in REGISTRY._collector_to_names:
            for name in REGISTRY._collector_to_names[collector]:
                if name.startswith(NAMESPACE):
                    try:
                        metric = collector._value
                        summary[name] = metric if hasattr(collector, '_value') else 'N/A'
                    except Exception:
                        summary[name] = 'N/A'
        
        return summary
        
    except Exception as e:
        logger.error("Failed to get metrics summary", error=str(e))
        return {"error": str(e)}