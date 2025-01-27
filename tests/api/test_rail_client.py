import pytest
import responses
import requests
from src.api.rail_client import RailClient
from src.api.base_client import APIError

@pytest.fixture
def client():
    return RailClient('test_api_key')

@pytest.fixture
def soap_response():
    return """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:lt4="http://thalesgroup.com/RTTI/2021-11-01/ldb/" xmlns:lt5="http://thalesgroup.com/RTTI/2021-11-01/ldb/types" xmlns:lt7="http://thalesgroup.com/RTTI/2021-11-01/ldb/types">
    <soap:Body>
        <lt4:GetDepBoardWithDetailsResponse>
            <lt4:GetStationBoardResult>
                <lt4:locationName>London Paddington</lt4:locationName>
                <lt7:trainServices>
                    <lt7:service>
                        <lt4:platform>3</lt4:platform>
                        <lt4:std>10:00</lt4:std>
                        <lt4:etd>On time</lt4:etd>
                        <lt4:operator>Great Western Railway</lt4:operator>
                        <lt5:destination>
                            <lt4:location>
                                <lt4:locationName>Reading</lt4:locationName>
                            </lt4:location>
                        </lt5:destination>
                        <lt7:subsequentCallingPoints>
                            <lt7:callingPointList>
                                <lt7:callingPoint>
                                    <lt7:locationName>Reading</lt7:locationName>
                                    <lt7:st>10:30</lt7:st>
                                    <lt7:et>On time</lt7:et>
                                </lt7:callingPoint>
                            </lt7:callingPointList>
                        </lt7:subsequentCallingPoints>
                    </lt7:service>
                    <lt7:service>
                        <lt4:platform>4</lt4:platform>
                        <lt4:std>10:15</lt4:std>
                        <lt4:etd>On time</lt4:etd>
                        <lt4:operator>Great Western Railway</lt4:operator>
                        <lt5:destination>
                            <lt4:location>
                                <lt4:locationName>Bristol Temple Meads</lt4:locationName>
                            </lt4:location>
                        </lt5:destination>
                        <lt7:subsequentCallingPoints>
                            <lt7:callingPointList>
                                <lt7:callingPoint>
                                    <lt7:locationName>Bath Spa</lt7:locationName>
                                    <lt7:st>11:30</lt7:st>
                                    <lt7:et>On time</lt7:et>
                                </lt7:callingPoint>
                            </lt7:callingPointList>
                        </lt7:subsequentCallingPoints>
                    </lt7:service>
                </lt7:trainServices>
            </lt4:GetStationBoardResult>
        </lt4:GetDepBoardWithDetailsResponse>
    </soap:Body>
</soap:Envelope>"""

@responses.activate
def test_get_departures_success(client, soap_response):
    """Test successful departures retrieval with default parameters"""
    # Mock the SOAP response
    responses.add(
        responses.POST,
        'https://lite.realtime.nationalrail.co.uk/OpenLDBWS/ldb11.asmx',
        body=soap_response,
        status=200,
        content_type='text/xml'
    )
    
    departures = client.get_departures('PAD', rows="10", time_offset="0", show_times=True)
    assert len(departures) == 2
    assert departures[0]['platform'] == '3'
    assert departures[0]['aimed_departure_time'] == '10:00'
    assert departures[0]['expected_departure_time'] == 'On time'
    assert departures[0]['destination_name'] == 'Reading'
    assert departures[1]['platform'] == '4'
    assert departures[1]['aimed_departure_time'] == '10:15'
    assert departures[1]['expected_departure_time'] == 'On time'
    assert departures[1]['destination_name'] == 'Bristol Temple Meads'

@responses.activate
def test_get_departures_no_data(client):
    """Test handling of no departures"""
    # Mock empty SOAP response
    responses.add(
        responses.POST,
        'https://lite.realtime.nationalrail.co.uk/OpenLDBWS/ldb11.asmx',
        body="""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:lt4="http://thalesgroup.com/RTTI/2021-11-01/ldb/">
    <soap:Body>
        <lt4:GetDepBoardWithDetailsResponse>
            <lt4:GetStationBoardResult>
                <lt4:locationName>London Paddington</lt4:locationName>
            </lt4:GetStationBoardResult>
        </lt4:GetDepBoardWithDetailsResponse>
    </soap:Body>
</soap:Envelope>""",
        status=200,
        content_type='text/xml'
    )
    
    departures = client.get_departures('PAD')
    assert len(departures) == 0

@responses.activate
def test_get_departures_with_custom_params(client, soap_response):
    """Test departures retrieval with custom parameters"""
    responses.add(
        responses.POST,
        'https://lite.realtime.nationalrail.co.uk/OpenLDBWS/ldb11.asmx',
        body=soap_response,
        status=200,
        content_type='text/xml'
    )
    
    # Test with custom parameters
    departures = client.get_departures(
        station='PAD',
        rows="5",
        time_offset="30",
        destination="RDG",
        show_times=False
    )
    
    assert len(departures) == 2
    # Verify calling points don't include times when show_times=False
    assert "10:30" not in departures[0]['calling_at_list']
    assert "Reading" in departures[0]['calling_at_list']

@responses.activate
def test_get_departures_error(client, caplog):
    """Test error handling and logging"""
    responses.add(
        responses.POST,
        'https://lite.realtime.nationalrail.co.uk/OpenLDBWS/ldb11.asmx',
        body="""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <soap:Fault>
            <faultcode>soap:Server</faultcode>
            <faultstring>API Error</faultstring>
        </soap:Fault>
    </soap:Body>
</soap:Envelope>""",
        status=500,
        content_type='text/xml'
    )
    
    departures = client.get_departures('PAD')
    assert len(departures) == 0
    assert "SOAP fault received: API Error" in caplog.text

@responses.activate
def test_auth_headers(client):
    """Test authentication headers are set correctly"""
    responses.add(
        responses.POST,
        'https://lite.realtime.nationalrail.co.uk/OpenLDBWS/ldb11.asmx',
        body="",
        status=200
    )
    
    client.get_departures('PAD')
    
    # Verify the request headers
    request = responses.calls[0].request
    assert request.headers['Content-Type'] == 'text/xml;charset=UTF-8'
    assert request.headers['SOAPAction'] == 'http://thalesgroup.com/RTTI/2021-11-01/ldb/GetDepBoardWithDetails'
    assert request.headers['X-SOAP-Version'] == '1.1'

@responses.activate
def test_auth_failure(client):
    """Test authentication failure handling"""
    responses.add(
        responses.POST,
        'https://lite.realtime.nationalrail.co.uk/OpenLDBWS/ldb11.asmx',
        body="""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <soap:Fault>
            <faultcode>soap:Client</faultcode>
            <faultstring>Invalid TokenValue supplied</faultstring>
        </soap:Fault>
    </soap:Body>
</soap:Envelope>""",
        status=401,
        content_type='text/xml'
    )
    
    with pytest.raises(APIError) as exc_info:
        client.get_departures('PAD')
    assert "Authentication failed" in str(exc_info.value)

@responses.activate
def test_get_departures_timeout(client, caplog):
    """Test timeout handling and logging"""
    responses.add(
        responses.POST,
        'https://lite.realtime.nationalrail.co.uk/OpenLDBWS/ldb11.asmx',
        body=requests.exceptions.ConnectTimeout()
    )
    
    departures = client.get_departures('PAD')
    assert len(departures) == 0

@responses.activate
def test_soap_fault_logging(client, caplog):
    """Test SOAP fault logging"""
    responses.add(
        responses.POST,
        'https://lite.realtime.nationalrail.co.uk/OpenLDBWS/ldb11.asmx',
        body="""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <soap:Fault>
            <faultcode>soap:Server</faultcode>
            <faultstring>Invalid station code</faultstring>
        </soap:Fault>
    </soap:Body>
</soap:Envelope>""",
        status=200,
        content_type='text/xml'
    )
    
    departures = client.get_departures('INVALID')
    assert len(departures) == 0
    assert "SOAP fault received: Invalid station code" in caplog.text

def test_client_initialization():
    """Test client initialization with custom timeout"""
    client = RailClient('test_key', timeout=5)
    assert client.api_key == 'test_key'
    assert client.timeout == 5
    assert not client.closed

def test_client_context_manager():
    """Test client context manager"""
    with RailClient('test_key') as client:
        assert not client.closed
    assert client.closed
