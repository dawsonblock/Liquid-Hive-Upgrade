"""Core Event Bus implementation with multiple backend support."""

import asyncio
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass
import structlog

from services.shared.schemas import EventEnvelope, EventBusConfig

logger = structlog.get_logger(__name__)


@dataclass
class EventSubscription:
    """Subscription information for event consumers."""
    subscriber_id: str
    event_types: Set[str]  # Empty set means subscribe to all events
    callback: Optional[Callable[[EventEnvelope], None]] = None
    max_queue_size: int = 1000
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class EventBus(ABC):
    """Abstract base class for event bus implementations."""
    
    @abstractmethod
    async def publish(self, event: EventEnvelope) -> bool:
        """Publish an event to the bus."""
        pass
    
    @abstractmethod
    async def subscribe(self, subscription: EventSubscription) -> str:
        """Subscribe to events. Returns subscription ID."""
        pass
    
    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events."""
        pass
    
    @abstractmethod
    async def get_events(self, subscriber_id: str, limit: int = 100) -> List[EventEnvelope]:
        """Get pending events for a subscriber."""
        pass
    
    @abstractmethod
    async def acknowledge_event(self, event_id: str, subscriber_id: str) -> bool:
        """Acknowledge successful processing of an event."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get bus statistics."""
        pass


class InMemoryEventBus(EventBus):
    """High-performance in-memory event bus implementation.
    
    Features:
    - Fast publish/subscribe with O(1) operations
    - Event filtering by type
    - Automatic cleanup of old events
    - Per-subscriber event queues
    - Dead letter queue for failed events
    - Statistics and monitoring
    """
    
    def __init__(self, config: Optional[EventBusConfig] = None):
        """Initialize the in-memory event bus.
        
        Args:
            config: Configuration for the event bus
        """
        self.config = config or EventBusConfig()
        
        # Core storage
        self._events: Dict[str, EventEnvelope] = {}  # event_id -> event
        self._subscriber_queues: Dict[str, deque] = {}  # subscriber_id -> event_ids
        self._subscriptions: Dict[str, EventSubscription] = {}  # subscription_id -> subscription
        self._event_subscribers: Dict[str, Set[str]] = {}  # event_id -> subscriber_ids
        
        # Dead letter queue for failed events
        self._dead_letter_queue: deque = deque(maxlen=1000)
        
        # Statistics
        self._stats = {
            "events_published": 0,
            "events_delivered": 0,
            "events_acknowledged": 0,
            "events_failed": 0,
            "active_subscriptions": 0,
            "queue_sizes": {},
            "oldest_unacked_event": None,
            "newest_event": None
        }
        
        # Cleanup task
        self._cleanup_task = None
        self._running = False
        
        logger.info("InMemoryEventBus initialized", config=self.config.dict())
    
    async def start(self):
        """Start the event bus and background tasks."""
        if self._running:
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Event bus started")
    
    async def stop(self):
        """Stop the event bus and cleanup resources."""
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Event bus stopped")
    
    async def publish(self, event: EventEnvelope) -> bool:
        """Publish an event to all relevant subscribers.
        
        Args:
            event: The event envelope to publish
            
        Returns:
            True if event was published successfully
        """
        try:
            # Store the event
            self._events[event.envelope_id] = event
            
            # Find subscribers interested in this event type
            interested_subscribers = self._find_interested_subscribers(event.event_type)
            
            # Add event to subscriber queues
            delivered_count = 0
            for subscriber_id in interested_subscribers:
                if subscriber_id in self._subscriber_queues:
                    queue = self._subscriber_queues[subscriber_id]
                    
                    # Check queue size limits
                    subscription = self._subscriptions.get(subscriber_id)
                    max_size = subscription.max_queue_size if subscription else 1000
                    
                    if len(queue) < max_size:
                        queue.append(event.envelope_id)
                        delivered_count += 1
                    else:
                        logger.warning(
                            "Subscriber queue full, dropping event",
                            subscriber_id=subscriber_id,
                            queue_size=len(queue),
                            event_id=event.envelope_id
                        )
            
            # Track which subscribers got this event
            self._event_subscribers[event.envelope_id] = interested_subscribers
            
            # Update statistics
            self._stats["events_published"] += 1
            self._stats["events_delivered"] += delivered_count
            self._stats["newest_event"] = event.created_at.isoformat()
            
            logger.debug(
                "Event published",
                event_id=event.envelope_id,
                event_type=event.event_type,
                subscribers=len(interested_subscribers),
                delivered=delivered_count
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to publish event", error=str(e), event_id=event.envelope_id)
            self._stats["events_failed"] += 1
            return False
    
    async def subscribe(self, subscription: EventSubscription) -> str:
        """Subscribe to events matching the given criteria.
        
        Args:
            subscription: Subscription configuration
            
        Returns:
            Subscription ID for managing the subscription
        """
        subscription_id = f"sub_{uuid.uuid4().hex[:8]}"
        
        # Store subscription
        self._subscriptions[subscription_id] = subscription
        
        # Initialize queue for this subscriber
        self._subscriber_queues[subscription.subscriber_id] = deque(
            maxlen=subscription.max_queue_size
        )
        
        # Update statistics
        self._stats["active_subscriptions"] = len(self._subscriptions)
        
        logger.info(
            "New subscription created",
            subscription_id=subscription_id,
            subscriber_id=subscription.subscriber_id,
            event_types=list(subscription.event_types) if subscription.event_types else "ALL"
        )
        
        return subscription_id
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription and clean up resources.
        
        Args:
            subscription_id: ID of subscription to remove
            
        Returns:
            True if subscription was found and removed
        """
        if subscription_id not in self._subscriptions:
            return False
        
        subscription = self._subscriptions.pop(subscription_id)
        
        # Clean up subscriber queue
        if subscription.subscriber_id in self._subscriber_queues:
            del self._subscriber_queues[subscription.subscriber_id]
        
        # Update statistics
        self._stats["active_subscriptions"] = len(self._subscriptions)
        
        logger.info(
            "Subscription removed",
            subscription_id=subscription_id,
            subscriber_id=subscription.subscriber_id
        )
        
        return True
    
    async def get_events(self, subscriber_id: str, limit: int = 100) -> List[EventEnvelope]:
        """Get pending events for a subscriber.
        
        Args:
            subscriber_id: ID of the subscriber
            limit: Maximum number of events to return
            
        Returns:
            List of event envelopes
        """
        if subscriber_id not in self._subscriber_queues:
            return []
        
        queue = self._subscriber_queues[subscriber_id]
        events = []
        
        # Get up to 'limit' events from the queue
        for _ in range(min(limit, len(queue))):
            if not queue:
                break
            
            event_id = queue.popleft()
            if event_id in self._events:
                events.append(self._events[event_id])
            else:
                logger.warning("Event not found in storage", event_id=event_id)
        
        return events
    
    async def acknowledge_event(self, event_id: str, subscriber_id: str) -> bool:
        """Acknowledge successful processing of an event.
        
        Args:
            event_id: ID of the event
            subscriber_id: ID of the subscriber acknowledging
            
        Returns:
            True if acknowledgment was processed
        """
        if event_id not in self._event_subscribers:
            return False
        
        # Remove subscriber from the event's pending list
        subscribers = self._event_subscribers[event_id]
        if subscriber_id in subscribers:
            subscribers.remove(subscriber_id)
            
            # If no more subscribers are pending, we can clean up the event
            if not subscribers:
                self._cleanup_event(event_id)
            
            self._stats["events_acknowledged"] += 1
            return True
        
        return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive bus statistics.
        
        Returns:
            Dictionary with various statistics
        """
        # Update queue sizes
        self._stats["queue_sizes"] = {
            subscriber_id: len(queue)
            for subscriber_id, queue in self._subscriber_queues.items()
        }
        
        # Find oldest unacknowledged event
        oldest_event = None
        for event in self._events.values():
            if not oldest_event or event.created_at < oldest_event:
                oldest_event = event.created_at
        
        if oldest_event:
            self._stats["oldest_unacked_event"] = oldest_event.isoformat()
        
        return {
            **self._stats,
            "total_events_in_memory": len(self._events),
            "total_subscriptions": len(self._subscriptions),
            "dead_letter_queue_size": len(self._dead_letter_queue),
            "memory_usage_estimate_mb": self._estimate_memory_usage(),
            "uptime_seconds": time.time() - (self._start_time if hasattr(self, '_start_time') else time.time())
        }
    
    def _find_interested_subscribers(self, event_type: str) -> Set[str]:
        """Find subscribers interested in a given event type.
        
        Args:
            event_type: Type of event to match
            
        Returns:
            Set of subscriber IDs
        """
        interested = set()
        
        for subscription in self._subscriptions.values():
            # If event_types is empty, subscriber wants all events
            if not subscription.event_types or event_type in subscription.event_types:
                interested.add(subscription.subscriber_id)
        
        return interested
    
    def _cleanup_event(self, event_id: str):
        """Clean up an event that has been fully acknowledged.
        
        Args:
            event_id: ID of event to clean up
        """
        if event_id in self._events:
            del self._events[event_id]
        
        if event_id in self._event_subscribers:
            del self._event_subscribers[event_id]
    
    async def _cleanup_loop(self):
        """Background task to clean up old events and maintain health."""
        while self._running:
            try:
                await self._perform_cleanup()
                await asyncio.sleep(60)  # Run cleanup every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in cleanup loop", error=str(e))
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def _perform_cleanup(self):
        """Perform cleanup of old events and statistics."""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.config.event_retention_hours)
        
        events_to_cleanup = []
        for event_id, event in self._events.items():
            if event.created_at < cutoff_time:
                events_to_cleanup.append(event_id)
        
        # Clean up old events
        for event_id in events_to_cleanup:
            self._cleanup_event(event_id)
        
        if events_to_cleanup:
            logger.info("Cleaned up old events", count=len(events_to_cleanup))
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB.
        
        Returns:
            Estimated memory usage in megabytes
        """
        # Rough estimation based on object counts
        events_size = len(self._events) * 2048  # ~2KB per event estimate
        queues_size = sum(len(q) * 64 for q in self._subscriber_queues.values())  # ~64B per queue entry
        subscriptions_size = len(self._subscriptions) * 512  # ~512B per subscription
        
        total_bytes = events_size + queues_size + subscriptions_size
        return round(total_bytes / (1024 * 1024), 2)


# Convenience functions for common operations
async def create_event_envelope(
    event_type: str,
    payload: Dict[str, Any],
    source_service: str,
    target_services: Optional[List[str]] = None,
    correlation_id: Optional[str] = None
) -> EventEnvelope:
    """Create an event envelope with standard fields populated.
    
    Args:
        event_type: Type of the event
        payload: Event data payload
        source_service: Service generating the event
        target_services: Services that should receive the event
        correlation_id: Optional correlation ID for request tracing
        
    Returns:
        Configured EventEnvelope
    """
    return EventEnvelope(
        envelope_id=f"evt_{uuid.uuid4().hex}",
        event_type=event_type,
        payload=payload,
        source_service=source_service,
        target_services=target_services or [],
        correlation_id=correlation_id
    )


# Global event bus instances
_default_bus: Optional[InMemoryEventBus] = None


async def get_default_event_bus() -> InMemoryEventBus:
    """Get the default global event bus instance.
    
    Returns:
        Default InMemoryEventBus instance
    """
    global _default_bus
    
    if _default_bus is None:
        _default_bus = InMemoryEventBus()
        await _default_bus.start()
    
    return _default_bus


async def shutdown_default_event_bus():
    """Shutdown the default global event bus."""
    global _default_bus
    
    if _default_bus is not None:
        await _default_bus.stop()
        _default_bus = None