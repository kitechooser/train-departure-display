import pytest
import responses
from src.api.tfl_client import TflClient
from src.domain.models.station import TflStation
from src.domain.models.service import TflService

@pytest.fixture
def client():
    return TflClient('test_app_id', 'test_app_key')

@pytest.fixture
def config():
    return {
        "tfl": {
            "mode": "tube",
            "direction": "all",
            "platformStyle": "direction"
        }
    }

@pytest.fixture
def station_response():
    return {
        "id": "940GZZLUNFD",
        "commonName": "Northfields Underground Station",
        "lineModeGroups": [
            {
                "modeName": "tube",
                "lineIdentifier": ["piccadilly"]
            }
        ]
    }

@pytest.fixture
def arrivals_response():
    return [
        {
            "lineId": "piccadilly",
            "lineName": "Piccadilly",
            "platformName": "Platform 3 - Westbound",
            "destinationName": "Heathrow Terminal 5 Underground Station",
            "timeToStation": 120,
            "currentLocation": "Approaching South Ealing"
        },
        {
            "lineId": "piccadilly",
            "lineName": "Piccadilly",
            "platformName": "Platform 3 - Westbound",
            "destinationName": "Heathrow Terminal 4 Underground Station",
            "timeToStation": 360,
            "currentLocation": "At Boston Manor Platform 3"
        }
    ]

@pytest.fixture
def sequence_response():
    return {
        "stopPointSequences": [
            {
                "stopPoint": [
                    {"id": "940GZZLUNFD", "name": "Northfields Underground Station"},
                    {"id": "940GZZLUSEA", "name": "South Ealing Underground Station"},
                    {"id": "940GZZLUBOS", "name": "Boston Manor Underground Station"},
                    {"id": "940GZZLUHTH", "name": "Heathrow Terminal 5 Underground Station"}
                ]
            }
        ]
    }

@responses.activate
def test_get_station_success(client, station_response):
    """Test successful station retrieval"""
    responses.add(
        responses.GET,
        'https://api.tfl.gov.uk/StopPoint/940GZZLUNFD',
        json=station_response,
        status=200
    )
    
    station = client.get_station('940GZZLUNFD', 'tube')
    assert isinstance(station, TflStation)
    assert station.id == '940GZZLUNFD'
    assert station.name == 'Northfields Underground Station'
    assert station.available_lines == ['piccadilly']

@responses.activate
def test_get_arrivals_success(client, config, station_response, arrivals_response, sequence_response):
    """Test successful arrivals retrieval"""
    # Mock station for testing
    station = TflStation(station_response)
    station.add_available_lines(['piccadilly'])
    
    # Add mock responses
    responses.add(
        responses.GET,
        'https://api.tfl.gov.uk/Line/piccadilly/Arrivals/940GZZLUNFD',
        json=arrivals_response,
        status=200
    )
    
    responses.add(
        responses.GET,
        'https://api.tfl.gov.uk/Line/piccadilly/Route/Sequence/all',
        json=sequence_response,
        status=200
    )
    
    services = client.get_arrivals(station, config)
    assert len(services) == 2
    assert all(isinstance(service, TflService) for service in services)
    
    # Check first service details
    service = services[0]
    assert service.line == 'Piccadilly'
    assert service.platform == '3'
    assert service.display_platform == 'Westbound'
    assert service.destination == 'Heathrow Terminal 5'
    assert service.status == '2 mins'
    
    # Check intermediate stops were fetched
    assert service.stops == ['South Ealing', 'Boston Manor']

@responses.activate
def test_get_station_not_found(client):
    """Test station not found handling"""
    responses.add(
        responses.GET,
        'https://api.tfl.gov.uk/StopPoint/invalid',
        json={'message': 'Station not found'},
        status=404
    )
    
    station = client.get_station('invalid', 'tube')
    assert station is None

@responses.activate
def test_get_arrivals_no_services(client, config):
    """Test handling of no services"""
    # Mock station for testing
    station = TflStation({
        "id": "test",
        "commonName": "Test Station"
    })
    station.add_available_lines(['piccadilly'])
    
    responses.add(
        responses.GET,
        'https://api.tfl.gov.uk/Line/piccadilly/Arrivals/test',
        json=[],
        status=200
    )
    
    services = client.get_arrivals(station, config)
    assert len(services) == 0

@responses.activate
def test_get_intermediate_stops_success(client):
    """Test successful intermediate stops retrieval"""
    responses.add(
        responses.GET,
        'https://api.tfl.gov.uk/Line/piccadilly/Route/Sequence/all',
        json={
            "stopPointSequences": [
                {
                    "stopPoint": [
                        {"id": "start", "name": "Start Station"},
                        {"id": "mid1", "name": "Middle Station 1"},
                        {"id": "mid2", "name": "Middle Station 2"},
                        {"id": "end", "name": "End Station"}
                    ]
                }
            ]
        },
        status=200
    )
    
    stops = client.get_intermediate_stops('piccadilly', 'start', 'End Station')
    assert stops == ['Middle Station 1', 'Middle Station 2']

@responses.activate
def test_get_intermediate_stops_no_sequence(client):
    """Test handling of no sequence data"""
    responses.add(
        responses.GET,
        'https://api.tfl.gov.uk/Line/piccadilly/Route/Sequence/all',
        json={},
        status=200
    )
    
    stops = client.get_intermediate_stops('piccadilly', 'start', 'end')
    assert stops is None
