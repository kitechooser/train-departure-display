from typing import Dict, Any, Optional, List
import logging
from src.infrastructure.event_bus import EventBus
from src.infrastructure.queue_manager import QueueManager
from src.presentation.displays.base_display import BaseDisplay

logger = logging.getLogger(__name__)

class DisplayService:
    """Service for managing displays and their updates"""
    
    def __init__(self, event_bus: EventBus, queue_manager: QueueManager):
        """Initialize the display service
        
        Args:
            event_bus: Event bus for handling events
            queue_manager: Queue manager for handling display queues
        """
        self.event_bus = event_bus
        self.queue_manager = queue_manager
        self.displays: List[BaseDisplay] = []
        
        # Subscribe to events
        self.event_bus.subscribe('display_update', self.handle_event)
        self.event_bus.subscribe('display_clear', self.handle_event)
        
    def handle_event(self, event: Dict[str, Any]) -> None:
        """Handle incoming events
        
        Args:
            event: Event data dictionary containing type and payload
        """
        if 'type' in event:
            if event['type'] == 'display_update':
                display_id = event.get('data', {}).get('display_id')
                content = event.get('data', {}).get('content')
                if display_id is not None and content is not None:
                    logger.info(f"Handling display update event for {display_id}: {content}")
                    self.update_display(display_id, content)
            elif event['type'] == 'display_clear':
                display_id = event.get('data', {}).get('display_id')
                if display_id is not None:
                    logger.info(f"Handling display clear event for {display_id}")
                    self.clear_display(display_id)
                
    def register_display(self, display: BaseDisplay) -> None:
        """Register a display with the service
        
        Args:
            display: Display instance to register
        """
        logger.info(f"Registering display: {display.id}")
        self.displays.append(display)
        
    def get_display(self, display_id: str) -> Optional[BaseDisplay]:
        """Get a display by ID
        
        Args:
            display_id: ID of the display to get
            
        Returns:
            Display instance if found, None otherwise
        """
        for display in self.displays:
            if display.id == display_id:
                return display
        logger.warning(f"Display not found: {display_id}")
        return None
        
    def update_display(self, display_id: str, content: Any) -> None:
        """Update a display with new content
        
        Args:
            display_id: ID of the display to update
            content: New content for the display
        """
        display = self.get_display(display_id)
        if display:
            logger.info(f"Updating display {display_id} with content: {content}")
            display.update(content)
            logger.info(f"Rendering display {display_id}")
            display.render()  # Ensure display is rendered after update
            self.event_bus.emit('display_updated', {
                'display_id': display_id
            })
            
    def clear_display(self, display_id: str) -> None:
        """Clear a display
        
        Args:
            display_id: ID of the display to clear
        """
        display = self.get_display(display_id)
        if display:
            logger.info(f"Clearing display {display_id}")
            display.clear()
            self.event_bus.emit('display_cleared', {
                'display_id': display_id
            })
            
    def update_all(self) -> None:
        """Update all displays"""
        logger.debug("Updating all displays")
        for display in self.displays:
            display.render()
            
    def cleanup(self) -> None:
        """Clean up resources and event subscriptions"""
        logger.info("Cleaning up display service")
        self.event_bus.unsubscribe('display_update', self.handle_event)
        self.event_bus.unsubscribe('display_clear', self.handle_event)
        for display in self.displays:
            display.cleanup()
        self.displays.clear()
