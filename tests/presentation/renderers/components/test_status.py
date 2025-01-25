import pytest
from PIL import Image, ImageDraw, ImageFont
import time
from src.presentation.renderers.components.text import TextComponent, TextStyle
from src.presentation.renderers.components.status import StatusComponent

@pytest.fixture
def font():
    return ImageFont.load_default()

@pytest.fixture
def style(font):
    return TextStyle(font=font)

@pytest.fixture
def status_component(style):
    # Use a smaller viewport width to ensure text needs scrolling
    return StatusComponent(50, 20, style)

def test_status_component_creation(status_component):
    """Test basic status component creation"""
    assert status_component.viewport_width == 50
    assert status_component.viewport_height == 20
    assert not status_component.is_showing
    assert not status_component.is_elevated

def test_status_component_size(status_component):
    """Test status component size"""
    width, height = status_component.get_size()
    assert width == 50
    assert height == 20

def test_status_component_render(status_component):
    """Test status component rendering"""
    # Test standalone rendering
    bitmap = status_component.render()
    assert isinstance(bitmap, Image.Image)
    assert bitmap.size == (50, 20)
    
    # Test rendering to existing bitmap
    image = Image.new('1', (200, 50))
    draw = ImageDraw.Draw(image)
    result = status_component.render(draw, 10, 5)
    assert result is None

def test_status_display(status_component):
    """Test status message display"""
    # Show status
    # Use long text to ensure scrolling
    status_component.show_status("This is a very long test status message that will definitely need to scroll", 2.0, test_mode=True)
    assert status_component.is_showing
    assert not status_component.is_elevated
    assert status_component.pixels_up == 0
    
    # Update animation
    status_component.update()
    assert status_component.pixels_up > 0  # Should start elevating
    
    # Hide status
    status_component.hide_status()
    assert not status_component.is_showing

def test_status_elevation(status_component):
    """Test status elevation animation"""
    # Use long text to ensure scrolling
    status_component.show_status("This is a very long test status message that will definitely need to scroll", 2.0, test_mode=True)
    
    # Run elevation animation
    while not status_component.is_elevated:
        initial_pixels = status_component.pixels_up
        status_component.update()
        if status_component.pixels_up < status_component.viewport_height:
            assert status_component.pixels_up > initial_pixels  # Should move up
            
    # Should pause after elevation
    for _ in range(status_component.elevation_pause):
        status_component.update()
        assert status_component.is_elevated  # Should stay elevated during pause

def test_status_duration(status_component):
    """Test status display duration"""
    duration = 0.1  # Short duration for testing
    status_component.show_status("Test Status", duration)
    
    # Wait for duration
    time.sleep(duration + 0.05)  # Add small buffer
    status_component.update()
    
    # Should auto-hide after duration
    assert not status_component.is_showing

def test_status_scroll(status_component):
    """Test status scrolling after elevation"""
    status_component.show_status("This is a very long test status message that will definitely need to scroll in the viewport", 2.0, test_mode=True)
    
    # Run until elevated
    while not status_component.is_elevated:
        status_component.update()
    
    # Run pause frames
    for _ in range(status_component.elevation_pause):
        status_component.update()
        
    # Should start scrolling
    status_component.scroll_component.set_scroll_speed(1)  # Ensure scroll speed is set
    status_component.scroll_component.start_scroll(test_mode=True)  # Restart scroll in test mode
    initial_scroll = status_component.scroll_component.scroll_position
    status_component.update()
    assert status_component.scroll_component.scroll_position < initial_scroll

def test_status_style_update(style, status_component):
    """Test style updates"""
    new_style = TextStyle(font=style.font, color="red")
    status_component.set_style(new_style)
    assert status_component.style == new_style
    assert status_component.text_component.style == new_style

def test_animation_speed_update(status_component):
    """Test animation speed adjustments"""
    # Set custom speeds
    status_component.set_elevation_speed(2)
    status_component.set_scroll_speed(3)
    
    # Show status
    status_component.show_status("This is a very long test status message that will definitely need to scroll in the viewport", 2.0, test_mode=True)
    
    # Check elevation speed
    initial_pixels = status_component.pixels_up
    status_component.update()
    assert status_component.pixels_up == initial_pixels + 2
    
    # Run until scrolling
    while not status_component.is_elevated:
        status_component.update()
    for _ in range(status_component.elevation_pause):
        status_component.update()
        
    # Check scroll speed
    status_component.scroll_component.set_scroll_speed(3)  # Set scroll speed after elevation
    status_component.scroll_component.start_scroll(test_mode=True)  # Restart scroll in test mode
    initial_scroll = status_component.scroll_component.scroll_position
    status_component.update()
    assert status_component.scroll_component.scroll_position == initial_scroll - 3

def test_pause_frames_update(status_component):
    """Test pause frame adjustments"""
    status_component.set_pause_frames(5, 10, 3)  # elevation, scroll start, scroll end
    assert status_component.elevation_pause == 5
    
    # Show status and run until elevated
    status_component.show_status("Test Status", 2.0)
    while not status_component.is_elevated:
        status_component.update()
        
    # Should pause for specified frames
    for _ in range(5):
        initial_scroll = status_component.scroll_component.scroll_position
        status_component.update()
        assert status_component.scroll_component.scroll_position == initial_scroll
