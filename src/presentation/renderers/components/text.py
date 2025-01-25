from typing import Optional, Tuple, Any, Dict
from PIL import Image, ImageDraw, ImageFont
from dataclasses import dataclass
from .base_component import BaseComponent
from src.infrastructure.event_bus import EventBus

@dataclass
class TextStyle:
    """Text style configuration"""
    font: ImageFont.FreeTypeFont
    color: int = 1  # White foreground
    align: str = "left"  # left, center, right
    padding: Tuple[int, int, int, int] = (0, 0, 0, 0)  # left, top, right, bottom

class TextComponent(BaseComponent):
    """Component for rendering text"""
    
    def __init__(self, text: str, style: TextStyle, event_bus: Optional[EventBus] = None):
        super().__init__(event_bus)
        self.text = text
        self.style = style
        self._cached_size: Optional[Tuple[int, int]] = None
        self._cached_bitmap: Optional[Image.Image] = None
        
    def get_size(self) -> Tuple[int, int]:
        """Get the size of the text including padding"""
        if self._cached_size is None:
            # Get text bounds
            left, top, right, bottom = self.style.font.getbbox(self.text)
            text_width = right - left
            text_height = bottom - top
            
            # Add padding
            width = text_width + self.style.padding[0] + self.style.padding[2]
            height = text_height + self.style.padding[1] + self.style.padding[3]
            
            self._cached_size = (width, height)
        return self._cached_size
        
    def render(self, draw: Optional[ImageDraw.ImageDraw] = None, x: int = 0, y: int = 0) -> Optional[Image.Image]:
        """Render the text
        
        Args:
            draw: Optional ImageDraw object to draw on. If None, returns a new bitmap.
            x: X coordinate to draw at
            y: Y coordinate to draw at
            
        Returns:
            If draw is None, returns a new bitmap. Otherwise returns None.
        """
        # Get text bounds for positioning
        left, top, right, bottom = self.style.font.getbbox(self.text)
        text_width = right - left
        text_height = bottom - top
        
        # Get total size including padding
        width, height = self.get_size()
        
        if draw is None:
            # Return cached bitmap if available and text hasn't changed
            if self._cached_bitmap is not None:
                return self._cached_bitmap
                
            # Create bitmap
            bitmap = Image.new('1', (width, height))
            draw = ImageDraw.Draw(bitmap)
            
            # Create bitmap with extra space for alignment
            render_width = max(width, text_width + 20)  # Add extra space to make alignment visible
            bitmap = Image.new('1', (render_width, height))
            draw = ImageDraw.Draw(bitmap)
            
            # Calculate text position
            if self.style.align == "center":
                text_x = (render_width - text_width) // 2 - left
            elif self.style.align == "right":
                text_x = render_width - text_width - self.style.padding[2] - left
            else:  # left
                text_x = self.style.padding[0] - left
                
            text_y = self.style.padding[1] - top
            
            # Draw text
            draw.text((text_x, text_y), self.text, font=self.style.font, fill=self.style.color)
            
            # Crop to original width if needed
            if render_width > width:
                bitmap = bitmap.crop((0, 0, width, height))
            
            # Cache bitmap
            self._cached_bitmap = bitmap
            return bitmap
        else:
            # Create temporary bitmap with extra space
            render_width = max(width, text_width + 20)  # Add extra space to make alignment visible
            temp_bitmap = Image.new('1', (render_width, height))
            temp_draw = ImageDraw.Draw(temp_bitmap)
            
            # Calculate text position
            if self.style.align == "center":
                text_x = (render_width - text_width) // 2 - left
            elif self.style.align == "right":
                text_x = render_width - text_width - self.style.padding[2] - left
            else:  # left
                text_x = self.style.padding[0] - left
                
            text_y = self.style.padding[1] - top
            
            # Draw text
            temp_draw.text((text_x, text_y), self.text, font=self.style.font, fill=self.style.color)
            
            # Crop and copy to destination
            if render_width > width:
                temp_bitmap = temp_bitmap.crop((0, 0, width, height))
            draw.bitmap((x, y), temp_bitmap, fill=self.style.color)
            return None
            
    def set_text(self, text: str) -> None:
        """Update the text content"""
        if text != self.text:
            self.text = text
            self._cached_size = None  # Invalidate size cache
            self._cached_bitmap = None  # Invalidate bitmap cache
            self._needs_refresh = True
            
    def set_style(self, style: TextStyle) -> None:
        """Update the text style"""
        self.style = style
        self._cached_size = None  # Invalidate size cache
        self._cached_bitmap = None  # Invalidate bitmap cache
        self._needs_refresh = True
            
    def handle_event(self, event: Dict[str, Any]) -> None:
        """Handle incoming events"""
        super().handle_event(event)
        if event['type'] == 'component_update' and 'text' in event['data']:
            self.set_text(event['data']['text'])
        elif event['type'] == 'component_update' and 'style' in event['data']:
            self.set_style(event['data']['style'])
