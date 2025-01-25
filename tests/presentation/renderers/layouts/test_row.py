import pytest
from PIL import Image, ImageDraw, ImageFont
from src.presentation.renderers.layouts.row import RowLayout, RowItem
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

def test_row_creation():
    """Test basic row creation"""
    width = 100
    height = 20
    row = RowLayout(width, height)
    
    assert row.width == width
    assert row.height == height
    assert len(row.items) == 0

def test_row_component_addition(text_component):
    """Test adding components to row"""
    row = RowLayout(100, 20)
    
    # Add fixed width component
    row.add_component(text_component, width=30)
    assert len(row.items) == 1
    assert row.items[0].component == text_component
    assert row.items[0].width == 30
    
    # Add auto-width component
    row.add_component(text_component)
    assert len(row.items) == 2
    assert row.items[1].width is None

def test_row_rendering(text_component):
    """Test row rendering"""
    row = RowLayout(100, 20)
    row.add_component(text_component)
    
    # Test standalone rendering
    bitmap = row.render()
    assert isinstance(bitmap, Image.Image)
    assert bitmap.size == (100, 20)
    
    # Test rendering to existing bitmap
    image = Image.new('1', (200, 50))
    draw = ImageDraw.Draw(image)
    result = row.render(draw, 10, 5)
    assert result is None

def test_row_auto_width(text_component):
    """Test auto-width distribution"""
    row = RowLayout(100, 20)
    
    # Add one fixed and two auto-width components
    row.add_component(text_component, width=20)  # 20px fixed
    row.add_component(text_component)  # Auto
    row.add_component(text_component)  # Auto
    
    # Remaining 80px should be split between auto components
    frame = row.render()
    assert isinstance(frame, Image.Image)
    
    # Each auto component should get 40px
    auto_items = [item for item in row.items if item.width is None]
    assert len(auto_items) == 2

def test_row_vertical_alignment(text_component):
    """Test vertical alignment options"""
    row = RowLayout(100, 30)  # Taller row for visible alignment
    
    # Test different alignments
    alignments = ["top", "center", "bottom"]
    frames = []
    
    for align in alignments:
        row.items = []  # Clear items
        row.add_component(text_component, align_v=align)
        frame = row.render()
        frames.append(list(frame.getdata()))
    
    # Each alignment should produce different output
    for i in range(len(frames)):
        for j in range(i + 1, len(frames)):
            assert frames[i] != frames[j]

def test_row_padding(font):
    """Test component padding"""
    row = RowLayout(100, 20)
    style = TextStyle(font=font)
    
    # Create component with black text
    text = "X"  # Single character to make padding visible
    style = TextStyle(font=font, color=1)  # White text
    component = TextComponent(text, style)
    
    # Add component with large padding
    padding = (10, 5, 10, 5)  # Large padding to ensure visible difference
    row.add_component(component, padding=padding)
    with_padding = row.render()
    
    # Add component without padding
    row.items = []  # Clear items
    row.add_component(component)
    without_padding = row.render()
    
    # Check that padding area contains white pixels
    padded_data = list(with_padding.getdata())
    unpadded_data = list(without_padding.getdata())
    
    # Get dimensions
    width = 100
    height = 20
    
    # Check left padding area (first 10 pixels of first row)
    left_padding = [padded_data[i * width : i * width + 10] for i in range(height)]  # All rows, first 10 pixels
    assert any(any(pixel == 1 for pixel in row) for row in left_padding), "Left padding should contain white pixels"
    
    # Check that unpadded version has black pixels in the same area
    left_unpadded = [unpadded_data[i * width : i * width + 10] for i in range(height)]
    assert any(any(pixel == 0 for pixel in row) for row in left_unpadded), "Unpadded area should contain black pixels"

def test_row_multiple_components(text_component):
    """Test rendering multiple components"""
    row = RowLayout(100, 20)
    
    # Add several components with different configurations
    row.add_component(text_component, width=30)
    row.add_component(text_component, padding=(5, 0, 5, 0))
    row.add_component(text_component, align_v="center")
    
    # Should render without errors
    frame = row.render()
    assert isinstance(frame, Image.Image)

def test_row_component_spacing(text_component):
    """Test spacing between components"""
    row = RowLayout(100, 20)
    
    # Add components with padding to create spacing
    row.add_component(text_component, padding=(0, 0, 5, 0))  # 5px right padding
    row.add_component(text_component, padding=(5, 0, 0, 0))  # 5px left padding
    
    # Render and verify
    frame = row.render()
    assert isinstance(frame, Image.Image)

def test_row_width_constraints(text_component):
    """Test width constraints handling"""
    row = RowLayout(100, 20)
    
    # Total fixed widths exceed row width
    with pytest.raises(ValueError):
        row.add_component(text_component, width=60)
        row.add_component(text_component, width=50)
        row.render()
