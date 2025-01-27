from typing import Optional, List, Dict, Any
import logging
import requests
from .base_client import BaseAPIClient, APIError

logger = logging.getLogger(__name__)

class RailClient(BaseAPIClient):
    """National Rail API client"""
    
    def __init__(self, api_key: str, timeout: int = 10):
        super().__init__('https://lite.realtime.nationalrail.co.uk/OpenLDBWS/ldb11.asmx', timeout)
        self.api_key = api_key
        
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        return {
            'Content-Type': 'text/xml'
        }
        
    def get_departures(self, station: str, rows: str = "10", time_offset: str = "0", show_times: bool = True, platform: Optional[str] = None, destination: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get departures for a station
        
        Args:
            station: Station code (e.g. WAT for Waterloo)
            rows: Number of departures to return
            time_offset: Time offset in minutes
            show_times: Whether to show calling point times
            platform: Optional platform number to filter by
            destination: Optional destination station code to filter by
            
        Returns:
            List of departure dictionaries
        """
        # Create SOAP request
        soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:typ="http://thalesgroup.com/RTTI/2013-11-28/Token/types" xmlns:lt4="http://thalesgroup.com/RTTI/2017-10-01/ldb/" xmlns:lt5="http://thalesgroup.com/RTTI/2017-10-01/ldb/types" xmlns:lt7="http://thalesgroup.com/RTTI/2017-10-01/ldb/types">
    <soap:Header>
        <typ:AccessToken>
            <typ:TokenValue>{self.api_key}</typ:TokenValue>
        </typ:AccessToken>
    </soap:Header>
    <soap:Body>
        <lt4:GetDepBoardWithDetailsRequest>
            <lt4:numRows>{rows}</lt4:numRows>
            <lt4:crs>{station}</lt4:crs>
            <lt4:timeOffset>{time_offset}</lt4:timeOffset>
            <lt4:filterCrs>{destination if destination else ''}</lt4:filterCrs>
            <lt4:filterType>to</lt4:filterType>
            <lt4:timeWindow>120</lt4:timeWindow>
        </lt4:GetDepBoardWithDetailsRequest>
    </soap:Body>
</soap:Envelope>"""

        try:
            # Make direct request using requests library
            response = requests.post(
                self.base_url,
                data=soap_request,
                headers=self._get_auth_headers(),
                timeout=self.timeout
            )
            
            # Log response for debugging
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {response.headers}")
            logger.debug(f"Response text: {response.text}")
            
            # Parse response
            services = []
            
            # Extract services from XML using string operations since xmltodict is having issues
            xml = response.text
            
            # Check for SOAP fault before HTTP errors
            if '<soap:Fault>' in xml:
                fault_string_start = xml.find('<faultstring>') + len('<faultstring>')
                fault_string_end = xml.find('</faultstring>')
                fault_message = xml[fault_string_start:fault_string_end] if fault_string_start > -1 and fault_string_end > -1 else "Unknown SOAP fault"
                logger.error(f"SOAP fault received: {fault_message}")
                if 'TokenValue' in fault_message or 'Authentication' in fault_message:
                    raise APIError(f"Authentication failed: {fault_message}")
                return []
            
            # Check for HTTP errors after SOAP fault check
            response.raise_for_status()
                
            # Find train services section
            train_services_start = xml.find('<lt7:trainServices>')
            if train_services_start != -1:
                train_services_end = xml.find('</lt7:trainServices>', train_services_start)
                if train_services_end != -1:
                    train_services_xml = xml[train_services_start:train_services_end + len('</lt7:trainServices>')]
                    logger.debug(f"Found train services section: {train_services_xml}")
                    
                    # Count services in XML
                    service_count = train_services_xml.count('<lt7:service>')
                    logger.debug(f"Found {service_count} services in XML")
                    
                    # Find all service elements
                    service_start = '<lt7:service>'
                    service_end = '</lt7:service>'
                    
                    # Get index of first service
                    current_pos = 0
                    while True:
                        start_idx = train_services_xml.find(service_start, current_pos)
                        if start_idx == -1:
                            break
                            
                        end_idx = train_services_xml.find(service_end, start_idx) + len(service_end)
                        if end_idx == -1:
                            break
                            
                        service_xml = train_services_xml[start_idx:end_idx]
                        current_pos = end_idx
                        logger.debug(f"Processing service at position {current_pos}: {service_xml}")
                        logger.debug(f"Next service start: {train_services_xml.find('<lt7:service>', current_pos)}")
                        
                        # Extract service information using string operations
                        def extract_value(tag: str, prefix: str = 'lt4') -> str:
                            full_tag = f'{prefix}:{tag}'
                            start = service_xml.find(f'<{full_tag}>')
                            if start == -1:
                                return ''
                            start += len(full_tag) + 2
                            end = service_xml.find(f'</{full_tag}>')
                            if end == -1:
                                return ''
                            return service_xml[start:end]
                        
                        # Get destination from lt5:destination/lt4:location/lt4:locationName
                        dest_section_start = service_xml.find('<lt5:destination>')
                        if dest_section_start != -1:
                            dest_section_end = service_xml.find('</lt5:destination>', dest_section_start)
                            if dest_section_end != -1:
                                dest_section = service_xml[dest_section_start:dest_section_end]
                                # Find location within destination section
                                loc_start = dest_section.find('<lt4:location>')
                                if loc_start != -1:
                                    loc_end = dest_section.find('</lt4:location>', loc_start)
                                    if loc_end != -1:
                                        loc_section = dest_section[loc_start:loc_end]
                                        dest_start = loc_section.find('<lt4:locationName>') + len('<lt4:locationName>')
                                        dest_end = loc_section.find('</lt4:locationName>')
                                        destination_name = loc_section[dest_start:dest_end] if dest_start > -1 and dest_end > -1 else 'Unknown'
                                    else:
                                        destination_name = 'Unknown'
                                else:
                                    destination_name = 'Unknown'
                            else:
                                destination_name = 'Unknown'
                        else:
                            destination_name = 'Unknown'
                        
                        # Get platform
                        platform = extract_value('platform')
                        
                        # Get times
                        aimed_departure_time = extract_value('std')
                        expected_departure_time = extract_value('etd')
                        
                        # Get operator
                        operator = extract_value('operator')
                        
                        departure = {
                            'destination_name': destination_name,
                            'platform': platform,
                            'aimed_departure_time': aimed_departure_time,
                            'expected_departure_time': expected_departure_time,
                            'operator': operator,
                            'calling_at_list': []
                        }
                        
                        # Extract calling points
                        if '<lt7:callingPoint>' in service_xml:
                            calling_points = []
                            cp_xml = service_xml
                            while '<lt7:callingPoint>' in cp_xml:
                                cp_start = cp_xml.find('<lt7:callingPoint>') 
                                cp_end = cp_xml.find('</lt7:callingPoint>') + len('</lt7:callingPoint>')
                                if cp_start == -1 or cp_end == -1:
                                    break
                                    
                                cp_data = cp_xml[cp_start:cp_end]
                                cp_xml = cp_xml[cp_end:]
                                
                                def extract_cp_value(tag: str, prefix: str = 'lt7') -> str:
                                    full_tag = f'{prefix}:{tag}'
                                    start = cp_data.find(f'<{full_tag}>')
                                    if start == -1:
                                        return ''
                                    start += len(full_tag) + 2
                                    end = cp_data.find(f'</{full_tag}>')
                                    if end == -1:
                                        return ''
                                    return cp_data[start:end]
                                
                                # Get station name using extract_value with lt7 prefix
                                station_name = extract_cp_value('locationName')
                                
                                # Get scheduled time
                                time = ''
                                if show_times:
                                    scheduled_time = extract_cp_value('st')
                                    if scheduled_time:
                                        time = f" ({scheduled_time})"
                                
                                if station_name:  # Only append if we got a valid station name
                                    calling_points.append(f"{station_name}{time}")
                                    
                            if calling_points:  # Only set if we have valid calling points
                                departure['calling_at_list'] = calling_points
                        
                        services.append(departure)
                        logger.debug(f"Added service to list: {departure}")
                        logger.debug(f"Current services list: {services}")
                    
            logger.debug(f"Final services list: {services}")
            return services
            
        except requests.exceptions.RequestException as e:
            if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
                # Check for SOAP fault in error response
                xml = e.response.text
                if '<soap:Fault>' in xml:
                    fault_string_start = xml.find('<faultstring>') + len('<faultstring>')
                    fault_string_end = xml.find('</faultstring>')
                    fault_message = xml[fault_string_start:fault_string_end] if fault_string_start > -1 and fault_string_end > -1 else "Unknown SOAP fault"
                    if 'TokenValue' in fault_message or 'Authentication' in fault_message:
                        raise APIError(f"Authentication failed: {fault_message}")
            logger.error(f"Failed to get departures for station {station}: {str(e)}")
            return []
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Error processing departures for station {station}: {str(e)}")
            return []
