from typing import List, Tuple, Optional, Protocol, Any
from PIL import Image, ImageDraw
from dataclasses import dataclass

class Renderable(Protocol):
    """Protocol for renderable components"""
    def get_size(self) -> Tuple[int, int]: ...
    def render(self, draw: Optional[ImageDraw.ImageDraw], x: int, y: int) -> Optional[Image.Image]: ...

@dataclass
class RowItem:
    """An item in the row layout"""
    component: Renderable
    width: Optional[int] = None  # Fixed width or None for auto
    padding: Tuple[int, int, int, int] = (0, 0, 0, 0)  # left, top, right, bottom
    align_v: str = "top"  # top, center, bottom

class RowLayout:
    """Row-based layout manager"""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.items: List[RowItem] = []
        
        # Create layout bitmap
        self.layout = Image.new('1', (width, height))
        self.layout_draw = ImageDraw.Draw(self.layout)
        
    def add_component(self, component: Renderable, width: Optional[int] = None,
                     padding: Tuple[int, int, int, int] = (0, 0, 0, 0),
                     align_v: str = "top") -> None:
        """Add a component to the row
        
        Args:
            component: The component to add
            width: Fixed width or None for auto-width
            padding: Item padding (left, top, right, bottom)
            align_v: Vertical alignment ("top", "center", "bottom")
        """
        # Check if adding this component would exceed row width
        if width is not None:
            total_width = sum(item.width + item.padding[0] + item.padding[2] 
                            for item in self.items if item.width is not None)
            total_width += width + padding[0] + padding[2]
            if total_width > self.width:
                raise ValueError("Total fixed widths exceed row width")
                
        self.items.append(RowItem(
            component=component,
            width=width,
            padding=padding,
            align_v=align_v
        ))
        
    def render(self, draw: Optional[ImageDraw.ImageDraw] = None, x: int = 0, y: int = 0) -> Optional[Image.Image]:
        """Render the row layout
        
        Args:
            draw: Optional ImageDraw object to draw on. If None, returns the layout bitmap.
            x: X coordinate to draw at
            y: Y coordinate to draw at
            
        Returns:
            If draw is None, returns the layout bitmap. Otherwise returns None.
        """
        # Clear layout
        self.layout_draw.rectangle(
            [0, 0, self.width - 1, self.height - 1],
            fill=0  # Black background
        )
        
        # Calculate widths for auto-width items
        fixed_width = sum(item.width + item.padding[0] + item.padding[2] 
                         for item in self.items if item.width is not None)
        auto_items = [item for item in self.items if item.width is None]
        
        if auto_items:
            remaining_width = self.width - fixed_width
            auto_width = remaining_width // len(auto_items)
            
        # Render each item
        current_x = x
        for item in self.items:
            # Get item width
            if item.width is not None:
                item_width = item.width
            else:
                item_width = auto_width
                
            # Create item bitmap
            item_bitmap = Image.new('1', (item_width, self.height))
            item_draw = ImageDraw.Draw(item_bitmap)
            
            # Clear item background
            item_draw.rectangle(
                [0, 0, item_width - 1, self.height - 1],
                fill=0  # Black background
            )
            
            # Draw padding area in white to make it visible
            if any(p > 0 for p in item.padding):
                # Draw padding area as filled white rectangle
                if item.padding[0] > 0:  # Left padding
                    item_draw.rectangle(
                        [0, 0, item.padding[0], self.height - 1],
                        fill=1  # White padding
                    )
                if item.padding[2] > 0:  # Right padding
                    item_draw.rectangle(
                        [item_width - item.padding[2] - 1, 0, item_width - 1, self.height - 1],
                        fill=1  # White padding
                    )
                if item.padding[1] > 0:  # Top padding
                    item_draw.rectangle(
                        [0, 0, item_width - 1, item.padding[1]],
                        fill=1  # White padding
                    )
                if item.padding[3] > 0:  # Bottom padding
                    item_draw.rectangle(
                        [0, self.height - item.padding[3] - 1, item_width - 1, self.height - 1],
                        fill=1  # White padding
                    )
            
            # Create padded area
            padded_width = item_width - (item.padding[0] + item.padding[2])
            padded_height = self.height - (item.padding[1] + item.padding[3])
            
            # Get component size
            comp_width, comp_height = item.component.get_size()
            
            # Calculate position within padded area
            base_x = item.padding[0]  # Row items are always left-aligned
            
            if item.align_v == "center":
                base_y = item.padding[1] + (padded_height - comp_height) // 2
            elif item.align_v == "bottom":
                base_y = self.height - comp_height - item.padding[3]
            else:  # top
                base_y = item.padding[1]
                
            # Render component directly into item
            item.component.render(item_draw, base_x, base_y)
            
            # Copy item to layout
            self.layout_draw.bitmap((current_x, y), item_bitmap, fill=1)
            
            # Move to next position
            current_x += item_width
            
        if draw is None:
            return self.layout
        else:
            # Copy layout to destination
            draw.bitmap((x, y), self.layout, fill=1)  # White foreground
            return None
