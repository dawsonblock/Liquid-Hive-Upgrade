"""Memory garbage collection with quality-based pruning."""

import os
import time
import math
from typing import List, Dict, Any, Tuple, Optional
from qdrant_client.http import models as qm
import structlog

from src.hivemind.clients.qdrant_store import (
from src.logging_config import get_logger
    _client, COLL, soft_delete, hard_delete, get_collection_stats
)

logger = structlog.get_logger(__name__)

# Configuration from environment
TTL_DAYS = int(os.getenv("MEMORY_TTL_DAYS", "90"))
MIN_QUALITY = float(os.getenv("MIN_QUALITY_SCORE", "0.42"))
GRACE_DAYS = int(os.getenv("SOFT_DELETE_GRACE_DAYS", "14"))
MAX_COLLECTION_SIZE = int(os.getenv("MAX_COLLECTION_SIZE", "5000000"))
DUP_THRESHOLD = float(os.getenv("DUPLICATE_COSINE_THRESHOLD", "0.985"))

def _now() -> int:
    """Get current timestamp."""
    return int(time.time())

def _filter(conditions: List[qm.Condition]) -> qm.Filter:
    """Create filter from conditions."""
    return qm.Filter(must=conditions)

def _scroll_ids(q, filter_condition: qm.Filter, limit: int = 2048) -> List[str]:
    """Scroll through collection and return matching point IDs."""
    ids = []
    offset = None
    
    try:
        while True:
            points, next_offset = q.scroll(
                collection_name=COLL,
                scroll_filter=filter_condition,
                with_payload=False,
                limit=limit,
                offset=offset
            )
            
            if not points:
                break
            
            ids.extend([str(point.id) for point in points])
            offset = next_offset
            
            if offset is None:
                break
            
            # Safety check to prevent infinite loops
            if len(ids) > MAX_COLLECTION_SIZE:
                logger.warning("Scroll limit reached", ids_collected=len(ids))
                break
        
        return ids
        
    except Exception as e:
        logger.error("Scroll operation failed", error=str(e))
        return ids

def find_expired_memories() -> List[str]:
    """Find memories that have exceeded TTL."""
    try:
        cutoff = _now() - TTL_DAYS * 86400  # Convert days to seconds
        
        expired_filter = _filter([
            qm.FieldCondition(
                key="created_at", 
                range=qm.Range(lte=cutoff)
            ),
            qm.FieldCondition(
                key="deleted", 
                match=qm.MatchValue(value=False)
            )
        ])
        
        q = _client()
        expired_ids = _scroll_ids(q, expired_filter)
        
        logger.info("Expired memories found",
                   count=len(expired_ids),
                   cutoff_days_ago=TTL_DAYS)
        
        return expired_ids
        
    except Exception as e:
        logger.error("Failed to find expired memories", error=str(e))
        return []

def find_low_value_memories() -> List[str]:
    """Find memories with low quality and no usage."""
    try:
        low_value_filter = _filter([
            qm.FieldCondition(
                key="quality", 
                range=qm.Range(lt=MIN_QUALITY)
            ),
            qm.FieldCondition(
                key="uses", 
                range=qm.Range(lte=0)
            ),
            qm.FieldCondition(
                key="deleted", 
                match=qm.MatchValue(value=False)
            )
        ])
        
        q = _client()
        low_value_ids = _scroll_ids(q, low_value_filter)
        
        logger.info("Low value memories found",
                   count=len(low_value_ids),
                   min_quality=MIN_QUALITY)
        
        return low_value_ids
        
    except Exception as e:
        logger.error("Failed to find low value memories", error=str(e))
        return []

def find_soft_to_hard_candidates() -> List[str]:
    """Find soft-deleted memories ready for hard deletion."""
    try:
        cutoff = _now() - GRACE_DAYS * 86400
        
        grace_expired_filter = _filter([
            qm.FieldCondition(
                key="deleted", 
                match=qm.MatchValue(value=True)
            ),
            qm.FieldCondition(
                key="updated_at", 
                range=qm.Range(lte=cutoff)
            )
        ])
        
        q = _client()
        hard_delete_ids = _scroll_ids(q, grace_expired_filter)
        
        logger.info("Memories ready for hard deletion",
                   count=len(hard_delete_ids),
                   grace_days=GRACE_DAYS)
        
        return hard_delete_ids
        
    except Exception as e:
        logger.error("Failed to find hard deletion candidates", error=str(e))
        return []

def find_oversize_candidates() -> List[str]:
    """Find lowest quality memories if collection is oversized."""
    try:
        stats = get_collection_stats()
        current_size = stats.get("vectors_count", 0)
        
        if current_size <= MAX_COLLECTION_SIZE:
            return []
        
        # Calculate how many to remove
        excess_count = current_size - MAX_COLLECTION_SIZE
        
        # Get lowest quality, non-deleted memories
        q = _client()
        
        # Scroll through collection to find lowest quality items
        # Note: This is a simplified approach - in production, you'd want
        # a more efficient index-based approach
        low_quality_filter = _filter([
            qm.FieldCondition(
                key="deleted", 
                match=qm.MatchValue(value=False)
            )
        ])
        
        points, _ = q.scroll(
            collection_name=COLL,
            scroll_filter=low_quality_filter,
            with_payload=True,
            limit=excess_count * 2  # Get more than needed to sort by quality
        )
        
        # Sort by quality (ascending) and take the worst ones
        sorted_points = sorted(
            points, 
            key=lambda p: p.payload.get("quality", 0.0)
        )
        
        oversize_ids = [str(p.id) for p in sorted_points[:excess_count]]
        
        logger.info("Oversize cleanup candidates found",
                   current_size=current_size,
                   max_size=MAX_COLLECTION_SIZE,
                   excess=excess_count,
                   candidates=len(oversize_ids))
        
        return oversize_ids
        
    except Exception as e:
        logger.error("Failed to find oversize candidates", error=str(e))
        return []

def calculate_quality_score(
    created_at: int,
    last_access: int,
    uses: int,
    feedback_score: Optional[float] = None
) -> float:
    """Calculate dynamic quality score based on usage patterns.
    
    Args:
        created_at: Creation timestamp
        last_access: Last access timestamp
        uses: Number of times accessed
        feedback_score: Optional external feedback score (0-1)
        
    Returns:
        Quality score between 0.0 and 1.0
    """
    try:
        now = _now()
        
        # Recency factor (exponential decay)
        age_days = (now - last_access) / 86400
        w_recency = math.exp(-age_days / 45)  # Half-life of ~31 days
        
        # Usage factor (logarithmic scaling)
        w_use = math.log1p(uses) / math.log1p(100)  # Normalized to 100 uses
        
        # Feedback factor (external rating)
        w_feedback = feedback_score if feedback_score is not None else 0.5
        
        # Combined quality score
        quality = 0.6 * w_recency + 0.3 * w_use + 0.1 * w_feedback
        
        # Clamp to [0, 1]
        quality = max(0.0, min(1.0, quality))
        
        logger.debug("Quality calculated",
                    age_days=age_days,
                    uses=uses,
                    w_recency=w_recency,
                    w_use=w_use,
                    w_feedback=w_feedback,
                    final_quality=quality)
        
        return quality
        
    except Exception as e:
        logger.error("Quality calculation failed", error=str(e))
        return 0.0  # Conservative fallback

def update_quality_scores(sample_size: int = 1000) -> int:
    """Update quality scores for a sample of memories.
    
    Args:
        sample_size: Number of memories to update per run
        
    Returns:
        Number of memories updated
    """
    try:
        q = _client()
        
        # Get a sample of active memories
        points, _ = q.scroll(
            collection_name=COLL,
            scroll_filter=_filter([
                qm.FieldCondition(
                    key="deleted", 
                    match=qm.MatchValue(value=False)
                )
            ]),
            with_payload=True,
            limit=sample_size
        )
        
        updated_count = 0
        
        for point in points:
            try:
                payload = point.payload
                
                # Calculate new quality score
                new_quality = calculate_quality_score(
                    created_at=payload.get("created_at", _now()),
                    last_access=payload.get("last_access", _now()),
                    uses=payload.get("uses", 0),
                    feedback_score=payload.get("feedback_score")
                )
                
                # Update quality if significantly different
                current_quality = payload.get("quality", 0.5)
                if abs(new_quality - current_quality) > 0.05:
                    q.set_payload(
                        collection_name=COLL,
                        payload={
                            "quality": new_quality,
                            "updated_at": _now()
                        },
                        points=[str(point.id)]
                    )
                    updated_count += 1
                    
            except Exception as e:
                logger.warning("Failed to update quality for point",
                             point_id=str(point.id),
                             error=str(e))
        
        logger.info("Quality scores updated",
                   sample_size=len(points),
                   updated_count=updated_count)
        
        return updated_count
        
    except Exception as e:
        logger.error("Quality update failed", error=str(e))
        return 0

def run_gc() -> Dict[str, Any]:
    """Run comprehensive garbage collection."""
    try:
        logger.info("Starting memory garbage collection",
                   ttl_days=TTL_DAYS,
                   min_quality=MIN_QUALITY,
                   grace_days=GRACE_DAYS,
                   max_size=MAX_COLLECTION_SIZE)
        
        start_time = time.time()
        gc_stats = {
            "start_time": start_time,
            "expired_soft_deleted": 0,
            "low_value_soft_deleted": 0,
            "oversize_soft_deleted": 0,
            "hard_deleted": 0,
            "quality_updates": 0,
            "errors": []
        }
        
        # Phase 1: Soft delete expired memories
        try:
            expired_ids = find_expired_memories()
            if expired_ids:
                if soft_delete(expired_ids):
                    gc_stats["expired_soft_deleted"] = len(expired_ids)
                    logger.info("Expired memories soft deleted", count=len(expired_ids))
        except Exception as e:
            gc_stats["errors"].append(f"Expired cleanup failed: {str(e)}")
        
        # Phase 2: Soft delete low-value memories
        try:
            low_value_ids = find_low_value_memories()
            if low_value_ids:
                if soft_delete(low_value_ids):
                    gc_stats["low_value_soft_deleted"] = len(low_value_ids)
                    logger.info("Low value memories soft deleted", count=len(low_value_ids))
        except Exception as e:
            gc_stats["errors"].append(f"Low value cleanup failed: {str(e)}")
        
        # Phase 3: Handle collection size limits
        try:
            oversize_ids = find_oversize_candidates()
            if oversize_ids:
                if soft_delete(oversize_ids):
                    gc_stats["oversize_soft_deleted"] = len(oversize_ids)
                    logger.info("Oversize memories soft deleted", count=len(oversize_ids))
        except Exception as e:
            gc_stats["errors"].append(f"Oversize cleanup failed: {str(e)}")
        
        # Phase 4: Hard delete grace period expired
        try:
            hard_delete_ids = find_soft_to_hard_candidates()
            if hard_delete_ids:
                if hard_delete(hard_delete_ids):
                    gc_stats["hard_deleted"] = len(hard_delete_ids)
                    logger.info("Memories hard deleted", count=len(hard_delete_ids))
        except Exception as e:
            gc_stats["errors"].append(f"Hard delete failed: {str(e)}")
        
        # Phase 5: Update quality scores for active memories
        try:
            quality_updates = update_quality_scores(sample_size=1000)
            gc_stats["quality_updates"] = quality_updates
        except Exception as e:
            gc_stats["errors"].append(f"Quality update failed: {str(e)}")
        
        # Final statistics
        end_time = time.time()
        gc_stats["end_time"] = end_time
        gc_stats["duration_seconds"] = end_time - start_time
        gc_stats["total_processed"] = (
            gc_stats["expired_soft_deleted"] +
            gc_stats["low_value_soft_deleted"] +
            gc_stats["oversize_soft_deleted"] +
            gc_stats["hard_deleted"]
        )
        
        # Get final collection stats
        try:
            collection_stats = get_collection_stats()
            gc_stats["final_collection_size"] = collection_stats.get("vectors_count", 0)
        except Exception as e:
            gc_stats["errors"].append(f"Final stats failed: {str(e)}")
        
        logger.info("Memory garbage collection completed",
                   duration=gc_stats["duration_seconds"],
                   total_processed=gc_stats["total_processed"],
                   errors=len(gc_stats["errors"]))
        
        return gc_stats
        
    except Exception as e:
        logger.error("Garbage collection failed", error=str(e))
        return {
            "error": str(e),
            "duration_seconds": 0,
            "total_processed": 0
        }

def find_duplicates(
    sample_size: int = 1000,
    similarity_threshold: float = None
) -> List[Tuple[str, str, float]]:
    """Find duplicate memories using vector similarity.
    
    Args:
        sample_size: Number of memories to check for duplicates
        similarity_threshold: Cosine similarity threshold for duplicates
        
    Returns:
        List of (id1, id2, similarity_score) tuples for duplicates
    """
    threshold = similarity_threshold or DUP_THRESHOLD
    duplicates = []
    
    try:
        q = _client()
        
        # Get a sample of active memories with vectors
        points, _ = q.scroll(
            collection_name=COLL,
            scroll_filter=_filter([
                qm.FieldCondition(
                    key="deleted", 
                    match=qm.MatchValue(value=False)
                )
            ]),
            with_payload=True,
            with_vectors=True,
            limit=sample_size
        )
        
        logger.info("Checking for duplicates", 
                   sample_size=len(points),
                   threshold=threshold)
        
        # Compare each point with others using vector similarity
        for i, point1 in enumerate(points):
            if i % 100 == 0:
                logger.debug("Duplicate check progress", 
                           checked=i, 
                           total=len(points))
            
            vector1 = point1.vector
            if vector1 is None:
                continue
            
            # Search for similar vectors
            similar_points = q.search(
                collection_name=COLL,
                query_vector=vector1,
                limit=10,
                query_filter=_filter([
                    qm.FieldCondition(
                        key="deleted", 
                        match=qm.MatchValue(value=False)
                    )
                ])
            )
            
            for similar in similar_points:
                # Skip self-match
                if str(similar.id) == str(point1.id):
                    continue
                
                # Check if similarity exceeds threshold
                if similar.score >= threshold:
                    # Check if this duplicate pair was already found
                    duplicate_pair = tuple(sorted([str(point1.id), str(similar.id)]))
                    
                    if not any(dp[:2] == duplicate_pair for dp in duplicates):
                        duplicates.append((
                            str(point1.id),
                            str(similar.id),
                            similar.score
                        ))
        
        logger.info("Duplicate detection completed",
                   sample_checked=len(points),
                   duplicates_found=len(duplicates))
        
        return duplicates
        
    except Exception as e:
        logger.error("Duplicate detection failed", error=str(e))
        return []

def remove_duplicates(max_duplicates: int = 100) -> int:
    """Remove duplicate memories, keeping the higher quality version.
    
    Args:
        max_duplicates: Maximum number of duplicates to process
        
    Returns:
        Number of duplicates removed
    """
    try:
        duplicates = find_duplicates(sample_size=1000)
        
        if not duplicates:
            return 0
        
        # Limit processing to prevent overwhelming the system
        duplicates_to_process = duplicates[:max_duplicates]
        
        removed_count = 0
        q = _client()
        
        for id1, id2, similarity in duplicates_to_process:
            try:
                # Get both points with payload to compare quality
                points = q.retrieve(
                    collection_name=COLL,
                    ids=[id1, id2],
                    with_payload=True
                )
                
                if len(points) != 2:
                    continue
                
                point1, point2 = points[0], points[1]
                
                # Compare quality scores
                quality1 = point1.payload.get("quality", 0.0)
                quality2 = point2.payload.get("quality", 0.0)
                
                # Remove the lower quality one
                if quality1 < quality2:
                    soft_delete([id1])
                    removed_count += 1
                    logger.debug("Duplicate removed",
                               kept=id2,
                               removed=id1,
                               similarity=similarity)
                elif quality2 < quality1:
                    soft_delete([id2])
                    removed_count += 1
                    logger.debug("Duplicate removed",
                               kept=id1,
                               removed=id2,
                               similarity=similarity)
                else:
                    # Same quality, remove the newer one (keep older)
                    created1 = point1.payload.get("created_at", 0)
                    created2 = point2.payload.get("created_at", 0)
                    
                    if created1 > created2:
                        soft_delete([id1])
                        removed_count += 1
                    else:
                        soft_delete([id2])
                        removed_count += 1
                
            except Exception as e:
                logger.warning("Failed to process duplicate pair",
                             id1=id1,
                             id2=id2,
                             error=str(e))
        
        logger.info("Duplicate removal completed",
                   processed=len(duplicates_to_process),
                   removed=removed_count)
        
        return removed_count
        
    except Exception as e:
        logger.error("Duplicate removal failed", error=str(e))
        return 0

if __name__ == "__main__":
    # Run garbage collection when called directly
    result = run_gc()
    logger.info(f"Garbage collection completed: {result}")