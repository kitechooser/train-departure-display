import pytest
from PIL import Image, ImageDraw, ImageFont
from src.presentation.renderers.layouts.grid import GridLayout, GridCell
from src.presentation.renderers.components.text import TextComponent, TextStyle

@pytest.fixture
def font():
    return ImageFont.load_default()

@pytest.fixture
def style(font):
    return TextStyle(font=font)

@pytest.fixture
def text_component(style):
    return TextComponent("Test", style)

def test_grid_creation():
    """Test basic grid creation"""
    width = 100
    height = 60
    rows = 3
    cols = 2
    grid = GridLayout(width, height, rows, cols)
    
    assert grid.width == width
    assert grid.height == height
    assert grid.rows == rows
    assert grid.cols == cols
    assert grid.cell_width == width // cols
    assert grid.cell_height == height // rows
    assert len(grid.cells) == 0

def test_grid_component_addition(text_component):
    """Test adding components to grid"""
    grid = GridLayout(100, 60, 3, 2)
    
    # Add component
    grid.add_component(text_component, row=0, col=0)
    assert len(grid.cells) == 1
    assert grid.cells[0].component == text_component
    assert grid.cells[0].row == 0
    assert grid.cells[0].col == 0
    
    # Add component with span
    grid.add_component(text_component, row=1, col=0, row_span=2, col_span=2)
    assert len(grid.cells) == 2
    assert grid.cells[1].row_span == 2
    assert grid.cells[1].col_span == 2

def test_grid_bounds_checking(text_component):
    """Test grid bounds validation"""
    grid = GridLayout(100, 60, 2, 2)
    
    # Test row out of bounds
    with pytest.raises(ValueError):
        grid.add_component(text_component, row=2, col=0)
        
    # Test column out of bounds
    with pytest.raises(ValueError):
        grid.add_component(text_component, row=0, col=2)
        
    # Test span out of bounds
    with pytest.raises(ValueError):
        grid.add_component(text_component, row=0, col=0, row_span=3)

def test_grid_overlap_checking(text_component):
    """Test grid overlap validation"""
    grid = GridLayout(100, 60, 2, 2)
    
    # Add first component
    grid.add_component(text_component, row=0, col=0)
    
    # Test overlapping component
    with pytest.raises(ValueError):
        grid.add_component(text_component, row=0, col=0)
        
    # Test overlapping span
    with pytest.raises(ValueError):
        grid.add_component(text_component, row=0, col=1, col_span=2)

def test_grid_rendering(text_component):
    """Test grid rendering"""
    grid = GridLayout(100, 60, 2, 2)
    grid.add_component(text_component, row=0, col=0)
    
    # Test standalone rendering
    bitmap = grid.render()
    assert isinstance(bitmap, Image.Image)
    assert bitmap.size == (100, 60)
    
    # Test rendering to existing bitmap
    image = Image.new('1', (200, 100))
    draw = ImageDraw.Draw(image)
    result = grid.render(draw, 10, 5)
    assert result is None

def test_grid_alignment(font):
    """Test component alignment in cells"""
    grid = GridLayout(100, 60, 2, 2)
    style = TextStyle(font=font)
    
    # Create components with different text for each alignment
    components = [
        TextComponent("Left Top Text", style),
        TextComponent("Center Text Here", style),
        TextComponent("Right Bottom", style)
    ]
    
    alignments = [
        ("left", "top"),
        ("center", "center"),
        ("right", "bottom")
    ]
    
    # Add each component with different alignment
    for i, ((align_h, align_v), component) in enumerate(zip(alignments, components)):
        grid.add_component(
            component,
            row=i // 2,
            col=i % 2,
            align_h=align_h,
            align_v=align_v
        )
        
    # Each alignment should produce different output
    frame = grid.render()
    frame_data = list(frame.getdata())
    
    # Create grid with different alignment
    grid2 = GridLayout(100, 60, 2, 2)
    for i, component in enumerate(components):
        grid2.add_component(
            component,
            row=i // 2,
            col=i % 2
        )
    frame2 = grid2.render()
    frame2_data = list(frame2.getdata())
    
    # Frames should be different
    assert frame_data != frame2_data

def test_grid_padding(font):
    """Test cell padding"""
    grid = GridLayout(100, 60, 2, 2)
    style = TextStyle(font=font)
    
    # Create component with black text
    text = "X"  # Single character to make padding visible
    style = TextStyle(font=font, color=1)  # White text
    component = TextComponent(text, style)
    
    # Add component with padding
    padding = (10, 10, 10, 10)  # Large padding to ensure visible difference
    grid.add_component(
        component,
        row=0,
        col=0,
        padding=padding
    )
    
    # Render with and without padding
    with_padding = grid.render()
    
    grid.cells = []  # Clear cells
    grid.add_component(
        component,
        row=0,
        col=0,
        padding=(0, 0, 0, 0)
    )
    without_padding = grid.render()
    
    # Check that padding area contains white pixels
    padded_data = list(with_padding.getdata())
    unpadded_data = list(without_padding.getdata())
    
    # Get dimensions
    width = 100
    height = 60
    
    # Check left padding area (first 10 pixels of first cell)
    cell_width = width // 2  # Grid is 2x2
    left_padding = [padded_data[i * width : i * width + 10] for i in range(10)]  # First 10 rows, first 10 pixels
    assert any(any(pixel == 1 for pixel in row) for row in left_padding), "Left padding should contain white pixels"
    
    # Check that unpadded version has black pixels in the same area
    left_unpadded = [unpadded_data[i * width : i * width + 10] for i in range(10)]
    assert any(any(pixel == 0 for pixel in row) for row in left_unpadded), "Unpadded area should contain black pixels"

def test_grid_spanning(font):
    """Test cell spanning"""
    grid = GridLayout(100, 60, 2, 2)
    style = TextStyle(font=font)
    
    # Create component with long text and white color
    text = "This is a very long text that will span multiple cells in the grid layout"
    style = TextStyle(font=font, color=1)  # White text
    component = TextComponent(text, style)
    
    # Add spanning component
    grid.add_component(
        component,
        row=0,
        col=0,
        row_span=2,
        col_span=2
    )
    
    # Component should fill entire grid
    frame = grid.render()
    
    # Add non-spanning component to new grid
    single_grid = GridLayout(100, 60, 2, 2)
    single_grid.add_component(
        component,
        row=0,
        col=0
    )
    single_frame = single_grid.render()
    
    # Frames should be different
    assert list(frame.getdata()) != list(single_frame.getdata())
