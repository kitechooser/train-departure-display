import pytest
from unittest.mock import Mock, patch, call
from src.infrastructure.event_bus import EventBus
from src.infrastructure.queue_manager import QueueManager
from src.infrastructure.config_manager import ConfigManager
from src.domain.processors.tfl_processor import TflProcessor
from src.api.tfl_client import TflClient
from src.services.status_service import StatusService

@pytest.fixture
def event_bus():
    mock_bus = Mock(spec=EventBus)
    mock_bus.subscribe = Mock()
    mock_bus.unsubscribe = Mock()
    mock_bus.emit = Mock()
    return mock_bus

@pytest.fixture
def config():
    return {
        'tfl': {
            'app_id': 'test-app-id',
            'app_key': 'test-app-key'
        }
    }

@pytest.fixture
def queue_manager(config):
    mock_queue = Mock(spec=QueueManager)
    mock_queue.append = Mock()
    mock_queue.prepend = Mock()
    mock_queue.peek = Mock()
    mock_queue.pop = Mock()
    mock_queue.clear = Mock()
    mock_queue.config = Mock()
    mock_queue.config.get_config = Mock(return_value=config)
    return mock_queue

@pytest.fixture
def tfl_client():
    with patch('src.api.tfl_client.TflClient') as mock:
        instance = mock.return_value
        instance.get_line_status = Mock()
        yield instance

@pytest.fixture
def tfl_processor():
    with patch('src.domain.processors.tfl_processor.TflProcessor') as mock:
        instance = mock.return_value
        instance.process_status = Mock(return_value={
            'severity': 1,
            'description': 'Good Service'
        })
        yield instance

@pytest.fixture
def service(event_bus, queue_manager, tfl_client, tfl_processor):
    with patch('src.services.status_service.TflClient') as client_mock, \
         patch('src.services.status_service.TflProcessor') as processor_mock:
        client_mock.return_value = tfl_client
        processor_mock.return_value = tfl_processor
        return StatusService(event_bus, queue_manager)

def test_status_service_creation(service, event_bus, tfl_client, queue_manager):
    """Test basic service creation"""
    assert service.event_bus is not None
    assert service.queue_manager is not None
    assert service.tfl_client is not None
    assert service.processor is not None
    assert len(service.statuses) == 0
    
    # Should subscribe to both update and request events
    assert event_bus.subscribe.call_count == 2
    
    # Should initialize TfL client with credentials from config
    config = queue_manager.config.get_config()
    tfl_config = config['tfl']
    assert tfl_client == service.tfl_client

def test_handle_status_update(service, queue_manager, tfl_processor, event_bus):
    """Test handling status update event"""
    event = {
        'type': 'status_update',
        'data': {
            'line': 'victoria',
            'status': {'raw_status': 'Good Service'}
        }
    }
    service.handle_event(event)
    
    tfl_processor.process_status.assert_called_once_with({'raw_status': 'Good Service'})
    queue_manager.append.assert_called_once_with('statuses', {
        'line': 'victoria',
        'status': {'severity': 1, 'description': 'Good Service'}
    })
    event_bus.emit.assert_called_once_with('status_updated', {
        'line': 'victoria',
        'status': {'severity': 1, 'description': 'Good Service'}
    })

def test_handle_status_update_missing_data(service, tfl_processor, queue_manager):
    """Test handling status update event with missing data"""
    # Test missing line
    event = {
        'type': 'status_update',
        'data': {
            'status': {'raw_status': 'Good Service'}
        }
    }
    service.handle_event(event)
    tfl_processor.process_status.assert_not_called()
    queue_manager.append.assert_not_called()
    
    # Test missing status
    event = {
        'type': 'status_update',
        'data': {
            'line': 'victoria'
        }
    }
    service.handle_event(event)
    tfl_processor.process_status.assert_not_called()
    queue_manager.append.assert_not_called()

def test_handle_status_request_found(service, event_bus):
    """Test handling status request event for existing status"""
    # Add a status
    service.statuses['victoria'] = {'severity': 1, 'description': 'Good Service'}
    
    event = {
        'type': 'status_request',
        'data': {
            'line': 'victoria'
        }
    }
    service.handle_event(event)
    
    event_bus.emit.assert_called_once_with('status_response', {
        'line': 'victoria',
        'status': {'severity': 1, 'description': 'Good Service'}
    })

def test_handle_status_request_not_found(service, event_bus):
    """Test handling status request event for non-existent status"""
    event = {
        'type': 'status_request',
        'data': {
            'line': 'victoria'
        }
    }
    service.handle_event(event)
    
    event_bus.emit.assert_called_once_with('status_not_found', {
        'line': 'victoria'
    })

def test_handle_status_request_missing_line(service, event_bus):
    """Test handling status request event with missing line"""
    event = {
        'type': 'status_request',
        'data': {}
    }
    service.handle_event(event)
    event_bus.emit.assert_not_called()

def test_get_all_statuses(service):
    """Test getting all statuses"""
    # Add some statuses
    service.statuses['victoria'] = {'severity': 1, 'description': 'Good Service'}
    service.statuses['piccadilly'] = {'severity': 2, 'description': 'Minor Delays'}
    
    result = service.get_all_statuses()
    assert result == {
        'victoria': {'severity': 1, 'description': 'Good Service'},
        'piccadilly': {'severity': 2, 'description': 'Minor Delays'}
    }
    # Verify it's a copy
    assert result is not service.statuses

def test_clear_status(service, event_bus):
    """Test clearing a single status"""
    # Add a status
    service.statuses['victoria'] = {'severity': 1, 'description': 'Good Service'}
    
    service.clear_status('victoria')
    
    assert 'victoria' not in service.statuses
    event_bus.emit.assert_called_once_with('status_cleared', {
        'line': 'victoria'
    })

def test_clear_status_not_found(service, event_bus):
    """Test clearing a non-existent status"""
    service.clear_status('victoria')
    event_bus.emit.assert_not_called()

def test_clear_all_statuses(service, event_bus):
    """Test clearing all statuses"""
    # Add some statuses
    service.statuses['victoria'] = {'severity': 1, 'description': 'Good Service'}
    service.statuses['piccadilly'] = {'severity': 2, 'description': 'Minor Delays'}
    
    service.clear_all_statuses()
    
    assert len(service.statuses) == 0
    event_bus.emit.assert_called_once_with('all_statuses_cleared')

def test_cleanup(service, event_bus):
    """Test service cleanup"""
    # Add a status
    service.statuses['victoria'] = {'severity': 1, 'description': 'Good Service'}
    
    service.cleanup()
    
    assert event_bus.unsubscribe.call_count == 2
    assert len(service.statuses) == 0
    event_bus.emit.assert_called_once_with('all_statuses_cleared')
