"""Feedback collection and processing implementation."""

import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import structlog

from services.shared.schemas import FeedbackEvent, EventType
from services.event_bus.bus import create_event_envelope, get_default_event_bus

logger = structlog.get_logger(__name__)


class FeedbackCollector:
    """Collects, validates, and routes feedback events to the event bus."""
    
    def __init__(self):
        """Initialize the feedback collector."""
        self.start_time = time.time()
        
        # Statistics tracking
        self.stats = {
            "total_collected": 0,
            "collected_by_type": defaultdict(int),
            "collected_by_agent": defaultdict(int),
            "failed_collections": 0,
            "validation_errors": 0
        }
        
        # Recent events for metrics calculation (keep last 24 hours)
        self.recent_events = deque(maxlen=10000)
        
        logger.info("FeedbackCollector initialized")
    
    async def collect_feedback(self, feedback_event: FeedbackEvent) -> bool:
        """Collect and process a feedback event.
        
        Args:
            feedback_event: The feedback event to collect
            
        Returns:
            True if successfully collected and published
        """
        try:
            # Validate the event
            if not self._validate_event(feedback_event):
                self.stats["validation_errors"] += 1
                return False
            
            # Get event bus
            event_bus = await get_default_event_bus()
            
            # Create event envelope
            envelope = await create_event_envelope(
                event_type=feedback_event.event_type.value,
                payload=feedback_event.dict(),
                source_service="feedback_api",
                target_services=["oracle_api", "analytics"],
                correlation_id=feedback_event.session_id
            )
            
            # Publish to event bus
            success = await event_bus.publish(envelope)
            
            if success:
                # Update statistics
                self.stats["total_collected"] += 1
                self.stats["collected_by_type"][feedback_event.event_type.value] += 1
                self.stats["collected_by_agent"][feedback_event.agent_id] += 1
                
                # Store for recent metrics
                self.recent_events.append({
                    "event": feedback_event,
                    "collected_at": datetime.utcnow()
                })
                
                logger.debug(
                    "Feedback event collected successfully",
                    event_id=feedback_event.event_id,
                    event_type=feedback_event.event_type.value,
                    agent_id=feedback_event.agent_id
                )
                
                return True
            else:
                self.stats["failed_collections"] += 1
                logger.error(
                    "Failed to publish feedback event to bus",
                    event_id=feedback_event.event_id
                )
                return False
                
        except Exception as e:
            self.stats["failed_collections"] += 1
            logger.error(
                "Error collecting feedback event",
                error=str(e),
                event_id=feedback_event.event_id
            )
            return False
    
    def _validate_event(self, event: FeedbackEvent) -> bool:
        """Validate a feedback event before processing.
        
        Args:
            event: The feedback event to validate
            
        Returns:
            True if event is valid
        """
        try:
            # Basic required field validation
            if not event.event_id:
                logger.warning("Event missing event_id")
                return False
            
            if not event.agent_id:
                logger.warning("Event missing agent_id", event_id=event.event_id)
                return False
            
            if not event.session_id:
                logger.warning("Event missing session_id", event_id=event.event_id)
                return False
            
            # Event type validation
            if not isinstance(event.event_type, EventType):
                logger.warning("Invalid event_type", event_id=event.event_id, event_type=event.event_type)
                return False
            
            # Content validation - must have either explicit or implicit feedback
            if not event.explicit and not event.implicit:
                logger.warning(
                    "Event has neither explicit nor implicit feedback",
                    event_id=event.event_id
                )
                return False
            
            # Validate implicit feedback values are numeric
            for key, value in event.implicit.items():
                if not isinstance(value, (int, float)):
                    logger.warning(
                        "Invalid implicit feedback value",
                        event_id=event.event_id,
                        key=key,
                        value=value
                    )
                    return False
            
            return True
            
        except Exception as e:
            logger.error("Error validating feedback event", error=str(e), event_id=event.event_id)
            return False
    
    async def get_metrics(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get aggregated feedback metrics for the specified time window.
        
        Args:
            time_window_hours: Time window for metrics calculation
            
        Returns:
            Dictionary containing various metrics
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
            
            # Filter events within time window
            recent_events = [
                entry for entry in self.recent_events
                if entry["collected_at"] >= cutoff_time
            ]
            
            if not recent_events:
                return {
                    "total_events": 0,
                    "events_by_type": {},
                    "events_by_agent": {},
                    "avg_rating": None,
                    "success_rate": None
                }
            
            # Calculate metrics
            events_by_type = defaultdict(int)
            events_by_agent = defaultdict(int)
            ratings = []
            success_rates = []
            
            for entry in recent_events:
                event = entry["event"]
                
                # Count by type and agent
                events_by_type[event.event_type.value] += 1
                events_by_agent[event.agent_id] += 1
                
                # Extract ratings if present
                if event.explicit.get("rating"):
                    ratings.append(float(event.explicit["rating"]))
                
                # Extract success rates if present
                if event.implicit.get("success_rate"):
                    success_rates.append(float(event.implicit["success_rate"]))
            
            # Calculate averages
            avg_rating = sum(ratings) / len(ratings) if ratings else None
            avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else None
            
            return {
                "total_events": len(recent_events),
                "events_by_type": dict(events_by_type),
                "events_by_agent": dict(events_by_agent),
                "avg_rating": avg_rating,
                "success_rate": avg_success_rate,
                "time_window_hours": time_window_hours,
                "oldest_event_age_hours": self._get_oldest_event_age_hours(recent_events),
                "newest_event_age_minutes": self._get_newest_event_age_minutes(recent_events)
            }
            
        except Exception as e:
            logger.error("Error calculating feedback metrics", error=str(e))
            return {
                "total_events": 0,
                "events_by_type": {},
                "events_by_agent": {},
                "error": str(e)
            }
    
    def _get_oldest_event_age_hours(self, events: List[Dict]) -> Optional[float]:
        """Get age of oldest event in hours."""
        if not events:
            return None
        
        oldest_time = min(entry["collected_at"] for entry in events)
        age_delta = datetime.utcnow() - oldest_time
        return age_delta.total_seconds() / 3600
    
    def _get_newest_event_age_minutes(self, events: List[Dict]) -> Optional[float]:
        """Get age of newest event in minutes."""
        if not events:
            return None
        
        newest_time = max(entry["collected_at"] for entry in events)
        age_delta = datetime.utcnow() - newest_time
        return age_delta.total_seconds() / 60
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current collector status and health information.
        
        Returns:
            Dictionary with status information
        """
        try:
            # Get event bus stats
            event_bus = await get_default_event_bus()
            bus_stats = await event_bus.get_stats()
            
            uptime_seconds = time.time() - self.start_time
            
            return {
                "status": "healthy",
                "uptime_seconds": uptime_seconds,
                "uptime_hours": round(uptime_seconds / 3600, 2),
                "collection_stats": dict(self.stats),
                "recent_events_count": len(self.recent_events),
                "event_bus_connected": True,
                "event_bus_stats": {
                    "events_published": bus_stats.get("events_published", 0),
                    "events_delivered": bus_stats.get("events_delivered", 0),
                    "active_subscriptions": bus_stats.get("active_subscriptions", 0)
                },
                "memory_usage": {
                    "recent_events_mb": self._estimate_recent_events_memory_mb(),
                    "bus_memory_mb": bus_stats.get("memory_usage_estimate_mb", 0)
                }
            }
            
        except Exception as e:
            logger.error("Error getting collector status", error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "uptime_seconds": time.time() - self.start_time
            }
    
    def _estimate_recent_events_memory_mb(self) -> float:
        """Estimate memory usage of recent events in MB."""
        # Rough estimation: ~1KB per event entry
        estimated_bytes = len(self.recent_events) * 1024
        return round(estimated_bytes / (1024 * 1024), 2)
    
    async def clear_old_events(self, max_age_hours: int = 24):
        """Clear events older than specified age to manage memory.
        
        Args:
            max_age_hours: Maximum age of events to keep
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            # Count events before cleanup
            initial_count = len(self.recent_events)
            
            # Filter out old events
            self.recent_events = deque(
                (entry for entry in self.recent_events if entry["collected_at"] >= cutoff_time),
                maxlen=self.recent_events.maxlen
            )
            
            cleaned_count = initial_count - len(self.recent_events)
            
            if cleaned_count > 0:
                logger.info(
                    "Cleaned up old feedback events",
                    removed_count=cleaned_count,
                    remaining_count=len(self.recent_events),
                    max_age_hours=max_age_hours
                )
            
        except Exception as e:
            logger.error("Error cleaning up old events", error=str(e))


# Global collector instance
_collector: Optional[FeedbackCollector] = None


def get_feedback_collector() -> FeedbackCollector:
    """Get the global feedback collector instance.
    
    Returns:
        FeedbackCollector instance
    """
    global _collector
    
    if _collector is None:
        _collector = FeedbackCollector()
    
    return _collector