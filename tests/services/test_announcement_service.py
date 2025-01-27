import pytest
from unittest.mock import Mock, patch
from src.infrastructure.event_bus import EventBus
from src.infrastructure.queue_manager import QueueManager
from src.services.announcement_service import AnnouncementService

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
def announcements_module():
    instance = Mock()
    instance.announce_next_train = Mock()
    instance.cleanup = Mock()
    return instance

@pytest.fixture
def service(event_bus, queue_manager, announcements_module):
    with patch('src.services.announcement_service.AnnouncementManager') as mock:
        mock.return_value = announcements_module
        return AnnouncementService(event_bus, queue_manager)

def test_announcement_service_creation(service, event_bus):
    """Test basic service creation"""
    assert service.event_bus is not None
    assert service.queue_manager is not None
    assert service.announcements is not None
    assert service._is_speaking is False
    # Should subscribe to both request and cancel events
    assert event_bus.subscribe.call_count == 2

def test_handle_announcement_request(service, queue_manager):
    """Test handling announcement request event"""
    event = {
        'type': 'announcement_request',
        'data': {
            'text': 'Test announcement',
            'priority': True
        }
    }
    service.handle_event(event)
    queue_manager.prepend.assert_called_once_with('announcements', {
        'text': 'Test announcement',
        'priority': True
    })

def test_handle_announcement_request_no_priority(service, queue_manager):
    """Test handling announcement request without priority"""
    event = {
        'type': 'announcement_request',
        'data': {
            'text': 'Test announcement'
        }
    }
    service.handle_event(event)
    queue_manager.append.assert_called_once_with('announcements', {
        'text': 'Test announcement',
        'priority': False
    })

def test_handle_announcement_cancel(service, queue_manager, announcements_module, event_bus):
    """Test handling announcement cancel event"""
    event = {'type': 'announcement_cancel'}
    service.handle_event(event)
    queue_manager.clear.assert_called_once_with('announcements')
    announcements_module.cleanup.assert_called_once()
    event_bus.emit.assert_called_once_with('announcements_cleared')

def test_process_queue_when_speaking(service, queue_manager, announcements_module):
    """Test queue processing when already speaking"""
    service._is_speaking = True
    service.process_queue()
    queue_manager.peek.assert_not_called()
    announcements_module.announce_next_train.assert_not_called()

def test_process_queue_empty(service, queue_manager, announcements_module):
    """Test queue processing with empty queue"""
    queue_manager.peek.return_value = None
    service.process_queue()
    announcements_module.announce_next_train.assert_not_called()

def test_process_queue_success(service, queue_manager, announcements_module, event_bus):
    """Test successful queue processing"""
    announcement = {
        'text': 'Test announcement',
        'priority': False
    }
    queue_manager.peek.return_value = announcement
    
    service.process_queue()
    
    expected_train_data = {
        'is_tfl': False,
        'destination_name': 'Test announcement',
        'aimed_departure_time': 'Due',
        'expected_departure_time': 'Due',
        'platform': '',
        'line': 'Announcement'
    }
    announcements_module.announce_next_train.assert_called_once_with(expected_train_data)
    queue_manager.pop.assert_called_once_with('announcements')
    event_bus.emit.assert_called_once_with('announcement_complete', {
        'text': 'Test announcement'
    })
    assert service._is_speaking is False

def test_process_queue_error(service, queue_manager, announcements_module, event_bus):
    """Test queue processing with error"""
    announcement = {
        'text': 'Test announcement',
        'priority': False
    }
    queue_manager.peek.return_value = announcement
    error_msg = "Test error"
    announcements_module.announce_next_train.side_effect = Exception(error_msg)
    
    service.process_queue()
    
    event_bus.emit.assert_called_once_with('announcement_error', {
        'text': 'Test announcement',
        'error': error_msg
    })
    assert service._is_speaking is False

def test_cleanup(service, event_bus, queue_manager, announcements_module):
    """Test service cleanup"""
    service.cleanup()
    assert event_bus.unsubscribe.call_count == 2
    queue_manager.clear.assert_called_once_with('announcements')
    announcements_module.cleanup.assert_called_once()
