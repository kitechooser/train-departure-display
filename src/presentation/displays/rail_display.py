from typing import List, Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont
from .base_display import BaseDisplay, DisplayConfig
from src.infrastructure.event_bus import EventBus
from src.domain.models.station import Station
from src.domain.models.service import Service
from src.presentation.renderers.components.text import TextComponent, TextStyle
from src.presentation.renderers.components.scroll import ScrollComponent
from src.presentation.renderers.layouts.grid import GridLayout

class RailDisplay(BaseDisplay):
    """National Rail display implementation"""
    
    def __init__(self, width: int, height: int, event_bus: Optional[EventBus] = None):
        """Initialize the rail display
        
        Args:
            width: Display width in pixels
            height: Display height in pixels
            event_bus: Optional event bus for event handling
        """
        super().__init__(width, height, event_bus)
        self.config = DisplayConfig(width=width, height=height)
        self.station: Optional[Station] = None
        self.services: List[Service] = []
        
    def render(self) -> Image.Image:
        """Render the display content
        
        Returns:
            PIL Image containing the rendered display
        """
        # Create base image
        image = Image.new('1', (self.width, self.height))
        draw = ImageDraw.Draw(image)
        
        # Create layout grid
        grid = GridLayout(self.width, self.height, rows=5, cols=1)  # Header + 2 services * 2 rows each
        
        # Add header if station is set
        if self.station:
            font = ImageFont.truetype("src/fonts/Dot Matrix Bold.ttf", 24)
            style = TextStyle(font=font)
            header = TextComponent(self.station.name, style)
            grid.add_component(header, row=0, col=0, padding=(5, 5, 5, 5))
            
        # Add services if available
        if self.services:
            font = ImageFont.truetype("src/fonts/Dot Matrix Regular.ttf", 16)
            style = TextStyle(font=font)
            for i, service in enumerate(self.services[:2]):  # Show up to 2 services
                # Platform info
                platform_text = f"Platform {service.platform}"
                platform_component = TextComponent(platform_text, style)
                grid.add_component(platform_component, row=i*2+1, col=0, padding=(5, 2, 5, 2))
                
                # Service info
                text = f"{service.destination} - {service.status}"
                text_component = TextComponent(text, style)
                component = ScrollComponent(text_component, self.width - 10, 20)  # -10 for padding
                component.set_scroll_speed(2)
                grid.add_component(component, row=i*2+2, col=0, padding=(5, 2, 5, 2))
                
        # Render the grid
        draw.bitmap((0, 0), grid.render(), fill=1)
        return image
        
    def handle_event(self, event: Dict[str, Any]) -> None:
        """Handle incoming events
        
        Args:
            event: Event data dictionary containing type and payload
        """
        if event['type'] == 'display_update':
            self.station = event['data'].get('station')
            self.services = event['data'].get('services', [])
        elif event['type'] == 'display_clear':
            self.station = None
            self.services = []
