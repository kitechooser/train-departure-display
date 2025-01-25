import pytest
from PIL import Image, ImageDraw, ImageFont
from src.presentation.renderers.components.text import TextComponent, TextStyle

@pytest.fixture
def font():
    # Use a default system font for testing
    return ImageFont.load_default()

@pytest.fixture
def style(font):
    return TextStyle(font=font)

def test_text_component_creation(style):
    """Test basic text component creation"""
    text = "Test Text"
    component = TextComponent(text, style)
    assert component.text == text
    assert component.style == style

def test_text_component_size(style):
    """Test text component size calculation"""
    component = TextComponent("Test", style)
    width, height = component.get_size()
    assert width > 0
    assert height > 0
    
    # Test with padding
    padded_style = TextStyle(font=style.font, padding=(2, 2, 2, 2))
    padded_component = TextComponent("Test", padded_style)
    width_padded, height_padded = padded_component.get_size()
    assert width_padded == width + 4  # 2px padding on each side
    assert height_padded == height + 4

def test_text_component_render(style):
    """Test text component rendering"""
    component = TextComponent("Test", style)
    width, height = component.get_size()
    
    # Test standalone rendering
    bitmap = component.render()
    assert isinstance(bitmap, Image.Image)
    assert bitmap.size == (width, height)
    
    # Test rendering to existing bitmap
    image = Image.new('1', (100, 20))
    draw = ImageDraw.Draw(image)
    result = component.render(draw, 10, 5)
    assert result is None  # Should return None when drawing to existing bitmap

def test_text_alignment(font):
    """Test text alignment options"""
    text = "Test"
    width = 100
    height = 20
    
    # Test left alignment (default)
    left_style = TextStyle(font=font)
    left = TextComponent(text, left_style)
    left_image = Image.new('1', (width, height))
    left_draw = ImageDraw.Draw(left_image)
    left.render(left_draw, 0, 0)
    
    # Test center alignment
    center_style = TextStyle(font=font, align="center")
    center = TextComponent(text, center_style)
    center_image = Image.new('1', (width, height))
    center_draw = ImageDraw.Draw(center_image)
    center.render(center_draw, 0, 0)
    
    # Test right alignment
    right_style = TextStyle(font=font, align="right")
    right = TextComponent(text, right_style)
    right_image = Image.new('1', (width, height))
    right_draw = ImageDraw.Draw(right_image)
    right.render(right_draw, 0, 0)
    
    # Verify each alignment produces different pixel patterns
    assert list(left_image.getdata()) != list(center_image.getdata())
    assert list(left_image.getdata()) != list(right_image.getdata())
    assert list(center_image.getdata()) != list(right_image.getdata())

def test_text_update(style):
    """Test text content updates"""
    component = TextComponent("Initial", style)
    initial_size = component.get_size()
    
    # Update text
    component.set_text("New Text")
    new_size = component.get_size()
    
    # Size should change with different text
    assert initial_size != new_size
    assert component.text == "New Text"

def test_style_update(font):
    """Test style updates"""
    component = TextComponent("Test", TextStyle(font=font))
    initial_size = component.get_size()
    
    # Update style with padding
    new_style = TextStyle(font=font, padding=(5, 5, 5, 5))
    component.set_style(new_style)
    new_size = component.get_size()
    
    # Size should include padding
    assert new_size[0] == initial_size[0] + 10  # 5px padding on each side
    assert new_size[1] == initial_size[1] + 10
    assert component.style == new_style

def test_cache_invalidation(style):
    """Test cache invalidation on updates"""
    component = TextComponent("Test", style)
    
    # Get initial cached values
    initial_size = component.get_size()
    initial_bitmap = component.render()
    
    # Update text
    component.set_text("New Text")
    
    # Cache should be invalidated
    assert component._cached_size is None
    assert component._cached_bitmap is None
    
    # New values should be different
    new_size = component.get_size()
    new_bitmap = component.render()
    assert initial_size != new_size
    assert list(initial_bitmap.getdata()) != list(new_bitmap.getdata())
