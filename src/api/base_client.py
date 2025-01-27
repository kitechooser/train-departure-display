import logging
import requests
from typing import Optional, Dict, Any, Union
from urllib.parse import urljoin
import time
from functools import wraps

logger = logging.getLogger(__name__)

class APIError(Exception):
    """Base exception for API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Any] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response
        
    def __str__(self):
        if self.status_code:
            return f"{self.args[0]} (HTTP {self.status_code})"
        return self.args[0]

class RateLimitError(APIError):
    """Raised when API rate limit is exceeded"""
    pass

class AuthenticationError(APIError):
    """Raised when API authentication fails"""
    pass

class NotFoundError(APIError):
    """Raised when resource is not found"""
    pass

def retry_on_error(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry API calls on failure"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (requests.RequestException, APIError) as e:
                    last_error = e
                    if isinstance(e, (AuthenticationError, NotFoundError)):
                        # Don't retry auth or not found errors
                        raise
                    if attempt < max_retries - 1:
                        wait_time = delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"API call failed, retrying in {wait_time}s... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    continue
            raise last_error
        return wrapper
    return decorator

class BaseAPIClient:
    """Base class for API clients with common functionality"""
    
    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self._closed = False
        
    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint"""
        return urljoin(f"{self.base_url}/", endpoint.lstrip('/'))
        
    def _handle_response(self, response: requests.Response) -> Union[Dict[str, Any], list]:
        """Handle API response and raise appropriate errors"""
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            status_code = response.status_code
            error_msg = f"HTTP {status_code}"
            
            try:
                error_data = response.json()
                if isinstance(error_data, dict):
                    error_msg = error_data.get('message', error_msg)
            except ValueError:
                error_msg = response.text or error_msg
                
            if status_code == 401:
                raise AuthenticationError(f"Authentication failed: {error_msg}", status_code, response)
            elif status_code == 404:
                raise NotFoundError(f"Resource not found: {error_msg}", status_code, response)
            elif status_code == 429:
                raise RateLimitError(f"Rate limit exceeded: {error_msg}", status_code, response)
            else:
                raise APIError(f"API request failed: {error_msg}", status_code, response)
        except ValueError as e:
            raise APIError(f"Invalid JSON response: {str(e)}")
            
    @retry_on_error()
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Union[Dict[str, Any], list]:
        """Make GET request to API endpoint"""
        url = self._build_url(endpoint)
        logger.debug(f"Making GET request to {url}")
        
        try:
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout
            )
            return self._handle_response(response)
        except requests.exceptions.Timeout:
            raise APIError(f"Request timed out after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {str(e)}")
            
    @retry_on_error()
    def post(self, endpoint: str, data: Optional[Any] = None, headers: Optional[Dict[str, str]] = None) -> Union[Dict[str, Any], list, str]:
        """Make POST request to API endpoint"""
        url = self._build_url(endpoint)
        logger.debug(f"Making POST request to {url}")
        
        try:
            response = self.session.post(
                url,
                data=data,
                headers=headers,
                timeout=self.timeout
            )
            # For XML responses, return the raw text
            if response.headers.get('content-type', '').startswith('text/xml'):
                return response.text
            return self._handle_response(response)
        except requests.exceptions.Timeout:
            raise APIError(f"Request timed out after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {str(e)}")
            
    def close(self):
        """Close the requests session"""
        if not self._closed:
            self.session.close()
            self._closed = True
        
    @property
    def closed(self) -> bool:
        """Check if client is closed"""
        return self._closed
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
