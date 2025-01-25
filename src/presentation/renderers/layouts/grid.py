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
        # Clear layout
        self.layout_draw.rectangle(
            [0, 0, self.width - 1, self.height - 1],
            fill=0  # Black background
        )
        
        # Render each cell
        for cell in self.cells:
            # Calculate cell bounds
            cell_x = x + (cell.col * self.cell_width)
            cell_y = y + (cell.row * self.cell_height)
            cell_width = cell.col_span * self.cell_width
            cell_height = cell.row_span * self.cell_height
            
            # Create cell bitmap
            cell_bitmap = Image.new('1', (cell_width, cell_height))
            cell_draw = ImageDraw.Draw(cell_bitmap)
            
            # Clear cell background
            cell_draw.rectangle(
                [0, 0, cell_width - 1, cell_height - 1],
                fill=0  # Black background
            )
            
            # Draw padding area in white to make it visible
            if any(p > 0 for p in cell.padding):
                # Draw padding area as filled white rectangle
                if cell.padding[0] > 0:  # Left padding
                    cell_draw.rectangle(
                        [0, 0, cell.padding[0], cell_height - 1],
                        fill=1  # White padding
                    )
                if cell.padding[2] > 0:  # Right padding
                    cell_draw.rectangle(
                        [cell_width - cell.padding[2] - 1, 0, cell_width - 1, cell_height - 1],
                        fill=1  # White padding
                    )
                if cell.padding[1] > 0:  # Top padding
                    cell_draw.rectangle(
                        [0, 0, cell_width - 1, cell.padding[1]],
                        fill=1  # White padding
                    )
                if cell.padding[3] > 0:  # Bottom padding
                    cell_draw.rectangle(
                        [0, cell_height - cell.padding[3] - 1, cell_width - 1, cell_height - 1],
                        fill=1  # White padding
                    )
            
            # Create padded area
            padded_width = cell_width - (cell.padding[0] + cell.padding[2])
            padded_height = cell_height - (cell.padding[1] + cell.padding[3])
            
            # Get component size
            comp_width, comp_height = cell.component.get_size()
            
            # Calculate position within padded area
            if cell.align_h == "center":
                base_x = cell.padding[0] + (padded_width - comp_width) // 2
            elif cell.align_h == "right":
                base_x = cell_width - comp_width - cell.padding[2]
            else:  # left
                base_x = cell.padding[0]
                
            if cell.align_v == "center":
                base_y = cell.padding[1] + (padded_height - comp_height) // 2
            elif cell.align_v == "bottom":
                base_y = cell_height - comp_height - cell.padding[3]
            else:  # top
                base_y = cell.padding[1]
                
            # Render component directly into cell
            cell.component.render(cell_draw, base_x, base_y)
            
            # Copy cell to layout
            self.layout_draw.bitmap((cell_x, cell_y), cell_bitmap, fill=1)
            
        if draw is None:
            return self.layout
        else:
            # Copy layout to destination
            draw.bitmap((x, y), self.layout, fill=1)  # White foreground
            return None
