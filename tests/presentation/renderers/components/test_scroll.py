import pytest
from PIL import Image, ImageDraw, ImageFont
import time
from src.presentation.renderers.components.text import TextComponent, TextStyle
from src.presentation.renderers.components.scroll import ScrollComponent

@pytest.fixture
def font():
    return ImageFont.load_default()

@pytest.fixture
def text_component(font):
    style = TextStyle(font=font)
    # Use a long text that will definitely need scrolling
    return TextComponent("This is a very long text that will definitely need to scroll in the viewport", style)

def test_scroll_component_creation(text_component):
    """Test basic scroll component creation"""
    width = 100
    height = 20
    component = ScrollComponent(text_component, width, height)
    assert component.viewport_width == width
    assert component.viewport_height == height
    assert component.text_component == text_component
    assert not component.is_scrolling

def test_scroll_component_size(text_component):
    """Test scroll component size"""
    width = 100
    height = 20
    component = ScrollComponent(text_component, width, height)
    
    # Size should match viewport
    assert component.get_size() == (width, height)

def test_scroll_component_render(text_component):
    """Test scroll component rendering"""
    width = 100
    height = 20
    component = ScrollComponent(text_component, width, height)
    
    # Test standalone rendering
    bitmap = component.render()
    assert isinstance(bitmap, Image.Image)
    assert bitmap.size == (width, height)
    
    # Test rendering to existing bitmap
    image = Image.new('1', (200, 50))
    draw = ImageDraw.Draw(image)
    result = component.render(draw, 10, 5)
    assert result is None

def test_scroll_animation(text_component):
    """Test scroll animation states"""
    width = 50
    height = 20
    component = ScrollComponent(text_component, width, height)
    
    # Start scroll in test mode
    component.start_scroll(test_mode=True)
    assert component.is_scrolling
    assert component.scroll_position == 0
    assert component.pause_count == 0
    
    # Update animation
    initial_pos = component.scroll_position
    component.update()
    assert component.scroll_position != initial_pos  # Position should change
    
    # Stop scroll
    component.stop_scroll()
    assert not component.is_scrolling
    
    # Reset
    component.reset()
    assert component.scroll_position == 0
    assert component.pause_count == 0
    assert not component.is_scrolling

def test_scroll_pausing(text_component):
    """Test scroll animation pausing"""
    width = 50
    height = 20
    component = ScrollComponent(text_component, width, height)
    
    # Set custom pause frames
    start_pause = 5
    end_pause = 3
    component.set_pause_frames(start_pause, end_pause)
    
    # Start scroll
    component.start_scroll()
    
    # Should pause at start
    for _ in range(start_pause):
        initial_pos = component.scroll_position
        component.update()
        assert component.scroll_position == initial_pos  # Should not move during pause
        
    # Should scroll after pause
    component.update()
    assert component.scroll_position < 0  # Should start moving

def test_scroll_speed(text_component):
    """Test scroll speed adjustment"""
    width = 50
    height = 20
    component = ScrollComponent(text_component, width, height)
    
    # Set custom speed and start in test mode
    speed = 2
    component.set_scroll_speed(speed)
    component.start_scroll(test_mode=True)
    
    # Update and check position change
    initial_pos = component.scroll_position
    component.update()
    assert component.scroll_position == initial_pos - speed

def test_text_update(text_component):
    """Test updating scroll text"""
    width = 50
    height = 20
    component = ScrollComponent(text_component, width, height)
    
    # Start scrolling
    component.start_scroll()
    assert component.is_scrolling
    
    # Update text
    text_component.set_text("New Text")
    component.update()  # Need to call update to detect text change
    
    # Should reset scroll state
    assert not component.is_scrolling
    assert component.scroll_position == 0
    assert component.pause_count == 0

def test_scroll_completion(text_component):
    """Test scroll animation completion"""
    width = 50
    height = 20
    component = ScrollComponent(text_component, width, height)
    
    # Start scroll
    component.start_scroll()
    
    # Run animation until text reaches end
    text_width = text_component.get_size()[0]
    max_scroll = text_width - width
    
    # Skip start pause
    for _ in range(component.start_pause + 1):
        component.update()
        
    # Run until we reach end
    while -component.scroll_position < max_scroll:
        component.update()
        
    # Should pause at end
    for _ in range(component.end_pause):
        initial_pos = component.scroll_position
        component.update()
        assert component.scroll_position == initial_pos
        
    # Should reset after end pause
    component.update()
    assert not component.is_scrolling
    assert component.scroll_position == 0
    assert component.pause_count == 0

def test_viewport_clearing(text_component):
    """Test viewport clearing between renders"""
    width = 50
    height = 20
    component = ScrollComponent(text_component, width, height)
    
    # Render frame 1
    frame1 = component.render()
    frame1_data = list(frame1.getdata())
    
    # Move text and render frame 2
    component.start_scroll(test_mode=True)
    component.update()
    frame2 = component.render()
    frame2_data = list(frame2.getdata())
    
    # Frames should be different (text moved)
    assert frame1_data != frame2_data
