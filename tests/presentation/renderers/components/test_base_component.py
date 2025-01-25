import pytest
from PIL import Image, ImageDraw
from unittest.mock import Mock, patch
from src.presentation.renderers.components.base_component import BaseComponent
from src.infrastructure.event_bus import EventBus

class TestComponent(BaseComponent):
    """Test implementation of BaseComponent"""
    def __init__(self, width: int, height: int, event_bus: EventBus = None):
        super().__init__(event_bus)
        self.width = width
        self.height = height
        
    def get_size(self):
        return (self.width, self.height)
        
    def render(self, draw=None, x=0, y=0):
        if draw is None:
            image = Image.new('1', self.get_size())
            draw = ImageDraw.Draw(image)
            draw.rectangle([0, 0, self.width-1, self.height-1], fill=1)
            return image
        else:
            draw.rectangle([x, y, x+self.width-1, y+self.height-1], fill=1)
            return None

@pytest.fixture
def event_bus():
    mock_bus = Mock(spec=EventBus)
    mock_bus.subscribe = Mock()
    mock_bus.unsubscribe = Mock()
    return mock_bus

@pytest.fixture
def component(event_bus):
    return TestComponent(100, 60, event_bus)

def test_component_creation(component):
    """Test basic component creation"""
    assert component.width == 100
    assert component.height == 60
    assert component.event_bus is not None
    assert component._needs_refresh is True

def test_component_get_size(component):
    """Test getting component size"""
    size = component.get_size()
    assert size == (100, 60)

def test_component_render_standalone(component):
    """Test rendering without a draw object"""
    image = component.render()
    assert isinstance(image, Image.Image)
    assert image.size == (100, 60)
    assert image.mode == '1'

def test_component_render_with_draw(component):
    """Test rendering with a draw object"""
    image = Image.new('1', (200, 100))
    draw = ImageDraw.Draw(image)
    result = component.render(draw, 10, 5)
    assert result is None

def test_component_event_subscription(component, event_bus):
    """Test event subscriptions"""
    component.subscribe_to_events()
    # Should subscribe to both update and clear events
    assert event_bus.subscribe.call_count == 2

def test_component_handle_update_event(component):
    """Test handling update event"""
    component._needs_refresh = False
    event = {'type': 'component_update'}
    component.handle_event(event)
    assert component._needs_refresh is True

def test_component_handle_clear_event(component):
    """Test handling clear event"""
    component._needs_refresh = False
    event = {'type': 'component_clear'}
    component.handle_event(event)
    assert component._needs_refresh is True

def test_component_cleanup(component, event_bus):
    """Test cleanup"""
    component.cleanup()
    # Should unsubscribe from both update and clear events
    assert event_bus.unsubscribe.call_count == 2

def test_component_without_event_bus():
    """Test component creation without event bus"""
    component = TestComponent(100, 60)
    assert component.event_bus is None
    # Should not raise any exceptions
    component.subscribe_to_events()
    component.cleanup()

@patch('PIL.Image.new')
def test_component_render_error(mock_new, component):
    """Test rendering error handling"""
    mock_new.side_effect = Exception("Test error")
    with pytest.raises(Exception):
        component.render()
