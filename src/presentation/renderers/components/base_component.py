from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from PIL import Image, ImageDraw
from src.infrastructure.event_bus import EventBus

class BaseComponent(ABC):
    """Base class for all display components"""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        """Initialize the component
        
        Args:
            event_bus: Optional event bus for event handling
        """
        self.event_bus = event_bus
        self._needs_refresh = True
        
    @abstractmethod
    def get_size(self) -> Tuple[int, int]:
        """Get the size of the component
        
        Returns:
            Tuple of (width, height) in pixels
        """
        pass
        
    @abstractmethod
    def render(self, draw: Optional[ImageDraw.ImageDraw] = None, x: int = 0, y: int = 0) -> Optional[Image.Image]:
        """Render the component
        
        Args:
            draw: Optional ImageDraw object to draw on. If None, returns a new bitmap.
            x: X coordinate to draw at
            y: Y coordinate to draw at
            
        Returns:
            If draw is None, returns a new bitmap. Otherwise returns None.
        """
        pass
        
    def subscribe_to_events(self) -> None:
        """Subscribe to relevant events on the event bus"""
        if self.event_bus:
            self.event_bus.subscribe('component_update', self.handle_event)
            self.event_bus.subscribe('component_clear', self.handle_event)
            
    def handle_event(self, event: Dict[str, Any]) -> None:
        """Handle incoming events
        
        Args:
            event: Event data dictionary containing type and payload
        """
        if event['type'] == 'component_update':
            self._needs_refresh = True
        elif event['type'] == 'component_clear':
            self._needs_refresh = True
            
    def cleanup(self) -> None:
        """Clean up resources and event subscriptions"""
        if self.event_bus:
            self.event_bus.unsubscribe('component_update', self.handle_event)
            self.event_bus.unsubscribe('component_clear', self.handle_event)
