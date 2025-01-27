from typing import Optional, Tuple, Any, Dict
import logging
from PIL import Image, ImageDraw, ImageFont
from dataclasses import dataclass
from .base_component import BaseComponent
from src.infrastructure.event_bus import EventBus

logger = logging.getLogger(__name__)

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
        logger.debug(f"TextComponent initialized with text: {text}")
        
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
            logger.debug(f"Text size calculated: {self._cached_size} for text: {self.text}")
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
        logger.debug(f"Rendering text: {self.text}")
        # Get text bounds for positioning
        left, top, right, bottom = self.style.font.getbbox(self.text)
        text_width = right - left
        text_height = bottom - top
        logger.debug(f"Text bounds: left={left}, top={top}, right={right}, bottom={bottom}")
        logger.debug(f"Text dimensions: {text_width}x{text_height}")
        
        # Get total size including padding
        width, height = self.get_size()
        
        if draw is None:
            # Return cached bitmap if available and text hasn't changed
            if self._cached_bitmap is not None:
                return self._cached_bitmap
                
            # Create bitmap with black background
            bitmap = Image.new('1', (width, height), 0)  # Black background
            draw = ImageDraw.Draw(bitmap)
            
            # Calculate text position within the bitmap
            if self.style.align == "center":
                text_x = (width - text_width) // 2
                text_y = (height - text_height) // 2
            elif self.style.align == "right":
                text_x = width - text_width - self.style.padding[2]
                text_y = (height - text_height) // 2
            else:  # left
                text_x = self.style.padding[0]
                text_y = (height - text_height) // 2

            # Ensure text is not positioned outside the bitmap
            text_x = max(0, min(text_x, width - text_width))
            text_y = max(0, min(text_y, height - text_height))
                
            logger.debug(f"Drawing text at position: ({text_x}, {text_y})")
            
            # Draw text in white
            draw.text((text_x, text_y), self.text, font=self.style.font, fill=1)  # Always white text
            
            # Cache bitmap
            self._cached_bitmap = bitmap
            logger.debug(f"Created bitmap with size: {bitmap.size}")
            return bitmap
        else:
            # Get destination image size
            dest_width = draw.im.size[0]
            dest_height = draw.im.size[1]
            
            # Calculate text position within the destination image
            if self.style.align == "center":
                text_x = x + (dest_width - text_width) // 2
                text_y = y + (dest_height - text_height) // 2
            elif self.style.align == "right":
                text_x = x + dest_width - text_width - self.style.padding[2]
                text_y = y + (dest_height - text_height) // 2
            else:  # left
                text_x = x + self.style.padding[0]
                text_y = y + (dest_height - text_height) // 2

            # Ensure text is not positioned outside the destination image
            text_x = max(x, min(text_x, x + dest_width - text_width))
            text_y = max(y, min(text_y, y + dest_height - text_height))
                
            logger.debug(f"Drawing text at position: ({text_x}, {text_y})")
            
            # Draw text in white (1)
            draw.text((text_x, text_y), self.text, font=self.style.font, fill=1)
            return None
            
    def set_text(self, text: str) -> None:
        """Update the text content"""
        if text != self.text:
            logger.debug(f"Setting text to: {text}")
            self.text = text
            self._cached_size = None  # Invalidate size cache
            self._cached_bitmap = None  # Invalidate bitmap cache
            self._needs_refresh = True
            
    def set_style(self, style: TextStyle) -> None:
        """Update the text style"""
        logger.debug(f"Setting text style: align={style.align}, color={style.color}, padding={style.padding}")
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
