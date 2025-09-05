"""Event routing utilities for the event bus system."""

from typing import Dict, List, Set, Callable, Any
import structlog

logger = structlog.get_logger(__name__)


class EventRouter:
    """Routes events based on patterns and filters."""
    
    def __init__(self):
        """Initialize event router."""
        self.routes: Dict[str, List[Callable]] = {}
        
    def add_route(self, pattern: str, handler: Callable):
        """Add event route.
        
        Args:
            pattern: Event pattern to match
            handler: Handler function
        """
        if pattern not in self.routes:
            self.routes[pattern] = []
        self.routes[pattern].append(handler)
        
    def route_event(self, event_type: str, event_data: Any) -> List[Any]:
        """Route event to matching handlers.
        
        Args:
            event_type: Type of event
            event_data: Event data
            
        Returns:
            List of handler results
        """
        results = []
        
        for pattern, handlers in self.routes.items():
            if self._match_pattern(event_type, pattern):
                for handler in handlers:
                    try:
                        result = handler(event_data)
                        results.append(result)
                    except Exception as e:
                        logger.error("Handler failed", pattern=pattern, error=str(e))
        
        return results
    
    def _match_pattern(self, event_type: str, pattern: str) -> bool:
        """Check if event type matches pattern.
        
        Args:
            event_type: Event type to check
            pattern: Pattern to match against
            
        Returns:
            True if pattern matches
        """
        if pattern == "*":
            return True
        if pattern == event_type:
            return True
        if pattern.endswith("*") and event_type.startswith(pattern[:-1]):
            return True
        return False