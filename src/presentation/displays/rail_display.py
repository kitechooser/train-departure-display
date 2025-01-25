from typing import Dict, Any, List, Optional
from PIL import Image, ImageDraw
import time
from .base_display import BaseDisplay, DisplayConfig
from ..renderers.components.text import TextComponent, TextStyle
from ..renderers.components.scroll import ScrollComponent

class RailDisplay(BaseDisplay):
    """National Rail specific display implementation"""
    
    def __init__(self, config: DisplayConfig):
        super().__init__(config)
        
        # Create components for each row
        self._setup_row_components()
        
        # State
        self.current_departures: List[Dict[str, Any]] = []
        self.current_calling_points: Optional[str] = None
        self.current_station: str = ""
        
    def _setup_row_components(self) -> None:
        """Set up the components for each row"""
        # Row 1 (First departure)
        self.rows[0].add_component(
            TextComponent("", self.bold_style),  # Platform
            width=50,
            padding=(2, 0, 2, 0)
        )
        self.rows[0].add_component(
            TextComponent("", self.bold_style),  # Destination
            padding=(2, 0, 2, 0)
        )
        self.rows[0].add_component(
            TextComponent("", self.bold_style),  # Time
            width=50,
            padding=(2, 0, 2, 0),
            align_v="center"
        )
        self.rows[0].add_component(
            TextComponent("", self.bold_style),  # Status
            width=60,
            padding=(2, 0, 2, 0),
            align_v="center"
        )
        
        # Row 2 (Calling points)
        self.rows[1].add_component(
            TextComponent("Calling at:", self.text_style),
            width=70,
            padding=(2, 0, 2, 0)
        )
        self.calling_points_scroll = ScrollComponent(
            TextComponent("", self.text_style),
            self.config.width - 70,
            12
        )
        self.rows[1].add_component(
            self.calling_points_scroll,
            padding=(0, 0, 2, 0)
        )
        
        # Row 3 (Second departure)
        self.rows[2].add_component(
            TextComponent("", self.text_style),  # Platform
            width=50,
            padding=(2, 0, 2, 0)
        )
        self.rows[2].add_component(
            TextComponent("", self.text_style),  # Destination
            padding=(2, 0, 2, 0)
        )
        self.rows[2].add_component(
            TextComponent("", self.text_style),  # Time
            width=50,
            padding=(2, 0, 2, 0),
            align_v="center"
        )
        self.rows[2].add_component(
            TextComponent("", self.text_style),  # Status
            width=60,
            padding=(2, 0, 2, 0),
            align_v="center"
        )
        
        # Row 4 (Third departure or status)
        self.rows[3].add_component(
            TextComponent("", self.text_style),  # Platform
            width=50,
            padding=(2, 0, 2, 0)
        )
        self.rows[3].add_component(
            TextComponent("", self.text_style),  # Destination
            padding=(2, 0, 2, 0)
        )
        self.rows[3].add_component(
            TextComponent("", self.text_style),  # Time
            width=50,
            padding=(2, 0, 2, 0),
            align_v="center"
        )
        self.rows[3].add_component(
            TextComponent("", self.text_style),  # Status
            width=60,
            padding=(2, 0, 2, 0),
            align_v="center"
        )
        
        # Row 5 (Time)
        self.rows[4].add_component(
            TextComponent("", self.bold_tall_style),  # Current time
            padding=(2, 0, 2, 0),
            align_v="center"
        )
        
    def update(self) -> None:
        """Update display state"""
        super().update()
        
        # Update calling points scroll
        self.calling_points_scroll.update()
            
    def set_departures(self, departures: List[Dict[str, Any]], 
                      calling_points: Optional[str],
                      station: str) -> None:
        """Set the current departures to display"""
        self.current_departures = departures
        self.current_calling_points = calling_points
        self.current_station = station
        
        if not departures:
            self._show_no_departures()
            return
            
        # Update first departure row
        first = departures[0]
        self.rows[0].items[0].component.set_text(f"Plat {first['platform']}")
        self.rows[0].items[1].component.set_text(first["destination_name"])
        self.rows[0].items[2].component.set_text(first["aimed_departure_time"])
        self.rows[0].items[3].component.set_text(first["expected_departure_time"])
        
        # Update calling points
        if calling_points:
            self.calling_points_scroll.set_text(calling_points)
            self.calling_points_scroll.start_scroll()
            
        # Update second departure row if available
        if len(departures) > 1:
            second = departures[1]
            self.rows[2].items[0].component.set_text(f"Plat {second['platform']}")
            self.rows[2].items[1].component.set_text(second["destination_name"])
            self.rows[2].items[2].component.set_text(second["aimed_departure_time"])
            self.rows[2].items[3].component.set_text(second["expected_departure_time"])
            
        # Update third departure row if available and not showing status
        if len(departures) > 2 and not self.status.is_showing:
            third = departures[2]
            self.rows[3].items[0].component.set_text(f"Plat {third['platform']}")
            self.rows[3].items[1].component.set_text(third["destination_name"])
            self.rows[3].items[2].component.set_text(third["aimed_departure_time"])
            self.rows[3].items[3].component.set_text(third["expected_departure_time"])
            
    def _show_no_departures(self) -> None:
        """Show the no departures message"""
        message = f"No trains from {self.current_station}"
        text_width = int(self.text_style.font.getlength(message))
        x = (self.config.width - text_width) // 2
        
        # Clear rows
        for row in self.rows[:-1]:  # Keep time row
            for item in row.items:
                item.component.set_text("")
                
        # Show message in first row
        self.rows[0].items[0].component.set_text(message)
        
    def set_time(self, time_str: str) -> None:
        """Set the current time display"""
        self.rows[4].items[0].component.set_text(time_str)
        
    def show_status(self, status: str, duration: float) -> None:
        """Show a status message"""
        self.status.show_status(status, duration)
