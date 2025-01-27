import pytest
from PIL import Image, ImageDraw
from unittest.mock import Mock, patch
from src.presentation.displays.rail_display import RailDisplay
from src.infrastructure.event_bus import EventBus
from src.domain.models.service import Service
from src.domain.models.station import Station

@pytest.fixture
def event_bus():
    mock_bus = Mock(spec=EventBus)
    mock_bus.subscribe = Mock()
    mock_bus.unsubscribe = Mock()
    return mock_bus

@pytest.fixture
def station():
    return Station(
        station_id="PAD",
        name="London Paddington"
    )

@pytest.fixture
def services():
    services = []
    service1 = Service()
    service1.platform = "1"
    service1.destination = "Reading"
    service1.status = "On Time"
    services.append(service1)
    
    service2 = Service()
    service2.platform = "2"
    service2.destination = "Oxford"
    service2.status = "Delayed"
    services.append(service2)
    
    return services

@pytest.fixture
def display(event_bus):
    return RailDisplay(800, 480, event_bus)

def test_rail_display_creation(display):
    """Test basic rail display creation"""
    assert display.width == 800
    assert display.height == 480
    assert display.event_bus is not None

def test_rail_display_render_empty(display):
    """Test rendering with no data"""
    image = display.render()
    assert isinstance(image, Image.Image)
    assert image.size == (800, 480)
    assert image.mode == '1'

def test_rail_display_render_with_data(display, station, services):
    """Test rendering with station and service data"""
    display.station = station
    display.services = services
    image = display.render()
    assert isinstance(image, Image.Image)
    assert image.size == (800, 480)

def test_rail_display_handle_update_event(display, station, services):
    """Test handling update event"""
    event = {
        'type': 'display_update',
        'data': {
            'station': station,
            'services': services
        }
    }
    display.handle_event(event)
    assert display.station == station
    assert display.services == services

def test_rail_display_handle_clear_event(display, station, services):
    """Test handling clear event"""
    # Set initial data
    display.station = station
    display.services = services
    
    # Clear the display
    event = {'type': 'display_clear'}
    display.handle_event(event)
    
    assert display.station is None
    assert display.services == []

def test_rail_display_event_subscription(event_bus):
    """Test event subscriptions"""
    # Event subscriptions happen in __init__
    RailDisplay(800, 480, event_bus)
    # Should subscribe to display_update and display_clear
    assert event_bus.subscribe.call_args_list[0][0][0] == 'display_update'
    assert event_bus.subscribe.call_args_list[1][0][0] == 'display_clear'

def test_rail_display_cleanup(display, event_bus):
    """Test cleanup"""
    display.cleanup()
    # Should unsubscribe from both update and clear events
    assert event_bus.unsubscribe.call_count == 2

@patch('PIL.Image.new')
def test_rail_display_render_error(mock_new, display):
    """Test rendering error handling"""
    mock_new.side_effect = Exception("Test error")
    with pytest.raises(Exception):
        display.render()
