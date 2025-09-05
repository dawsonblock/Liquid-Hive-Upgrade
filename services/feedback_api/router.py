"""FastAPI router for feedback collection endpoints."""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
import structlog

from services.shared.schemas import FeedbackEvent, EventType
from services.event_bus.bus import create_event_envelope
from .collector import FeedbackCollector, get_feedback_collector

logger = structlog.get_logger(__name__)

# Create router
feedback_router = APIRouter()


# Request/Response models
class CollectFeedbackRequest(BaseModel):
    """Request model for collecting feedback."""
    
    # Required fields
    agent_id: str = Field(..., description="ID of the agent being evaluated")
    session_id: str = Field(..., description="User session identifier")
    
    # Context information
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Contextual information about the interaction"
    )
    
    # Explicit feedback from user
    explicit: Dict[str, Any] = Field(
        default_factory=dict,
        description="Direct user feedback (ratings, corrections, etc.)"
    )
    
    # Implicit feedback from system observation
    implicit: Dict[str, float] = Field(
        default_factory=dict,
        description="Behavioral signals (success rates, response times, etc.)"
    )
    
    # Supporting artifacts
    artifacts: Dict[str, str] = Field(
        default_factory=dict,
        description="References to logs, outputs, or other supporting data"
    )
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for processing"
    )


class CollectFeedbackResponse(BaseModel):
    """Response model for feedback collection."""
    
    event_id: str = Field(..., description="Unique identifier for the collected event")
    status: str = Field(..., description="Collection status")
    message: str = Field(..., description="Human-readable status message")
    timestamp: datetime = Field(..., description="When the feedback was collected")


class BulkFeedbackRequest(BaseModel):
    """Request model for collecting multiple feedback events."""
    
    events: List[CollectFeedbackRequest] = Field(
        ..., 
        description="List of feedback events to collect",
        min_items=1,
        max_items=100  # Limit batch size
    )


class BulkFeedbackResponse(BaseModel):
    """Response model for bulk feedback collection."""
    
    collected_count: int = Field(..., description="Number of events successfully collected")
    failed_count: int = Field(..., description="Number of events that failed")
    event_ids: List[str] = Field(..., description="IDs of successfully collected events")
    errors: List[str] = Field(default_factory=list, description="Error messages for failures")


class FeedbackMetricsResponse(BaseModel):
    """Response model for feedback metrics."""
    
    total_events: int = Field(..., description="Total events collected")
    events_by_type: Dict[str, int] = Field(..., description="Events grouped by type")
    events_by_agent: Dict[str, int] = Field(..., description="Events grouped by agent")
    avg_rating: Optional[float] = Field(None, description="Average user rating if available")
    success_rate: Optional[float] = Field(None, description="Overall success rate if available")
    time_window_hours: int = Field(24, description="Time window for metrics")


@feedback_router.post("/collect", response_model=CollectFeedbackResponse)
async def collect_feedback(
    request: CollectFeedbackRequest,
    http_request: Request,
    collector: FeedbackCollector = Depends(get_feedback_collector)
) -> CollectFeedbackResponse:
    """Collect a single feedback event.
    
    This endpoint accepts feedback from users, systems, or automated processes
    and stores it for analysis by the Oracle system.
    """
    try:
        # Generate unique event ID
        event_id = f"feedback_{uuid.uuid4().hex}"
        
        # Create feedback event
        feedback_event = FeedbackEvent(
            event_id=event_id,
            event_type=EventType.FEEDBACK_EXPLICIT if request.explicit else EventType.FEEDBACK_IMPLICIT,
            agent_id=request.agent_id,
            session_id=request.session_id,
            timestamp=datetime.utcnow(),
            context=request.context,
            explicit=request.explicit,
            implicit=request.implicit,
            artifacts=request.artifacts,
            metadata=request.metadata
        )
        
        # Collect the feedback
        success = await collector.collect_feedback(feedback_event)
        
        if success:
            logger.info(
                "Feedback collected successfully",
                event_id=event_id,
                agent_id=request.agent_id,
                session_id=request.session_id,
                has_explicit=bool(request.explicit),
                has_implicit=bool(request.implicit)
            )
            
            return CollectFeedbackResponse(
                event_id=event_id,
                status="collected",
                message="Feedback successfully collected and queued for processing",
                timestamp=feedback_event.timestamp
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to collect feedback - internal error"
            )
    
    except Exception as e:
        logger.error("Error collecting feedback", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect feedback: {str(e)}"
        )


@feedback_router.post("/collect/bulk", response_model=BulkFeedbackResponse)
async def collect_bulk_feedback(
    request: BulkFeedbackRequest,
    http_request: Request,
    collector: FeedbackCollector = Depends(get_feedback_collector)
) -> BulkFeedbackResponse:
    """Collect multiple feedback events in a single request.
    
    Useful for batch processing or when network latency is a concern.
    Maximum 100 events per request.
    """
    collected_events = []
    failed_events = []
    errors = []
    
    try:
        for event_request in request.events:
            try:
                # Generate unique event ID
                event_id = f"feedback_{uuid.uuid4().hex}"
                
                # Create feedback event
                feedback_event = FeedbackEvent(
                    event_id=event_id,
                    event_type=EventType.FEEDBACK_EXPLICIT if event_request.explicit else EventType.FEEDBACK_IMPLICIT,
                    agent_id=event_request.agent_id,
                    session_id=event_request.session_id,
                    timestamp=datetime.utcnow(),
                    context=event_request.context,
                    explicit=event_request.explicit,
                    implicit=event_request.implicit,
                    artifacts=event_request.artifacts,
                    metadata=event_request.metadata
                )
                
                # Attempt to collect feedback
                success = await collector.collect_feedback(feedback_event)
                
                if success:
                    collected_events.append(event_id)
                else:
                    failed_events.append(event_id)
                    errors.append(f"Failed to collect event for agent {event_request.agent_id}")
            
            except Exception as e:
                failed_events.append(f"unknown_{len(failed_events)}")
                errors.append(f"Error processing event: {str(e)}")
        
        logger.info(
            "Bulk feedback collection completed",
            total_events=len(request.events),
            collected=len(collected_events),
            failed=len(failed_events)
        )
        
        return BulkFeedbackResponse(
            collected_count=len(collected_events),
            failed_count=len(failed_events),
            event_ids=collected_events,
            errors=errors
        )
    
    except Exception as e:
        logger.error("Error in bulk feedback collection", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Bulk collection failed: {str(e)}"
        )


@feedback_router.get("/metrics", response_model=FeedbackMetricsResponse)
async def get_feedback_metrics(
    hours: int = 24,
    collector: FeedbackCollector = Depends(get_feedback_collector)
) -> FeedbackMetricsResponse:
    """Get aggregated feedback metrics for monitoring and dashboards.
    
    Args:
        hours: Time window for metrics calculation (default: 24 hours)
    """
    try:
        metrics = await collector.get_metrics(time_window_hours=hours)
        
        return FeedbackMetricsResponse(
            total_events=metrics.get("total_events", 0),
            events_by_type=metrics.get("events_by_type", {}),
            events_by_agent=metrics.get("events_by_agent", {}),
            avg_rating=metrics.get("avg_rating"),
            success_rate=metrics.get("success_rate"),
            time_window_hours=hours
        )
    
    except Exception as e:
        logger.error("Error retrieving feedback metrics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve metrics: {str(e)}"
        )


@feedback_router.post("/system/metric")
async def collect_system_metric(
    metric_name: str,
    metric_value: float,
    component: str,
    unit: str = "count",
    tags: Dict[str, str] = None,
    collector: FeedbackCollector = Depends(get_feedback_collector)
):
    """Collect a system performance metric.
    
    This endpoint is used by system components to report performance metrics
    that can be used for optimization decisions.
    """
    try:
        # Create system metric event
        event_id = f"metric_{uuid.uuid4().hex}"
        
        metric_data = {
            "metric_name": metric_name,
            "value": metric_value,
            "unit": unit,
            "component": component,
            "tags": tags or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        feedback_event = FeedbackEvent(
            event_id=event_id,
            event_type=EventType.SYSTEM_METRIC,
            agent_id=component,  # Use component as agent_id for system metrics
            session_id="system",
            context=metric_data,
            implicit={"value": metric_value}
        )
        
        success = await collector.collect_feedback(feedback_event)
        
        if success:
            return {
                "event_id": event_id,
                "status": "collected",
                "message": f"System metric {metric_name} collected successfully"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to collect system metric"
            )
    
    except Exception as e:
        logger.error("Error collecting system metric", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect system metric: {str(e)}"
        )


@feedback_router.get("/status")
async def get_collector_status(
    collector: FeedbackCollector = Depends(get_feedback_collector)
):
    """Get the current status of the feedback collector."""
    try:
        status = await collector.get_status()
        return status
    except Exception as e:
        logger.error("Error retrieving collector status", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve status: {str(e)}"
        )