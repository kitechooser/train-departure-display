import pytest
import responses
from src.api.base_client import BaseAPIClient, APIError, RateLimitError, AuthenticationError, NotFoundError

@pytest.fixture
def client():
    return BaseAPIClient('https://api.example.com')

@responses.activate
def test_get_success(client):
    """Test successful GET request"""
    responses.add(
        responses.GET,
        'https://api.example.com/test',
        json={'data': 'test'},
        status=200
    )
    
    result = client.get('/test')
    assert result == {'data': 'test'}

@responses.activate
def test_get_auth_error(client):
    """Test authentication error handling"""
    responses.add(
        responses.GET,
        'https://api.example.com/test',
        json={'message': 'Unauthorized'},
        status=401
    )
    
    with pytest.raises(AuthenticationError) as exc:
        client.get('/test')
    assert 'HTTP 401' in str(exc.value)
    assert 'Unauthorized' in str(exc.value)

@responses.activate
def test_get_not_found(client):
    """Test not found error handling"""
    responses.add(
        responses.GET,
        'https://api.example.com/test',
        json={'message': 'Not Found'},
        status=404
    )
    
    with pytest.raises(NotFoundError) as exc:
        client.get('/test')
    assert 'HTTP 404' in str(exc.value)
    assert 'Not Found' in str(exc.value)

@responses.activate
def test_get_rate_limit(client):
    """Test rate limit error handling"""
    responses.add(
        responses.GET,
        'https://api.example.com/test',
        json={'message': 'Rate limit exceeded'},
        status=429
    )
    
    with pytest.raises(RateLimitError) as exc:
        client.get('/test')
    assert 'HTTP 429' in str(exc.value)
    assert 'Rate limit exceeded' in str(exc.value)

@responses.activate
def test_get_server_error(client):
    """Test server error handling"""
    responses.add(
        responses.GET,
        'https://api.example.com/test',
        json={'message': 'Server Error'},
        status=500
    )
    
    with pytest.raises(APIError) as exc:
        client.get('/test')
    assert 'HTTP 500' in str(exc.value)
    assert 'Server Error' in str(exc.value)

@responses.activate
def test_get_invalid_json(client):
    """Test invalid JSON response handling"""
    responses.add(
        responses.GET,
        'https://api.example.com/test',
        body='Invalid JSON',
        status=200
    )
    
    with pytest.raises(APIError) as exc:
        client.get('/test')
    assert 'Invalid JSON' in str(exc.value)

@responses.activate
def test_retry_on_error(client):
    """Test retry mechanism"""
    # Add three failure responses followed by a success
    responses.add(
        responses.GET,
        'https://api.example.com/test',
        json={'message': 'Server Error'},
        status=500
    )
    responses.add(
        responses.GET,
        'https://api.example.com/test',
        json={'message': 'Server Error'},
        status=500
    )
    responses.add(
        responses.GET,
        'https://api.example.com/test',
        json={'data': 'success'},
        status=200
    )
    
    result = client.get('/test')
    assert result == {'data': 'success'}
    assert len(responses.calls) == 3  # Verify it retried twice before succeeding

def test_context_manager():
    """Test context manager functionality"""
    with BaseAPIClient('https://api.example.com') as client:
        assert isinstance(client, BaseAPIClient)
        assert not client.closed
    assert client.closed  # Check our closed property instead of session.closed
