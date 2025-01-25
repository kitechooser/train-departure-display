from typing import Optional, Tuple, Any
from PIL import Image, ImageDraw
import time
from .text import TextComponent, TextStyle
from .scroll import ScrollComponent

class StatusComponent:
    """Component for animated status messages"""
    
    def __init__(self, viewport_width: int, viewport_height: int, style: TextStyle):
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.style = style
        
        # Create text and scroll components
        self.text_component = TextComponent("", style)
        self.scroll_component = ScrollComponent(
            self.text_component,
            viewport_width,
            viewport_height
        )
        
        # Animation state
        self.is_elevated = False
        self.pixels_up = 0
        self.elevation_speed = 1  # pixels per frame
        self.elevation_pause = 20  # frames to pause after elevation
        self.pause_count = 0
        self.animation_start = 0
        self.is_showing = False
        self.status_duration = 0
        self.test_mode = False  # For testing
        
        # Create viewport bitmap
        self.viewport = Image.new('1', (viewport_width, viewport_height))
        self.viewport_draw = ImageDraw.Draw(self.viewport)
        
    def get_size(self) -> Tuple[int, int]:
        """Get the size of the viewport"""
        return (self.viewport_width, self.viewport_height)
        
    def show_status(self, text: str, duration: float, test_mode: bool = False) -> None:
        """Start showing a status message
        
        Args:
            text: The status message to show
            duration: How long to show the status in seconds
            test_mode: Whether to enable test mode
        """
        self.text_component.set_text(text)
        self.status_duration = duration
        self.animation_start = time.time()
        self.is_showing = True
        self.is_elevated = False
        self.pixels_up = 0
        self.pause_count = 0
        self.test_mode = test_mode
        self.scroll_component.stop_scroll()  # Reset scroll state
        
    def hide_status(self) -> None:
        """Stop showing the status message"""
        self.is_showing = False
        self.is_elevated = False
        self.pixels_up = 0
        self.pause_count = 0
        self.test_mode = False
        self.scroll_component.stop_scroll()
        
    def update(self) -> None:
        """Update the status animation state"""
        if not self.is_showing:
            return
            
        current_time = time.time()
        
        # Check if duration expired
        if current_time - self.animation_start >= self.status_duration:
            self.hide_status()
            return
            
        # Handle elevation animation
        if not self.is_elevated:
            if self.pixels_up < self.viewport_height:
                self.pixels_up += self.elevation_speed
            elif not self.test_mode and self.pause_count < self.elevation_pause:
                self.pause_count += 1
            else:
                self.is_elevated = True
                self.scroll_component.start_scroll(test_mode=self.test_mode)
                self.pause_count = 0  # Reset pause count for scroll animation
        else:
            # Update scroll animation
            self.scroll_component.update()
            
    def render(self, draw: Optional[ImageDraw.ImageDraw] = None, x: int = 0, y: int = 0) -> Optional[Image.Image]:
        """Render the status message
        
        Args:
            draw: Optional ImageDraw object to draw on. If None, returns the viewport bitmap.
            x: X coordinate to draw at
            y: Y coordinate to draw at
            
        Returns:
            If draw is None, returns the viewport bitmap. Otherwise returns None.
        """
        # Clear viewport
        self.viewport_draw.rectangle(
            [0, 0, self.viewport_width - 1, self.viewport_height - 1],
            fill=0  # Black background
        )
        
        if not self.is_elevated:
            # Render elevation animation
            text_height = self.text_component.get_size()[1]
            render_y = y + text_height - self.pixels_up
            if render_y >= 0:  # Only render if text is visible
                self.text_component.render(self.viewport_draw, x, render_y)
        else:
            # Render scrolling text
            self.scroll_component.render(self.viewport_draw, x, y)
            
        if draw is None:
            return self.viewport
        else:
            # Copy viewport to destination
            draw.bitmap((x, y), self.viewport, fill=1)  # White foreground
            return None
            
    def set_style(self, style: TextStyle) -> None:
        """Update the text style"""
        self.style = style
        self.text_component.set_style(style)
        
    def set_scroll_speed(self, speed: int) -> None:
        """Set the scroll speed in pixels per frame"""
        self.scroll_component.set_scroll_speed(speed)
        
    def set_elevation_speed(self, speed: int) -> None:
        """Set the elevation animation speed in pixels per frame"""
        self.elevation_speed = speed
        
    def set_pause_frames(self, elevation_pause: int, scroll_start: int, scroll_end: int) -> None:
        """Set the number of frames to pause during animations"""
        self.elevation_pause = elevation_pause
        self.scroll_component.set_pause_frames(scroll_start, scroll_end)
