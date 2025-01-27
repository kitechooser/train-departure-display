from typing import List, Tuple, Optional, Protocol, Any
from PIL import Image, ImageDraw
from dataclasses import dataclass

class Renderable(Protocol):
    """Protocol for renderable components"""
    def get_size(self) -> Tuple[int, int]: ...
    def render(self, draw: Optional[ImageDraw.ImageDraw], x: int, y: int) -> Optional[Image.Image]: ...

@dataclass
class GridCell:
    """A cell in the grid layout"""
    component: Renderable
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1
    padding: Tuple[int, int, int, int] = (0, 0, 0, 0)  # left, top, right, bottom
    align_h: str = "left"  # left, center, right
    align_v: str = "top"   # top, center, bottom

class GridLayout:
    """Grid-based layout manager"""
    
    def __init__(self, width: int, height: int, rows: int, cols: int):
        self.width = width
        self.height = height
        self.rows = rows
        self.cols = cols
        self.cells: List[GridCell] = []
        
        # Calculate cell dimensions
        self.cell_width = width // cols
        self.cell_height = height // rows
        
        # Create layout bitmap
        self.layout = Image.new('1', (width, height))
        self.layout_draw = ImageDraw.Draw(self.layout)
        
    def clear(self) -> None:
        """Clear all components from the grid"""
        self.cells = []
        
    def add_component(self, component: Renderable, row: int, col: int, 
                     row_span: int = 1, col_span: int = 1,
                     padding: Tuple[int, int, int, int] = (0, 0, 0, 0),
                     align_h: str = "left", align_v: str = "top") -> None:
        """Add a component to the grid
        
        Args:
            component: The component to add
            row: Row index (0-based)
            col: Column index (0-based)
            row_span: Number of rows to span
            col_span: Number of columns to span
            padding: Cell padding (left, top, right, bottom)
            align_h: Horizontal alignment ("left", "center", "right")
            align_v: Vertical alignment ("top", "center", "bottom")
        """
        if row + row_span > self.rows or col + col_span > self.cols:
            raise ValueError("Component placement exceeds grid bounds")
            
        # Check for overlapping cells
        for cell in self.cells:
            if (row < cell.row + cell.row_span and 
                row + row_span > cell.row and
                col < cell.col + cell.col_span and
                col + col_span > cell.col):
                raise ValueError("Component placement overlaps existing cell")
                
        self.cells.append(GridCell(
            component=component,
            row=row,
            col=col,
            row_span=row_span,
            col_span=col_span,
            padding=padding,
            align_h=align_h,
            align_v=align_v
        ))
        
    def render(self, draw: Optional[ImageDraw.ImageDraw] = None, x: int = 0, y: int = 0) -> Optional[Image.Image]:
        """Render the grid layout
        
        Args:
            draw: Optional ImageDraw object to draw on. If None, returns the layout bitmap.
            x: X coordinate to draw at
            y: Y coordinate to draw at
            
        Returns:
            If draw is None, returns the layout bitmap. Otherwise returns None.
        """
        # Create new layout with black background
        self.layout = Image.new('1', (self.width, self.height), 0)
        self.layout_draw = ImageDraw.Draw(self.layout)
        
        # Render each cell
        for cell in self.cells:
            # Calculate cell bounds
            cell_x = (cell.col * self.cell_width)
            cell_y = (cell.row * self.cell_height)
            cell_width = cell.col_span * self.cell_width
            cell_height = cell.row_span * self.cell_height
            
            # Create content bitmap (size of available space minus padding)
            content_width = cell_width - (cell.padding[0] + cell.padding[2])
            content_height = cell_height - (cell.padding[1] + cell.padding[3])
            content_bitmap = Image.new('1', (content_width, content_height), 0)  # Black background
            content_draw = ImageDraw.Draw(content_bitmap)
            
            # Create white background for text area
            text_width, text_height = cell.component.get_size()
            text_x = (content_width - text_width) // 2 if cell.align_h == "center" else 0
            text_y = (content_height - text_height) // 2 if cell.align_v == "center" else 0
            content_draw.rectangle([text_x, text_y, text_x + text_width, text_y + text_height], fill=1)  # White background
            
            # Get component size
            comp_width, comp_height = cell.component.get_size()
            
            # Calculate position within content area
            if cell.align_h == "center":
                content_x = (content_width - comp_width) // 2
            elif cell.align_h == "right":
                content_x = content_width - comp_width
            else:  # left
                content_x = 0

            if cell.align_v == "center":
                content_y = (content_height - comp_height) // 2
            elif cell.align_v == "bottom":
                content_y = content_height - comp_height
            else:  # top
                content_y = 0
                
            # Render component into content bitmap
            cell.component.render(content_draw, content_x, content_y)
            
            # Create cell bitmap and mask (full size including padding) with black background
            cell_bitmap = Image.new('1', (cell_width, cell_height), 0)
            cell_mask = Image.new('1', (cell_width, cell_height), 0)
            
            # Paste content bitmap directly into cell bitmap at padding offset
            cell_bitmap.paste(content_bitmap, (cell.padding[0], cell.padding[1]))
            
            # Paste cell bitmap directly into layout
            self.layout.paste(cell_bitmap, (cell_x, cell_y))
            
        if draw is None:
            return self.layout
        else:
            # Copy layout to destination
            draw.bitmap((x, y), self.layout, fill=1)  # White foreground
            return None
