from typing import List, Dict, Any, Optional, Tuple
import logging
from src.domain.models import TflStation, TflService

logger = logging.getLogger(__name__)

class TflProcessor:
    """Processor for TfL data"""
    
    def __init__(self, tfl_client, config: Dict[str, Any]):
        self.client = tfl_client
        self.config = config
        
    def get_station_data(self, screen_config: Dict[str, Any]) -> Tuple[Optional[List[Dict[str, Any]]], Optional[List[str]], str]:
        """Get processed station data including departures and calling points"""
        station_id = screen_config["departureStation"]
        out_of_hours_name = screen_config["outOfHoursName"]
        
        # Get station information
        station = self.client.get_station(station_id, self.config["tfl"]["mode"])
        if not station:
            logger.warning(f"Could not get TfL station data for {station_id}")
            return False, False, out_of_hours_name
            
        # Get arrival information
        services = self.client.get_arrivals(station, self.config)
        if not services:
            logger.warning(f"No arrivals found for station {station_id}")
            return False, False, out_of_hours_name
            
        # Convert services to display format
        departures = [service.to_display_format() for service in services]
        
        # Get calling points from first service
        calling_points = services[0].stops if services else []
        
        logger.info(f"Processed {len(departures)} departures for {station.name}")
        return departures, calling_points, station.name
        
    def filter_platform_departures(self, 
                                 departures: List[Dict[str, Any]], 
                                 platform_number: str,
                                 station_name: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[List[str]], str]:
        """Filter departures by platform number"""
        if not departures:
            return False, False, station_name
            
        if not platform_number:
            return departures, departures[0]["calling_at_list"], station_name
            
        filtered = []
        target_platform = str(platform_number).strip()
        logger.info(f"\nFiltering departures for platform {target_platform}")
        
        for departure in departures:
            platform = str(departure.get('platform', '')).strip()
            logger.info(f"Checking TfL service: platform={platform} display_platform={departure.get('display_platform', '')}")
            
            # Try exact match first
            if platform == target_platform:
                logger.info(f"Matched TfL service on platform {platform}")
                filtered.append(departure)
            # Then try extracting number from display_platform
            elif departure.get('display_platform', ''):
                display_platform = departure['display_platform']
                if 'Plat ' in display_platform:
                    display_num = display_platform.replace('Plat ', '').strip()
                    if display_num == target_platform:
                        logger.info(f"Matched TfL service on platform {platform}")
                        filtered.append(departure)
                
        logger.info(f"Found {len(filtered)} departures for platform {platform_number}")
        
        if filtered:
            return filtered, filtered[0]["calling_at_list"], station_name
        else:
            return False, False, station_name
