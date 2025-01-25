from typing import Optional, Tuple, Any
from PIL import Image, ImageDraw
import time
from .text import TextComponent, TextStyle

class ScrollComponent:
    """Component for scrolling text animations"""
    
    def __init__(self, text_component: TextComponent, viewport_width: int, viewport_height: int):
        self.text_component = text_component
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        
        # Animation state
        self.scroll_position = 0
        self.scroll_speed = 1  # pixels per frame
        self.start_pause = 20  # frames to pause at start
        self.end_pause = 8  # frames to pause at end
        self.pause_count = 0
        self.animation_start = 0
        self.is_scrolling = False
        self.test_mode = False  # For testing
        self.at_end = False  # Track if we've reached the end
        
        # Create viewport bitmap
        self.viewport = Image.new('1', (viewport_width, viewport_height))
        self.viewport_draw = ImageDraw.Draw(self.viewport)
        
        # Track text changes
        self._last_text = text_component.text
        
    def get_size(self) -> Tuple[int, int]:
        """Get the size of the viewport"""
        return (self.viewport_width, self.viewport_height)
        
    def start_scroll(self, test_mode: bool = False) -> None:
        """Start the scroll animation"""
        self.scroll_position = 0
        self.pause_count = 0
        self.animation_start = time.time()
        self.is_scrolling = True
        self.test_mode = test_mode
        self.at_end = False
        
    def stop_scroll(self) -> None:
        """Stop the scroll animation"""
        self.is_scrolling = False
        self.scroll_position = 0
        self.pause_count = 0
        self.test_mode = False
        self.at_end = False
        
    def reset(self) -> None:
        """Reset the scroll animation state"""
        self.scroll_position = 0
        self.pause_count = 0
        self.is_scrolling = False  # Stop scrolling on reset
        self.test_mode = False
        self.at_end = False
        
    def _needs_scroll(self) -> bool:
        """Check if text needs scrolling"""
        text_width = self.text_component.get_size()[0]
        return text_width > self.viewport_width
        
    def update(self) -> None:
        """Update the scroll animation state"""
        # Check for text changes
        if self.text_component.text != self._last_text:
            self._last_text = self.text_component.text
            self.stop_scroll()
            return
            
        if not self.is_scrolling:
            return
            
        # Get text width for max scroll
        text_width = self.text_component.get_size()[0]
        max_scroll = text_width - self.viewport_width
        
        # Check if we've reached the end
        if -self.scroll_position >= max_scroll:
            self.at_end = True
            
        # Check if scrolling is needed
        if not self._needs_scroll():
            self.stop_scroll()
            return
            
        # Test mode - skip pauses and scroll immediately
        if self.test_mode:
            self.scroll_position -= self.scroll_speed
            return
            
        # Handle start pause
        if self.scroll_position == 0:
            if self.pause_count < self.start_pause:
                self.pause_count += 1
                return
            self.pause_count = 0  # Reset pause count after start pause
            
        # Handle end pause
        if self.at_end:
            if self.pause_count < self.end_pause:
                self.pause_count += 1
                return
            self.stop_scroll()  # Stop scrolling after end pause
            return
            
        # Regular scrolling
        self.scroll_position -= self.scroll_speed
        
    def render(self, draw: Optional[ImageDraw.ImageDraw] = None, x: int = 0, y: int = 0) -> Optional[Image.Image]:
        """Render the scrolling text
        
        Args:
            draw: Optional ImageDraw object to draw on. If None, returns the viewport bitmap.
            x: X coordinate to draw at
            y: Y coordinate to draw at
            
        Returns:
            If draw is None, returns the viewport bitmap. Otherwise returns None.
        """
        # Create fresh viewport for each render
        self.viewport = Image.new('1', (self.viewport_width, self.viewport_height))
        self.viewport_draw = ImageDraw.Draw(self.viewport)
        
        # Clear viewport
        self.viewport_draw.rectangle(
            [0, 0, self.viewport_width - 1, self.viewport_height - 1],
            fill=0  # Black background
        )
        
        # Draw text at current scroll position
        render_x = x + self.scroll_position
        render_y = y + (self.viewport_height - self.text_component.get_size()[1]) // 2
        self.text_component.render(self.viewport_draw, render_x, render_y)
        
        if draw is None:
            return self.viewport
        else:
            # Copy viewport to destination
            draw.bitmap((x, y), self.viewport, fill=1)  # White foreground
            return None
        
            
    def set_text(self, text: str) -> None:
        """Update the text content"""
        if text != self.text_component.text:
            self.text_component.set_text(text)
            self.stop_scroll()
            self._last_text = text
        
    def set_style(self, style: TextStyle) -> None:
        """Update the text style"""
        self.text_component.set_style(style)
        self.stop_scroll()
        
    def set_scroll_speed(self, speed: int) -> None:
        """Set the scroll speed in pixels per frame"""
        self.scroll_speed = speed
        
    def set_pause_frames(self, start: int, end: int) -> None:
        """Set the number of frames to pause at start and end"""
        self.start_pause = start
        self.end_pause = end
