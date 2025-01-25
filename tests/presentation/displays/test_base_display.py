import pytest
from PIL import Image, ImageDraw
from unittest.mock import Mock, patch
from src.presentation.displays.base_display import BaseDisplay
from src.infrastructure.event_bus import EventBus

class TestDisplay(BaseDisplay):
    """Test implementation of BaseDisplay"""
    def __init__(self, width: int, height: int, event_bus: EventBus = None):
        super().__init__(width, height, event_bus)
        
    def render(self) -> Image.Image:
        """Test render implementation"""
        image = Image.new('1', (self.width, self.height))
        draw = ImageDraw.Draw(image)
        draw.rectangle([0, 0, self.width-1, self.height-1], fill=1)
        return image

@pytest.fixture
def event_bus():
    mock_bus = Mock(spec=EventBus)
    # Add required methods to mock
    mock_bus.subscribe = Mock()
    mock_bus.unsubscribe = Mock()
    return mock_bus

@pytest.fixture
def display(event_bus):
    return TestDisplay(100, 60, event_bus)

def test_display_creation(display):
    """Test basic display creation"""
    assert display.width == 100
    assert display.height == 60
    assert display.event_bus is not None

def test_display_dimensions():
    """Test different display dimensions"""
    display = TestDisplay(200, 100)
    assert display.width == 200
    assert display.height == 100

def test_display_render(display):
    """Test basic rendering"""
    image = display.render()
    assert isinstance(image, Image.Image)
    assert image.size == (100, 60)
    assert image.mode == '1'

def test_display_event_subscription(display, event_bus):
    """Test event bus subscription"""
    display.subscribe_to_events()
    event_bus.subscribe.assert_called()

def test_display_event_handling(display):
    """Test event handling"""
    event = {'type': 'test_event', 'data': {'message': 'test'}}
    # Should not raise any exceptions
    display.handle_event(event)

def test_display_cleanup(display, event_bus):
    """Test display cleanup"""
    display.cleanup()
    event_bus.unsubscribe.assert_called()

def test_display_without_event_bus():
    """Test display creation without event bus"""
    display = TestDisplay(100, 60)
    assert display.event_bus is None
    # Should not raise any exceptions
    display.subscribe_to_events()
    display.cleanup()

@patch('PIL.Image.new')
def test_display_render_error(mock_new, display):
    """Test rendering error handling"""
    mock_new.side_effect = Exception("Test error")
    with pytest.raises(Exception):
        display.render()
