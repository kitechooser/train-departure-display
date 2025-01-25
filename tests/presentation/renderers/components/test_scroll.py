import pytest
from PIL import Image, ImageDraw, ImageFont
from unittest.mock import Mock
from src.presentation.renderers.components.scroll import ScrollComponent
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
    return ImageFont.load_default()

@pytest.fixture
def text_component(font):
    style = TextStyle(font=font)
    # Use a long text that will need scrolling in a 100px viewport
    return TextComponent("This is a very long text that will definitely need to scroll in the viewport", style)

@pytest.fixture
def scroll_component(text_component, event_bus):
    return ScrollComponent(text_component, 100, 20, event_bus)

def test_scroll_component_creation(scroll_component):
    """Test basic scroll component creation"""
    assert scroll_component.viewport_width == 100
    assert scroll_component.viewport_height == 20
    assert scroll_component.event_bus is not None
    assert scroll_component._needs_refresh is True

def test_scroll_component_size(scroll_component):
    """Test scroll component size"""
    width, height = scroll_component.get_size()
    assert width == 100
    assert height == 20

def test_scroll_component_render(scroll_component):
    """Test scroll component rendering"""
    # Test standalone rendering
    bitmap = scroll_component.render()
    assert isinstance(bitmap, Image.Image)
    assert bitmap.size == (100, 20)
    
    # Test rendering to existing bitmap
    image = Image.new('1', (200, 100))
    draw = ImageDraw.Draw(image)
    result = scroll_component.render(draw, 10, 5)
    assert result is None

def test_scroll_animation_control(scroll_component):
    """Test scroll animation controls"""
    # Start scrolling
    scroll_component.start_scroll()
    assert scroll_component.is_scrolling is True
    assert scroll_component.scroll_position == 0
    
    # Stop scrolling
    scroll_component.stop_scroll()
    assert scroll_component.is_scrolling is False
    assert scroll_component.scroll_position == 0
    
    # Reset
    scroll_component.reset()
    assert scroll_component.is_scrolling is False
    assert scroll_component.scroll_position == 0
    assert scroll_component.pause_count == 0

def test_scroll_update(scroll_component):
    """Test scroll animation update"""
    # Verify text needs scrolling
    assert scroll_component._needs_scroll() is True
    
    # Start scrolling in test mode
    scroll_component.start_scroll(test_mode=True)
    initial_pos = scroll_component.scroll_position
    
    # Update should change position in test mode
    scroll_component.update()
    assert scroll_component.scroll_position < initial_pos  # Should move left

def test_text_update(scroll_component):
    """Test text content updates"""
    scroll_component.start_scroll()
    scroll_component.set_text("New Text")
    assert scroll_component.text_component.text == "New Text"
    assert scroll_component.is_scrolling is False
    assert scroll_component._needs_refresh is True

def test_style_update(scroll_component, font):
    """Test style updates"""
    new_style = TextStyle(font=font, padding=(5, 5, 5, 5))
    scroll_component.set_style(new_style)
    assert scroll_component.text_component.style == new_style
    assert scroll_component.is_scrolling is False
    assert scroll_component._needs_refresh is True

def test_scroll_speed_update(scroll_component):
    """Test scroll speed updates"""
    scroll_component.set_scroll_speed(2)
    assert scroll_component.scroll_speed == 2
    assert scroll_component._needs_refresh is True

def test_pause_frames_update(scroll_component):
    """Test pause frames updates"""
    scroll_component.set_pause_frames(30, 10)
    assert scroll_component.start_pause == 30
    assert scroll_component.end_pause == 10
    assert scroll_component._needs_refresh is True

def test_scroll_event_handling(scroll_component):
    """Test event handling"""
    # Test text update event
    event = {
        'type': 'component_update',
        'data': {'text': 'Updated Text'}
    }
    scroll_component.handle_event(event)
    assert scroll_component.text_component.text == "Updated Text"
    assert scroll_component._needs_refresh is True
    
    # Test scroll speed update event
    event = {
        'type': 'component_update',
        'data': {'scroll_speed': 3}
    }
    scroll_component.handle_event(event)
    assert scroll_component.scroll_speed == 3
    assert scroll_component._needs_refresh is True
    
    # Test pause frames update event
    event = {
        'type': 'component_update',
        'data': {
            'pause_frames': {
                'start': 40,
                'end': 15
            }
        }
    }
    scroll_component.handle_event(event)
    assert scroll_component.start_pause == 40
    assert scroll_component.end_pause == 15
    assert scroll_component._needs_refresh is True

def test_scroll_event_subscription(scroll_component, event_bus):
    """Test event subscription"""
    scroll_component.subscribe_to_events()
    assert event_bus.subscribe.call_count == 2  # component_update and component_clear

def test_scroll_cleanup(scroll_component, event_bus):
    """Test cleanup"""
    scroll_component.cleanup()
    assert event_bus.unsubscribe.call_count == 2  # component_update and component_clear

def test_scroll_without_event_bus(text_component):
    """Test component creation without event bus"""
    component = ScrollComponent(text_component, 100, 20)
    assert component.event_bus is None
    # Should not raise any exceptions
    component.subscribe_to_events()
    component.cleanup()
