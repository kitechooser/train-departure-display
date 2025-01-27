import pytest
from unittest.mock import Mock, patch
from src.domain.processors.tfl_processor import TflProcessor
from src.domain.models.station import TflStation
from src.domain.models.service import TflService

@pytest.fixture
def config():
    return {
        "tfl": {
            "mode": "tube",
            "platformStyle": "direction",
            "direction": "all"
        }
    }

@pytest.fixture
def screen_config():
    return {
        "departureStation": "940GZZLUNFD",
        "outOfHoursName": "Northfields"
    }

@pytest.fixture
def mock_client():
    client = Mock()
    # Create station with proper dictionary input
    station_data = {
        'id': '940GZZLUNFD',
        'commonName': 'Northfields',
        'lineModeGroups': [
            {
                'modeName': 'tube',
                'lineIdentifier': ['piccadilly']
            }
        ]
    }
    station = TflStation(station_data)
    client.get_station.return_value = station
    return client

def test_get_station_data_success(config, screen_config, mock_client):
    """Test successful station data retrieval"""
    processor = TflProcessor(mock_client, config)
    
    # Mock arrivals data
    mock_client.get_arrivals.return_value = [
        TflService({
            'lineName': 'Piccadilly',
            'platformName': 'Platform 1 - Westbound',
            'destinationName': 'Heathrow T4',
            'timeToStation': 120
        }, config),
        TflService({
            'lineName': 'Piccadilly',
            'platformName': 'Platform 2 - Eastbound',
            'destinationName': 'Cockfosters',
            'timeToStation': 180
        }, config)
    ]
    
    departures, calling_points, station_name = processor.get_station_data(screen_config)
    
    assert len(departures) == 2
    assert station_name == "Northfields"
    assert departures[0]['platform'] == '3'  # Westbound mapped to platform 3
    assert departures[1]['platform'] == '4'  # Eastbound mapped to platform 4

def test_get_station_data_no_station(config, screen_config, mock_client):
    """Test handling when station not found"""
    processor = TflProcessor(mock_client, config)
    mock_client.get_station.return_value = None
    
    departures, calling_points, station_name = processor.get_station_data(screen_config)
    
    assert departures is False
    assert calling_points is False
    assert station_name == screen_config["outOfHoursName"]

def test_get_station_data_no_services(config, screen_config, mock_client):
    """Test handling when no services found"""
    processor = TflProcessor(mock_client, config)
    mock_client.get_arrivals.return_value = []
    
    departures, calling_points, station_name = processor.get_station_data(screen_config)
    
    assert departures is False
    assert calling_points is False
    assert station_name == screen_config["outOfHoursName"]

def test_filter_platform_departures_westbound(config):
    """Test filtering westbound services (Platform 1 -> 3)"""
    processor = TflProcessor(None, config)
    departures = [
        {
            'platform': '3',  # Already mapped from Platform 1 Westbound
            'display_platform': 'Westbound',
            'destination_name': 'Heathrow T4',
            'calling_at_list': 'Test calling points'
        }
    ]
    
    filtered, calling_points, station = processor.filter_platform_departures(
        departures, '3', 'Northfields'
    )
    
    assert len(filtered) == 1
    assert filtered[0]['platform'] == '3'
    assert filtered[0]['display_platform'] == 'Westbound'

def test_filter_platform_departures_eastbound(config):
    """Test filtering eastbound services (Platform 2 -> 4)"""
    processor = TflProcessor(None, config)
    departures = [
        {
            'platform': '4',  # Already mapped from Platform 2 Eastbound
            'display_platform': 'Eastbound',
            'destination_name': 'Cockfosters',
            'calling_at_list': 'Test calling points'
        }
    ]
    
    filtered, calling_points, station = processor.filter_platform_departures(
        departures, '4', 'Northfields'
    )
    
    assert len(filtered) == 1
    assert filtered[0]['platform'] == '4'
    assert filtered[0]['display_platform'] == 'Eastbound'

def test_filter_platform_departures_no_match(config):
    """Test filtering when no services match platform"""
    processor = TflProcessor(None, config)
    departures = [
        {
            'platform': '3',
            'display_platform': 'Westbound',
            'destination_name': 'Heathrow T4'
        }
    ]
    
    filtered, calling_points, station = processor.filter_platform_departures(
        departures, '4', 'Northfields'
    )
    
    assert filtered is False
    assert calling_points is False
    assert station == 'Northfields'

def test_filter_platform_departures_no_platform_filter(config):
    """Test when no platform filter is specified"""
    processor = TflProcessor(None, config)
    departures = [
        {
            'platform': '3',
            'display_platform': 'Westbound',
            'destination_name': 'Heathrow T4',
            'calling_at_list': 'Test calling points'
        }
    ]
    
    filtered, calling_points, station = processor.filter_platform_departures(
        departures, '', 'Northfields'
    )
    
    assert len(filtered) == 1
    assert filtered == departures
    assert calling_points == departures[0]['calling_at_list']

def test_filter_platform_departures_no_departures(config):
    """Test filtering with no departures"""
    processor = TflProcessor(None, config)
    
    filtered, calling_points, station = processor.filter_platform_departures(
        [], '3', 'Northfields'
    )
    
    assert filtered is False
    assert calling_points is False
    assert station == 'Northfields'
