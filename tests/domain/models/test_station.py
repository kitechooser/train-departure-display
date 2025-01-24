import pytest
from src.domain.models import Station, TflStation

def test_base_station():
    """Test base Station class"""
    station = Station('test_id', 'Test Station')
    assert station.id == 'test_id'
    assert station.name == 'Test Station'

def test_tfl_station_creation():
    """Test TflStation creation from data"""
    data = {
        'id': '940GZZLUNFD',
        'commonName': 'Northfields Underground Station'
    }
    station = TflStation(data)
    assert station.id == '940GZZLUNFD'
    assert station.name == 'Northfields Underground Station'
    assert station.available_lines == []

def test_tfl_station_fallback_name():
    """Test TflStation name fallback"""
    data = {
        'id': 'test_id',
        'name': 'Fallback Name'  # Using name instead of commonName
    }
    station = TflStation(data)
    assert station.name == 'Fallback Name'

def test_tfl_station_unknown_name():
    """Test TflStation unknown name handling"""
    data = {
        'id': 'test_id'
        # No name provided
    }
    station = TflStation(data)
    assert station.name == 'Unknown Station'

def test_tfl_station_add_lines():
    """Test adding available lines"""
    station = TflStation({'id': 'test'})
    lines = ['piccadilly', 'district']
    station.add_available_lines(lines)
    assert station.available_lines == lines

def test_tfl_station_from_api_response_success():
    """Test creating TflStation from successful API response"""
    response = {
        'id': 'test_id',
        'commonName': 'Test Station',
        'lineModeGroups': [
            {
                'modeName': 'tube',
                'lineIdentifier': ['piccadilly', 'district']
            },
            {
                'modeName': 'bus',
                'lineIdentifier': ['123', '456']
            }
        ]
    }
    
    station = TflStation.from_api_response(response, 'tube')
    assert station is not None
    assert station.id == 'test_id'
    assert station.name == 'Test Station'
    assert station.available_lines == ['piccadilly', 'district']

def test_tfl_station_from_api_response_lines_array():
    """Test creating TflStation using lines array"""
    response = {
        'id': 'test_id',
        'commonName': 'Test Station',
        'lines': [
            {'id': 'piccadilly', 'modeName': 'tube'},
            {'id': 'district', 'modeName': 'tube'},
            {'id': '123', 'modeName': 'bus'}
        ]
    }
    
    station = TflStation.from_api_response(response, 'tube')
    assert station is not None
    assert station.available_lines == ['piccadilly', 'district']

def test_tfl_station_from_api_response_no_matching_mode():
    """Test handling when no matching mode is found"""
    response = {
        'id': 'test_id',
        'commonName': 'Test Station',
        'lineModeGroups': [
            {
                'modeName': 'bus',
                'lineIdentifier': ['123', '456']
            }
        ]
    }
    
    station = TflStation.from_api_response(response, 'tube')
    assert station is None

def test_tfl_station_from_api_response_empty():
    """Test handling empty API response"""
    station = TflStation.from_api_response(None, 'tube')
    assert station is None
