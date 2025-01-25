from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from PIL import Image
from src.infrastructure.event_bus import EventBus

@dataclass
class DisplayConfig:
    """Configuration for display components"""
    width: int
    height: int
    font_size: int = 16
    line_spacing: int = 2
    padding: tuple[int, int, int, int] = (5, 5, 5, 5)  # left, top, right, bottom
    scroll_speed: int = 2
    scroll_pause: int = 30

class BaseDisplay(ABC):
    """Base class for all display implementations"""
    
    def __init__(self, width: int, height: int, event_bus: Optional[EventBus] = None):
        """Initialize the display
        
        Args:
            width: Display width in pixels
            height: Display height in pixels
            event_bus: Optional event bus for event handling
        """
        self.width = width
        self.height = height
        self.event_bus = event_bus
        
    @abstractmethod
    def render(self) -> Image.Image:
        """Render the display content
        
        Returns:
            PIL Image containing the rendered display
        """
        pass
        
    def subscribe_to_events(self) -> None:
        """Subscribe to relevant events on the event bus"""
        if self.event_bus:
            self.event_bus.subscribe('display_update', self.handle_event)
            self.event_bus.subscribe('display_clear', self.handle_event)
            
    def handle_event(self, event: Dict[str, Any]) -> None:
        """Handle incoming events
        
        Args:
            event: Event data dictionary containing type and payload
        """
        # Base implementation does nothing
        pass
        
    def cleanup(self) -> None:
        """Clean up resources and event subscriptions"""
        if self.event_bus:
            self.event_bus.unsubscribe('display_update', self.handle_event)
            self.event_bus.unsubscribe('display_clear', self.handle_event)
