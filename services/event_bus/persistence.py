"""Event persistence utilities for the event bus system."""

import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import structlog

from services.shared.schemas import EventEnvelope

logger = structlog.get_logger(__name__)


class EventPersistence:
    """Handles persistence of events to disk."""
    
    def __init__(self, storage_path: str = "./events"):
        """Initialize event persistence.
        
        Args:
            storage_path: Path to store events
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
    async def persist_event(self, event: EventEnvelope) -> bool:
        """Persist an event to disk.
        
        Args:
            event: Event to persist
            
        Returns:
            True if successful
        """
        try:
            event_file = self.storage_path / f"{event.envelope_id}.json"
            
            with open(event_file, 'w') as f:
                json.dump(event.dict(), f, indent=2, default=str)
            
            return True
            
        except Exception as e:
            logger.error("Failed to persist event", error=str(e))
            return False
    
    async def load_events(self, limit: int = 100) -> List[EventEnvelope]:
        """Load events from disk.
        
        Args:
            limit: Maximum number of events to load
            
        Returns:
            List of loaded events
        """
        events = []
        
        try:
            event_files = list(self.storage_path.glob("*.json"))
            event_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            for event_file in event_files[:limit]:
                with open(event_file, 'r') as f:
                    event_data = json.load(f)
                    
                event = EventEnvelope(**event_data)
                events.append(event)
                
        except Exception as e:
            logger.error("Failed to load events", error=str(e))
        
        return events
    
    async def cleanup_old_events(self, max_age_hours: int = 24) -> int:
        """Clean up old event files.
        
        Args:
            max_age_hours: Maximum age of events to keep
            
        Returns:
            Number of files cleaned up
        """
        cleaned_count = 0
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        try:
            for event_file in self.storage_path.glob("*.json"):
                if event_file.stat().st_mtime < cutoff_time:
                    event_file.unlink()
                    cleaned_count += 1
                    
        except Exception as e:
            logger.error("Failed to cleanup events", error=str(e))
        
        return cleaned_count