from typing import List, Optional, Dict, Any
import logging
from PIL import Image, ImageDraw, ImageFont
from .base_display import BaseDisplay, DisplayConfig
from src.infrastructure.event_bus import EventBus
from src.domain.models.station import Station
from src.domain.models.service import Service
from src.presentation.renderers.components.text import TextComponent, TextStyle
from src.presentation.renderers.components.scroll import ScrollComponent
from src.presentation.renderers.layouts.grid import GridLayout

logger = logging.getLogger(__name__)

class RailDisplay(BaseDisplay):
    """National Rail display implementation"""

    def __init__(self, width: int = 256, height: int = 64, event_bus: Optional[EventBus] = None, display_id: str = "rail"):
        """Initialize the rail display

        Args:
            event_bus: Optional event bus for event handling
            width: Display width in pixels (default: 256)
            height: Display height in pixels (default: 64)
            display_id: Unique identifier for this display (default: "rail")
        """
        super().__init__(width, height, event_bus, display_id=display_id)
        self.config = DisplayConfig(width=width, height=height)
        self.station: Optional[Station] = None
        self.services: List[Service] = []
        # Initialize components without event bus to prevent subscription
        self.grid = GridLayout(width=width, height=height, rows=4, cols=3)  # 4 rows, 3 columns for destination, platform, time
        style = TextStyle(font=ImageFont.truetype("src/fonts/Dot Matrix Bold.ttf", 8), color=1, align="center")  # White text
        self.text = TextComponent("", style, None)
        self.scroll = ScrollComponent(self.text, width, height, None)
        logger.info("Rail display initialized")
        
        # Subscribe to events
        if event_bus:
            event_bus.subscribe('display_update', self.handle_event)
            event_bus.subscribe('display_clear', self.handle_event)
            
    def render(self) -> Image.Image:
        """Render the display content

        Returns:
            PIL Image containing the rendered display
        """
        logger.info("Rendering rail display")
        # Create a new image with black background
        image = Image.new('1', (self.width, self.height), 0)  # 0 = black in binary mode
        
        # Draw either grid content or text content
        grid_image = self.grid.render()
        if grid_image and len(self.services) > 0:
            logger.debug("Drawing grid content")
            # Paste grid image directly
            image.paste(grid_image, (0, 0))
        else:
            # Draw text content if no grid content
            text_image = self.text.render()
            if text_image:
                logger.debug(f"Drawing text content: {self.text.text}")
                image.paste(text_image, (0, 0))
            
        # Draw scroll content
        scroll_image = self.scroll.render()
        if scroll_image:
            logger.debug("Drawing scroll content")
            image.paste(scroll_image, (0, self.height - scroll_image.height))
            
        # Update physical/mock display
        self.update_display(image)
        return image
            
    def handle_event(self, event: Dict[str, Any]) -> None:
        """Handle incoming events
        
        Args:
            event: Event data dictionary containing type and payload
        """
        if 'type' in event:
            if event['type'] == 'display_update':
                data = event.get('data', {})
                if 'station' in data and 'services' in data:
                    logger.info(f"Handling display update with station and services data")
                    self.station = data['station']
                    self.services = data['services']
                    self.draw_services(self.services)
                elif 'content' in data:
                    content = data['content']
                    if 'departures' in content:
                        logger.info(f"Handling display update with departures data")
                        # Convert departures to services format
                        services = []
                        for departure in content['departures']:
                            service = Service(
                                destination_name=departure.get('destination_name', 'Unknown'),
                                platform=departure.get('platform', ''),
                                calling_at_list=departure.get('calling_at_list', [])
                            )
                            services.append(service)
                        self.services = services
                        self.draw_services(services)
                    elif 'error' in content:
                        logger.info(f"Handling display error: {content['error']}")
                        self.draw_error(content['error'])
            elif event['type'] == 'display_clear':
                logger.info("Handling display clear event")
                self.clear()
            
    def update(self, content: Dict[str, Any]) -> None:
        """Update display content
        
        Args:
            content: Display content dictionary
        """
        logger.info(f"Updating display content: {content}")
        # Clear previous content
        self.clear()
        
        # Draw new content
        if 'error' in content:
            self.draw_error(content['error'])
        elif 'services' in content:
            self.draw_services(content['services'])
        elif 'status' in content:
            self.draw_status(content['status'])
            
    def draw_error(self, error: str) -> None:
        """Draw error message
        
        Args:
            error: Error message to display
        """
        logger.info(f"Drawing error message: {error}")
        font = ImageFont.truetype("src/fonts/Dot Matrix Bold.ttf", 8)
        style = TextStyle(font=font, color=1, align="center")  # White text
        self.text.set_style(style)  # Set style first
        self.text.set_text(error)  # Then set text
        # Force a render after updating
        self.render()
        
    def draw_services(self, services: List[Service]) -> None:
        """Draw service information
        
        Args:
            services: List of services to display
        """
        logger.info(f"Drawing services: {len(services)} services")
        # Clear grid before adding new components
        self.grid.clear()
        
        # Add each service to a new row
        for row, service in enumerate(services):
            # Create text components for each column with white text
            style = TextStyle(
                font=ImageFont.truetype("src/fonts/Dot Matrix Bold.ttf", 8),
                color=1,  # White text
                align="left"
            )
            dest_text = TextComponent(service.destination, style, None)
            plat_text = TextComponent(str(service.platform), style, None)
            time_text = TextComponent(service.status if hasattr(service, 'status') else '', style, None)
            
            # Add each component to its respective column
            self.grid.add_component(dest_text, row, 0)
            self.grid.add_component(plat_text, row, 1)
            self.grid.add_component(time_text, row, 2)
            
    def draw_status(self, status: Dict[str, Any]) -> None:
        """Draw status information
        
        Args:
            status: Status information dictionary
        """
        logger.info(f"Drawing status: {status}")
        font = ImageFont.truetype("src/fonts/Dot Matrix Bold.ttf", 8)
        style = TextStyle(font=font, color=1, align="center")  # White text
        self.text.set_text(status.get('description', ''))
        self.text.set_style(style)
        
    def clear(self) -> None:
        """Clear display content"""
        logger.info("Clearing display content")
        self.station = None
        self.services = []
        self.grid.clear()
        self.scroll.reset()
        self.text.set_text("")
