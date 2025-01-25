import pytest
from PIL import Image, ImageDraw
from unittest.mock import Mock, patch
from src.presentation.displays.tfl_display import TflDisplay
from src.infrastructure.event_bus import EventBus
from src.domain.models.service import TflService
from src.domain.models.station import TflStation

@pytest.fixture
def event_bus():
    mock_bus = Mock(spec=EventBus)
    mock_bus.subscribe = Mock()
    mock_bus.unsubscribe = Mock()
    return mock_bus

@pytest.fixture
def station():
    station_data = {
        'id': '940GZZLUBST',
        'commonName': 'Baker Street',
        'lineModeGroups': [
            {
                'modeName': 'tube',
                'lineIdentifier': ['metropolitan', 'circle']
            }
        ]
    }
    return TflStation(station_data)

@pytest.fixture
def services():
    config = {
        "tfl": {
            "platformStyle": "numeric"
        }
    }
    services_data = [
        {
            "id": "1",
            "destinationName": "Aldgate",
            "timeToStation": 300,  # 5 minutes
            "platformName": "Platform 1",
            "lineName": "Metropolitan",
            "lineId": "metropolitan"
        },
        {
            "id": "2",
            "destinationName": "Uxbridge",
            "timeToStation": 600,  # 10 minutes
            "platformName": "Platform 2",
            "lineName": "Metropolitan",
            "lineId": "metropolitan"
        }
    ]
    return [TflService(item, config) for item in services_data]

@pytest.fixture
def display(event_bus):
    return TflDisplay(800, 480, event_bus)

def test_tfl_display_creation(display):
    """Test basic TFL display creation"""
    assert display.width == 800
    assert display.height == 480
    assert display.event_bus is not None

def test_tfl_display_render_empty(display):
    """Test rendering with no data"""
    image = display.render()
    assert isinstance(image, Image.Image)
    assert image.size == (800, 480)
    assert image.mode == '1'

def test_tfl_display_render_with_data(display, station, services):
    """Test rendering with station and service data"""
    display.station = station
    display.services = services
    image = display.render()
    assert isinstance(image, Image.Image)
    assert image.size == (800, 480)

def test_tfl_display_handle_update_event(display, station, services):
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

def test_tfl_display_handle_clear_event(display, station, services):
    """Test handling clear event"""
    # Set initial data
    display.station = station
    display.services = services
    
    # Clear the display
    event = {'type': 'display_clear'}
    display.handle_event(event)
    
    assert display.station is None
    assert display.services == []

def test_tfl_display_event_subscription(display, event_bus):
    """Test event subscriptions"""
    display.subscribe_to_events()
    # Should subscribe to both update and clear events
    assert event_bus.subscribe.call_count == 2

def test_tfl_display_cleanup(display, event_bus):
    """Test cleanup"""
    display.cleanup()
    # Should unsubscribe from both update and clear events
    assert event_bus.unsubscribe.call_count == 2

@patch('PIL.Image.new')
def test_tfl_display_render_error(mock_new, display):
    """Test rendering error handling"""
    mock_new.side_effect = Exception("Test error")
    with pytest.raises(Exception):
        display.render()
