import pytest
from PIL import Image, ImageDraw, ImageFont
from unittest.mock import Mock
from src.presentation.renderers.components.text import TextComponent, TextStyle
from src.infrastructure.event_bus import EventBus

@pytest.fixture
def event_bus():
    mock_bus = Mock(spec=EventBus)
    mock_bus.subscribe = Mock()
    mock_bus.unsubscribe = Mock()
    return mock_bus

@pytest.fixture
def font():
    # Use a default system font for testing
    return ImageFont.load_default()

@pytest.fixture
def style(font):
    return TextStyle(font=font)

def test_text_component_creation(style, event_bus):
    """Test basic text component creation"""
    text = "Test Text"
    component = TextComponent(text, style, event_bus)
    assert component.text == text
    assert component.style == style
    assert component.event_bus is not None

def test_text_component_size(style, event_bus):
    """Test text component size calculation"""
    component = TextComponent("Test", style, event_bus)
    width, height = component.get_size()
    assert width > 0
    assert height > 0
    
    # Test with padding
    padded_style = TextStyle(font=style.font, padding=(2, 2, 2, 2))
    padded_component = TextComponent("Test", padded_style, event_bus)
    width_padded, height_padded = padded_component.get_size()
    assert width_padded == width + 4  # 2px padding on each side
    assert height_padded == height + 4

def test_text_component_render(style, event_bus):
    """Test text component rendering"""
    component = TextComponent("Test", style, event_bus)
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

def test_text_alignment(font, event_bus):
    """Test text alignment options"""
    text = "Test"
    width = 100
    height = 20
    
    # Test left alignment (default)
    left_style = TextStyle(font=font)
    left = TextComponent(text, left_style, event_bus)
    left_image = Image.new('1', (width, height))
    left_draw = ImageDraw.Draw(left_image)
    left.render(left_draw, 0, 0)
    
    # Test center alignment
    center_style = TextStyle(font=font, align="center")
    center = TextComponent(text, center_style, event_bus)
    center_image = Image.new('1', (width, height))
    center_draw = ImageDraw.Draw(center_image)
    center.render(center_draw, 0, 0)
    
    # Test right alignment
    right_style = TextStyle(font=font, align="right")
    right = TextComponent(text, right_style, event_bus)
    right_image = Image.new('1', (width, height))
    right_draw = ImageDraw.Draw(right_image)
    right.render(right_draw, 0, 0)
    
    # Verify each alignment produces different pixel patterns
    assert list(left_image.getdata()) != list(center_image.getdata())
    assert list(left_image.getdata()) != list(right_image.getdata())
    assert list(center_image.getdata()) != list(right_image.getdata())

def test_text_update(style, event_bus):
    """Test text content updates"""
    component = TextComponent("Initial", style, event_bus)
    initial_size = component.get_size()
    
    # Update text
    component.set_text("New Text")
    new_size = component.get_size()
    
    # Size should change with different text
    assert initial_size != new_size
    assert component.text == "New Text"
    assert component._needs_refresh is True

def test_style_update(font, event_bus):
    """Test style updates"""
    component = TextComponent("Test", TextStyle(font=font), event_bus)
    initial_size = component.get_size()
    
    # Update style with padding
    new_style = TextStyle(font=font, padding=(5, 5, 5, 5))
    component.set_style(new_style)
    new_size = component.get_size()
    
    # Size should include padding
    assert new_size[0] == initial_size[0] + 10  # 5px padding on each side
    assert new_size[1] == initial_size[1] + 10
    assert component.style == new_style
    assert component._needs_refresh is True

def test_cache_invalidation(style, event_bus):
    """Test cache invalidation on updates"""
    component = TextComponent("Test", style, event_bus)
    
    # Get initial cached values
    initial_size = component.get_size()
    initial_bitmap = component.render()
    
    # Update text
    component.set_text("New Text")
    
    # Cache should be invalidated
    assert component._cached_size is None
    assert component._cached_bitmap is None
    assert component._needs_refresh is True
    
    # New values should be different
    new_size = component.get_size()
    new_bitmap = component.render()
    assert initial_size != new_size
    assert list(initial_bitmap.getdata()) != list(new_bitmap.getdata())

def test_text_event_handling(style, event_bus):
    """Test event handling"""
    component = TextComponent("Initial", style, event_bus)
    
    # Test text update event
    event = {
        'type': 'component_update',
        'data': {'text': 'Updated Text'}
    }
    component.handle_event(event)
    assert component.text == "Updated Text"
    assert component._needs_refresh is True
    
    # Test style update event
    new_style = TextStyle(font=style.font, padding=(5, 5, 5, 5))
    event = {
        'type': 'component_update',
        'data': {'style': new_style}
    }
    component.handle_event(event)
    assert component.style == new_style
    assert component._needs_refresh is True

def test_text_event_subscription(style, event_bus):
    """Test event subscription"""
    component = TextComponent("Test", style, event_bus)
    component.subscribe_to_events()
    assert event_bus.subscribe.call_count == 2  # component_update and component_clear

def test_text_cleanup(style, event_bus):
    """Test cleanup"""
    component = TextComponent("Test", style, event_bus)
    component.cleanup()
    assert event_bus.unsubscribe.call_count == 2  # component_update and component_clear

def test_text_without_event_bus(style):
    """Test component creation without event bus"""
    component = TextComponent("Test", style)
    assert component.event_bus is None
    # Should not raise any exceptions
    component.subscribe_to_events()
    component.cleanup()
