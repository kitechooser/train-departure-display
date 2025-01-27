import pytest
from unittest.mock import Mock, patch, call
from src.infrastructure.event_bus import EventBus
from src.infrastructure.queue_manager import QueueManager
from src.infrastructure.config_manager import ConfigManager
from src.services.main_service import MainService
from src.services.announcement_service import AnnouncementService
from src.services.display_service import DisplayService
from src.services.status_service import StatusService
from src.presentation.displays.tfl_display import TflDisplay
from src.presentation.displays.rail_display import RailDisplay

@pytest.fixture
def event_bus():
    with patch('src.infrastructure.event_bus.EventBus') as mock:
        instance = mock.return_value
        instance.subscribe = Mock()
        instance.unsubscribe = Mock()
        instance.emit = Mock()
        yield instance

@pytest.fixture
def queue_manager():
    with patch('src.infrastructure.queue_manager.QueueManager') as mock:
        instance = mock.return_value
        instance.append = Mock()
        instance.prepend = Mock()
        instance.peek = Mock()
        instance.pop = Mock()
        instance.clear = Mock()
        yield instance

@pytest.fixture
def config_manager():
    with patch('src.infrastructure.config_manager.ConfigManager') as mock:
        instance = mock.return_value
        mock_config = {
            'display': {
                'width': 256,
                'height': 64,
                'previewMode': True,
                'dualDisplays': True
            },
            'screen1': {
                'outOfHoursName': 'Test Station 1',
                'type': 'rail',
                'station': 'PAD'
            },
            'screen2': {
                'outOfHoursName': 'Test Station 2',
                'type': 'tfl',
                'station': 'Victoria',
                'platform': '1'
            }
        }
        instance.get = Mock(side_effect=lambda key, default=None: mock_config.get(key, default))
        yield instance

@pytest.fixture
def announcement_service():
    with patch('src.services.announcement_service.AnnouncementService') as mock:
        instance = mock.return_value
        instance.cleanup = Mock()
        yield instance

@pytest.fixture
def display_service():
    with patch('src.services.display_service.DisplayService') as mock:
        instance = mock.return_value
        instance.register_display = Mock()
        instance.update_display = Mock()
        instance.update_all = Mock()
        instance.cleanup = Mock()
        yield instance

@pytest.fixture
def status_service():
    with patch('src.services.status_service.StatusService') as mock:
        instance = mock.return_value
        instance.update_status = Mock()
        instance.cleanup = Mock()
        yield instance

@pytest.fixture
def tfl_display():
    with patch('src.presentation.displays.tfl_display.TflDisplay') as mock:
        yield mock.return_value

@pytest.fixture
def rail_display():
    with patch('src.presentation.displays.rail_display.RailDisplay') as mock:
        yield mock.return_value

@pytest.fixture
def service(event_bus, queue_manager, config_manager, announcement_service, 
            display_service, status_service, tfl_display, rail_display):
    with patch.multiple('src.services.main_service',
                       EventBus=Mock(return_value=event_bus),
                       QueueManager=Mock(return_value=queue_manager),
                       ConfigManager=Mock(return_value=config_manager),
                       AnnouncementService=Mock(return_value=announcement_service),
                       DisplayService=Mock(return_value=display_service),
                       StatusService=Mock(return_value=status_service),
                       TflDisplay=Mock(return_value=tfl_display),
                       RailDisplay=Mock(return_value=rail_display)), \
         patch('src.display_manager.create_display', return_value=Mock()):
        return MainService("config.json")

def test_main_service_creation(service, event_bus, display_service, tfl_display, rail_display, config_manager):
    """Test basic service creation"""
    assert service.event_bus is not None
    assert service.queue_manager is not None
    assert service.config is not None
    assert service.announcement_service is not None
    assert service.display_service is not None
    assert service.status_service is not None
    
    # Should subscribe to service events
    assert event_bus.subscribe.call_count == 2
    
    # Should register displays based on screen config
    screen1_config = config_manager.get('screen1')
    screen2_config = config_manager.get('screen2')
    
    expected_calls = []
    if screen1_config['type'] == 'rail':
        expected_calls.append(call(rail_display))
    else:
        expected_calls.append(call(tfl_display))
        
    if screen2_config['type'] == 'rail':
        expected_calls.append(call(rail_display))
    else:
        expected_calls.append(call(tfl_display))
        
    display_service.register_display.assert_has_calls(expected_calls)

def test_handle_tfl_update(service, display_service, status_service, event_bus):
    """Test handling TfL service update"""
    event = {
        'type': 'service_update',
        'data': {
            'service_type': 'tfl',
            'content': {
                'status': {
                    'severity': 2,
                    'description': 'Minor Delays'
                }
            }
        }
    }
    service.handle_event(event)
    
    display_service.update_display.assert_called_once_with('tfl', event['data']['content'])
    status_service.update_status.assert_called_once_with('tfl', event['data']['content']['status'])
    event_bus.emit.assert_called_once_with('announcement_request', {
        'text': 'Minor Delays',
        'priority': True
    })

def test_handle_tfl_update_no_announcement(service, display_service, status_service, event_bus):
    """Test handling TfL service update with no announcement needed"""
    event = {
        'type': 'service_update',
        'data': {
            'service_type': 'tfl',
            'content': {
                'status': {
                    'severity': 1,
                    'description': 'Good Service'
                }
            }
        }
    }
    service.handle_event(event)
    
    display_service.update_display.assert_called_once_with('tfl', event['data']['content'])
    status_service.update_status.assert_called_once_with('tfl', event['data']['content']['status'])
    event_bus.emit.assert_not_called()

def test_tfl_update_loop(service, display_service, event_bus):
    """Test TfL update loop with station data"""
    # Mock TfL client get_stations to return test data
    test_stations = [
        {
            'name': 'Victoria',
            'platform': '1',
            'services': [
                {
                    'destination': 'Heathrow',
                    'due': '2 mins',
                    'platform': 'Westbound'
                }
            ]
        }
    ]
    service.tfl_client.get_stations = Mock(return_value=test_stations)
    
    # Run one iteration of the update loop
    service._process_tfl_updates()
    
    # Verify stations were fetched
    expected_stations = [
        {
            'name': 'Victoria',
            'platform': '1'
        }
    ]
    service.tfl_client.get_stations.assert_called_once_with(expected_stations)
    
    # Verify event was emitted with station data
    event_bus.emit.assert_called_once()
    event_data = event_bus.emit.call_args[0][1]
    assert event_data['type'] == 'service_update'  # Using old event type since migration config is not set
    assert event_data['data']['service_type'] == 'tfl'
    assert event_data['data']['content']['stations'] == test_stations

def test_rail_update_loop(service, display_service, event_bus):
    """Test rail update loop with station code tracking"""
    # Mock rail client get_departures to return test data
    test_departures = [
        {
            'platform': '1',
            'aimed_departure_time': '14:30',
            'destination_name': 'Reading'
        }
    ]
    service.rail_client.get_departures = Mock(return_value=test_departures)
    
    # Run one iteration of the update loop
    service._process_rail_updates()
    
    # Verify departures were fetched for the rail station
    expected_calls = [
        call(station='PAD', rows="10", time_offset="0", show_times=True)
    ]
    service.rail_client.get_departures.assert_has_calls(expected_calls)
    
    # Verify station codes were added to departures
    event_bus.emit.assert_called_once()
    event_data = event_bus.emit.call_args[0][1]
    assert event_data['type'] == 'service_update'  # Using old event type since migration config is not set
    assert event_data['data']['service_type'] == 'rail'
    assert len(event_data['data']['content']['departures']) == 1  # One for the rail station
    assert event_data['data']['content']['departures'][0]['station_code'] == 'PAD'

def test_handle_rail_update(service, display_service, event_bus):
    """Test handling rail service update with announcements"""
    event = {
        'type': 'service_update',
        'data': {
            'service_type': 'rail',
            'content': {
                'announcement': 'Platform change for the 14:30 service'
            }
        }
    }
    service.handle_event(event)
    
    display_service.update_display.assert_called_once_with('rail', event['data']['content'])
    event_bus.emit.assert_called_once_with('announcement_request', {
        'text': 'Platform change for the 14:30 service',
        'priority': False
    })

def test_handle_rail_update_no_announcement(service, display_service, event_bus):
    """Test handling rail service update with no announcement"""
    event = {
        'type': 'service_update',
        'data': {
            'service_type': 'rail',
            'content': {}
        }
    }
    service.handle_event(event)
    
    display_service.update_display.assert_called_once_with('rail', event['data']['content'])
    event_bus.emit.assert_not_called()

def test_handle_service_error(service, event_bus):
    """Test handling service error"""
    event = {
        'type': 'service_error',
        'data': {
            'service': 'tfl',
            'error': 'API Error'
        }
    }
    service.handle_event(event)
    
    service.display_service.update_display.assert_called_once_with('tfl', {'error': 'API Error'})

def test_handle_service_error_missing_data(service, event_bus):
    """Test handling service error with missing data"""
    event = {
        'type': 'service_error',
        'data': {}
    }
    service.handle_event(event)
    service.display_service.update_display.assert_not_called()

def test_start(service, event_bus):
    """Test service start"""
    service.start()
    service.display_service.update_display.assert_has_calls([
        call('rail', {'error': 'Waiting for data...'}),
        call('tfl_secondary', {'error': 'Waiting for data...'})
    ])

def test_stop(service, event_bus, announcement_service, display_service, status_service):
    """Test service stop"""
    service.stop()
    
    announcement_service.cleanup.assert_called_once()
    display_service.cleanup.assert_called_once()
    status_service.cleanup.assert_called_once()
    assert event_bus.unsubscribe.call_count == 2
