import pytest
from src.domain.models.service import TflService

@pytest.fixture
def config():
    return {
        "tfl": {
            "platformStyle": "direction"
        }
    }

def test_basic_service_creation(config):
    """Test basic service creation"""
    item = {
        'lineName': 'Piccadilly',
        'platformName': 'Platform 1',
        'destinationName': 'Heathrow Airport T4 Underground Station',
        'timeToStation': 120
    }
    
    service = TflService(item, config)
    assert service.line == 'Piccadilly'
    assert service.platform == '1'
    assert service.destination == 'Heathrow Airport T4'
    assert service.time_to_station == 120

def test_platform_mapping_westbound(config):
    """Test platform mapping for westbound trains"""
    item = {
        'lineName': 'Piccadilly',
        'platformName': 'Platform 1 - Westbound',
        'destinationName': 'Heathrow Airport T4',
        'timeToStation': 120
    }
    
    service = TflService(item, config)
    assert service.platform == '3'  # Westbound maps to platform 3
    assert service.display_platform == 'Westbound'

def test_platform_mapping_eastbound(config):
    """Test platform mapping for eastbound trains"""
    item = {
        'lineName': 'Piccadilly',
        'platformName': 'Platform 2 - Eastbound',
        'destinationName': 'Cockfosters',
        'timeToStation': 120
    }
    
    service = TflService(item, config)
    assert service.platform == '4'  # Eastbound maps to platform 4
    assert service.display_platform == 'Eastbound'

def test_platform_mapping_numeric_style(config):
    """Test platform mapping with numeric style"""
    config['tfl']['platformStyle'] = 'number'
    item = {
        'lineName': 'Piccadilly',
        'platformName': 'Platform 1 - Westbound',
        'destinationName': 'Heathrow Airport T4',
        'timeToStation': 120
    }
    
    service = TflService(item, config)
    assert service.platform == '3'  # Still maps to platform 3
    assert service.display_platform == 'Plat 3'  # But displays as number

def test_empty_platform(config):
    """Test handling of empty platform"""
    item = {
        'lineName': 'Piccadilly',
        'platformName': '',
        'destinationName': 'Heathrow Airport T4',
        'timeToStation': 120
    }
    
    service = TflService(item, config)
    assert service.platform == ''
    assert service.display_platform == ''

def test_status_formatting(config):
    """Test status time formatting"""
    # Test "Due"
    item = {'timeToStation': 20}
    service = TflService(item, config)
    assert service.status == 'Due'
    
    # Test "1 min"
    item = {'timeToStation': 45}
    service = TflService(item, config)
    assert service.status == '1 min'
    
    # Test "X mins"
    item = {'timeToStation': 180}
    service = TflService(item, config)
    assert service.status == '3 mins'

def test_destination_formatting(config):
    """Test destination name formatting"""
    item = {
        'destinationName': 'Heathrow Airport T4 Underground Station',
    }
    service = TflService(item, config)
    assert service.destination == 'Heathrow Airport T4'
    
    item = {
        'destinationName': 'Bank DLR Station',
    }
    service = TflService(item, config)
    assert service.destination == 'Bank'

def test_display_format(config):
    """Test conversion to display format"""
    item = {
        'lineName': 'Piccadilly',
        'platformName': 'Platform 1 - Westbound',
        'destinationName': 'Heathrow Airport T4',
        'timeToStation': 120
    }
    
    service = TflService(item, config)
    display = service.to_display_format()
    
    assert display['platform'] == '3'
    assert display['display_platform'] == 'Westbound'
    assert display['aimed_departure_time'] == '2 mins'
    assert display['expected_departure_time'] == 'On time'
    assert display['destination_name'] == 'Heathrow Airport T4'
    assert display['is_tfl'] is True
    assert display['mode'] == 'tfl'

def test_calling_points(config):
    """Test calling points formatting"""
    item = {
        'lineName': 'Piccadilly',
        'platformName': 'Platform 1',
        'destinationName': 'Heathrow Airport T4',
        'timeToStation': 120
    }
    
    service = TflService(item, config)
    service.stops = ['South Ealing', 'Boston Manor', 'Osterley']
    
    display = service.to_display_format()
    expected_calling = "This is a Piccadilly line service to Heathrow Airport T4, calling at South Ealing, Boston Manor, Osterley"
    assert display['calling_at_list'] == expected_calling

def test_api_response_sorting(config):
    """Test sorting of services from API response"""
    response = [
        {'timeToStation': 300, 'destinationName': 'B'},
        {'timeToStation': 120, 'destinationName': 'A'},
        {'timeToStation': 600, 'destinationName': 'C'}
    ]
    
    services = TflService.from_api_response(response, config)
    
    assert len(services) == 3
    assert services[0].time_to_station == 120
    assert services[1].time_to_station == 300
    assert services[2].time_to_station == 600
