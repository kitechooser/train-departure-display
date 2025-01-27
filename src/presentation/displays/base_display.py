from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import logging
from PIL import Image
from src.infrastructure.event_bus import EventBus

logger = logging.getLogger(__name__)

@dataclass
class DisplayConfig:
    """Configuration for display components"""
    width: int
    height: int
    font_size: int = 8  # Reduced from 16 to 8
    line_spacing: int = 1  # Reduced from 2 to 1
    padding: tuple[int, int, int, int] = (0, 0, 0, 0)  # Removed default padding
    scroll_speed: int = 2
    scroll_pause: int = 30

class BaseDisplay(ABC):
    """Base class for all display implementations"""
    
    def __init__(self, width: int, height: int, event_bus: Optional[EventBus] = None, display_id: str = ""):
        """Initialize the display
        
        Args:
            width: Display width in pixels
            height: Display height in pixels
            event_bus: Optional event bus for event handling
            display_id: Unique identifier for this display
        """
        self.width = width
        self.height = height
        self.event_bus = event_bus
        self.device = None  # Will be set by MainService
        self.id = display_id
        logger.info(f"Initializing display {display_id} ({width}x{height})")
        if event_bus:
            self.subscribe_to_events()
        
    @abstractmethod
    def render(self) -> Image.Image:
        """Render the display content
        
        Returns:
            PIL Image containing the rendered display
        """
        pass

    def update_display(self, image: Image.Image) -> None:
        """Update the physical/mock display with new content
        
        Args:
            image: PIL Image to display
        """
        if self.device:
            logger.info(f"Updating device for display {self.id} with image size {image.size}")
            self.device.display(image)
        else:
            logger.warning(f"No device set for display {self.id}")
        
    def subscribe_to_events(self) -> None:
        """Subscribe to relevant events on the event bus"""
        if self.event_bus:
            logger.info(f"Subscribing display {self.id} to events")
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
            logger.info(f"Cleaning up display {self.id}")
            self.event_bus.unsubscribe('display_update', self.handle_event)
            self.event_bus.unsubscribe('display_clear', self.handle_event)
