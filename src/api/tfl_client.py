from typing import Optional, List, Dict, Any
import logging
from .base_client import BaseAPIClient, APIError
from src.domain.models.station import TflStation
from src.domain.models.service import TflService

logger = logging.getLogger(__name__)

class TflClient(BaseAPIClient):
    """TfL API client"""
    
    def __init__(self, app_id: str, app_key: str, timeout: int = 10):
        super().__init__('https://api.tfl.gov.uk', timeout)
        self.app_id = app_id
        self.app_key = app_key
        
    def _get_auth_params(self) -> Dict[str, str]:
        """Get authentication parameters"""
        return {
            'app_id': self.app_id,
            'app_key': self.app_key
        }
        
    def get_station(self, station_id: str, mode: str) -> Optional[TflStation]:
        """Get station information by ID"""
        logger.info(f"Looking up TfL station: {station_id}")
        
        try:
            # Direct StopPoint lookup using NAPTAN code
            response = self.get(
                f'/StopPoint/{station_id}',
                params=self._get_auth_params()
            )
            
            return TflStation.from_api_response(response, mode)
            
        except APIError as e:
            logger.error(f"Failed to get station {station_id}: {str(e)}")
            return None
            
    def get_arrivals(self, station: TflStation, config: Dict[str, Any]) -> List[TflService]:
        """Get arrivals for a station"""
        if not station or not station.available_lines:
            return []
            
        try:
            # Get arrivals for all available lines
            response = self.get(
                f'/Line/{",".join(station.available_lines)}/Arrivals/{station.id}',
                params={
                    **self._get_auth_params(),
                    'direction': config["tfl"]["direction"]
                }
            )
            
            services = TflService.from_api_response(response, config)
            
            # Filter services by platform if specified
            if 'platform' in config:
                services = [s for s in services if s.platform == config['platform']]
            
            # Get intermediate stops for each service
            for service in services:
                if service.line and station.id:
                    service.stops = self.get_intermediate_stops(
                        service.line_id,
                        station.id,
                        service.destination
                    )
                    
            return services
            
        except APIError as e:
            logger.error(f"Failed to get arrivals for station {station.id}: {str(e)}")
            return []
            
    def get_intermediate_stops(self, line_id: str, from_id: str, to_name: str) -> Optional[List[str]]:
        """Get intermediate stops between two stations on a line"""
        try:
            response = self.get(
                f'/Line/{line_id}/Route/Sequence/all',
                params=self._get_auth_params()
            )
            
            if not response or 'stopPointSequences' not in response:
                return None
                
            # Find the sequence that contains our stations
            for sequence in response['stopPointSequences']:
                stops = sequence.get('stopPoint', [])
                
                # Find our starting station's index
                start_idx = None
                end_idx = None
                for i, stop in enumerate(stops):
                    if stop.get('id') == from_id:
                        start_idx = i
                    # Match destination by name since we don't have its ID
                    elif to_name in stop.get('name', ''):
                        end_idx = i
                        
                if start_idx is not None and end_idx is not None:
                    # Get intermediate stops
                    if start_idx < end_idx:
                        intermediate = stops[start_idx+1:end_idx]
                    else:
                        intermediate = stops[end_idx+1:start_idx][::-1]
                    
                    return [stop['name'].replace(' Underground Station', '').strip() 
                           for stop in intermediate]
            
            return None
            
        except APIError as e:
            logger.error(f"Failed to get intermediate stops for line {line_id}: {str(e)}")
            return None
            
    def get_stations(self, stations: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Get station information for specified stations
        
        Args:
            stations: List of station configurations with name and platform
            
        Returns:
            List of station dictionaries with status information
        """
        try:
            result = []
            for station_config in stations:
                station_name = station_config.get('name')
                platform = station_config.get('platform')
                
                # Get station status
                url = f"{self.base_url}/StopPoint/Search/{station_name}"
                response = self._make_request(url)
                if response and 'matches' in response:
                    for match in response['matches']:
                        if match.get('name') == station_name:
                            station = {
                                'name': station_name,
                                'platform': platform,
                                'status': {
                                    'description': 'Good Service',  # Default status
                                    'severity': 10  # Normal severity
                                }
                            }
                            
                            # Get line status
                            for line in match.get('lines', []):
                                line_id = line.get('id')
                                if line_id:
                                    url = f"{self.base_url}/Line/{line_id}/Status"
                                    status_response = self._make_request(url)
                                    if status_response:
                                        status = status_response[0].get('lineStatuses', [{}])[0]
                                        station['status'] = {
                                            'description': status.get('statusSeverityDescription', 'Good Service'),
                                            'severity': status.get('statusSeverity', 10)
                                        }
                                        break  # Use first line's status
                                        
                            result.append(station)
                            break  # Use first matching station
                            
            return result
            
        except APIError as e:
            logger.error(f"Failed to get station information: {str(e)}")
            return []
