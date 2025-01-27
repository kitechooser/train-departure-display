import pytest
from unittest.mock import Mock, patch
from src.infrastructure.event_bus import EventBus
from src.infrastructure.queue_manager import QueueManager
from src.presentation.displays.base_display import BaseDisplay
from src.services.display_service import DisplayService

@pytest.fixture
def event_bus():
    mock_bus = Mock(spec=EventBus)
    mock_bus.subscribe = Mock()
    mock_bus.unsubscribe = Mock()
    mock_bus.emit = Mock()
    return mock_bus

@pytest.fixture
def queue_manager():
    mock_queue = Mock(spec=QueueManager)
    mock_queue.append = Mock()
    mock_queue.prepend = Mock()
    mock_queue.peek = Mock()
    mock_queue.pop = Mock()
    mock_queue.clear = Mock()
    return mock_queue

@pytest.fixture
def display():
    mock_display = Mock(spec=BaseDisplay)
    mock_display.id = "test_display"
    mock_display.update = Mock()
    mock_display.clear = Mock()
    mock_display.render = Mock()
    mock_display.cleanup = Mock()
    return mock_display

@pytest.fixture
def service(event_bus, queue_manager):
    return DisplayService(event_bus, queue_manager)

def test_display_service_creation(service, event_bus):
    """Test basic service creation"""
    assert service.event_bus is not None
    assert service.queue_manager is not None
    assert len(service.displays) == 0
    # Should subscribe to both update and clear events
    assert event_bus.subscribe.call_count == 2

def test_register_display(service, display):
    """Test registering a display"""
    service.register_display(display)
    assert len(service.displays) == 1
    assert service.displays[0] == display

def test_get_display(service, display):
    """Test getting a display by ID"""
    service.register_display(display)
    
    # Test getting existing display
    result = service.get_display("test_display")
    assert result == display
    
    # Test getting non-existent display
    result = service.get_display("non_existent")
    assert result is None

def test_handle_display_update(service, display, event_bus):
    """Test handling display update event"""
    service.register_display(display)
    
    event = {
        'type': 'display_update',
        'data': {
            'display_id': 'test_display',
            'content': 'Test content'
        }
    }
    service.handle_event(event)
    
    display.update.assert_called_once_with('Test content')
    event_bus.emit.assert_called_once_with('display_updated', {
        'display_id': 'test_display'
    })

def test_handle_display_update_missing_data(service, display, event_bus):
    """Test handling display update event with missing data"""
    service.register_display(display)
    
    # Test missing display_id
    event = {
        'type': 'display_update',
        'data': {
            'content': 'Test content'
        }
    }
    service.handle_event(event)
    display.update.assert_not_called()
    
    # Test missing content
    event = {
        'type': 'display_update',
        'data': {
            'display_id': 'test_display'
        }
    }
    service.handle_event(event)
    display.update.assert_not_called()

def test_handle_display_clear(service, display, event_bus):
    """Test handling display clear event"""
    service.register_display(display)
    
    event = {
        'type': 'display_clear',
        'data': {
            'display_id': 'test_display'
        }
    }
    service.handle_event(event)
    
    display.clear.assert_called_once()
    event_bus.emit.assert_called_once_with('display_cleared', {
        'display_id': 'test_display'
    })

def test_handle_display_clear_missing_id(service, display):
    """Test handling display clear event with missing ID"""
    service.register_display(display)
    
    event = {
        'type': 'display_clear',
        'data': {}
    }
    service.handle_event(event)
    display.clear.assert_not_called()

def test_update_display(service, display, event_bus):
    """Test updating a display directly"""
    service.register_display(display)
    
    service.update_display('test_display', 'Test content')
    
    display.update.assert_called_once_with('Test content')
    event_bus.emit.assert_called_once_with('display_updated', {
        'display_id': 'test_display'
    })

def test_update_display_not_found(service, display, event_bus):
    """Test updating a non-existent display"""
    service.register_display(display)
    
    service.update_display('non_existent', 'Test content')
    
    display.update.assert_not_called()
    event_bus.emit.assert_not_called()

def test_clear_display(service, display, event_bus):
    """Test clearing a display directly"""
    service.register_display(display)
    
    service.clear_display('test_display')
    
    display.clear.assert_called_once()
    event_bus.emit.assert_called_once_with('display_cleared', {
        'display_id': 'test_display'
    })

def test_clear_display_not_found(service, display, event_bus):
    """Test clearing a non-existent display"""
    service.register_display(display)
    
    service.clear_display('non_existent')
    
    display.clear.assert_not_called()
    event_bus.emit.assert_not_called()

def test_update_all(service, display):
    """Test updating all displays"""
    service.register_display(display)
    
    service.update_all()
    
    display.render.assert_called_once()

def test_cleanup(service, event_bus, display):
    """Test service cleanup"""
    service.register_display(display)
    
    service.cleanup()
    
    assert event_bus.unsubscribe.call_count == 2
    display.cleanup.assert_called_once()
    assert len(service.displays) == 0
