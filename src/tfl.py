import requests
import math
import time

class TflStation:
    def __init__(self, station_data):
        self.id = station_data.get('id')
        self.name = station_data.get('commonName', station_data.get('name', 'Unknown Station'))
        self.available_lines = []
        
    def add_available_lines(self, lines):
        self.available_lines = lines

class TflArrival:
    def __init__(self, item, config):
        platform = item.get('platformName', '')
        platform_style = config["tfl"].get("platformStyle", "direction")
        self.line = item.get('lineName', 'Underground')
        
        if not platform:
            self.platform = ''
            self.display_platform = ''
            return
            
        # Extract platform number for filtering
        numbers = ''.join(c for c in platform if c.isdigit())
        self.platform = numbers if numbers else platform
        
        # Set display format based on style
        platform_lower = platform.lower()
        if platform_style == "direction":
            if 'westbound' in platform_lower:
                self.display_platform = 'Westbound'
            elif 'eastbound' in platform_lower:
                self.display_platform = 'Eastbound'
            elif 'northbound' in platform_lower:
                self.display_platform = 'Northbound'
            elif 'southbound' in platform_lower:
                self.display_platform = 'Southbound'
            else:
                self.display_platform = f"Plat {self.platform}"
        else:
            self.display_platform = f"Plat {self.platform}"
        self.expected_arrival = time.time() + item['timeToStation']
        self.destination = self._format_destination(item['destinationName'])
        self.time_to_station = item['timeToStation']
        self.status = self._get_status()
        
    def _format_destination(self, name):
        return name.replace('Underground Station', '').replace('DLR Station', '').strip()
        
    def _get_status(self):
        if self.time_to_station < 30:
            return "Due"
        elif self.time_to_station < 60:
            return "1 min"
        else:
            return f"{math.ceil(self.time_to_station/60)} mins"
            
    def is_delayed(self):
        """Check if service is significantly delayed"""
        return False  # TfL API doesn't provide delay information

def query_tfl(url, params):
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        print(f"TfL API Error: Status {response.status_code} for URL {url}")
        if response.status_code != 404:  # Log response content for non-404 errors
            print(f"Response content: {response.text}")
        return None
    except Exception as e:
        print(f"TfL API Error: {str(e)}")
        return None

def get_tfl_station(config, screen_config):
    station_id = screen_config["departureStation"]
    print(f"Looking up TfL station: {station_id}")
    
    # Direct StopPoint lookup using NAPTAN code
    url = f'https://api.tfl.gov.uk/StopPoint/{station_id}'
    params = {
        'app_id': config["tfl"]["appId"],
        'app_key': config["tfl"]["appKey"]
    }
    
    response = query_tfl(url, params)
    if not response:
        print(f"No response from TfL API for station: {station_id}")
        return None
    
    # Create station from direct response
    tfl_station = TflStation(response)
    
    # Ensure we have a valid station name
    if not tfl_station.name:
        tfl_station.name = station_id
    
    # Get lines from the initial response
    line_groups = response.get('lineModeGroups', [])
    if line_groups:
        for group in line_groups:
            if group['modeName'].lower() == config["tfl"]["mode"].lower():
                tfl_station.add_available_lines(group['lineIdentifier'])
                break
    
    # If no lines found, try getting them from lines array
    if not tfl_station.available_lines and 'lines' in response:
        lines = [line['id'] for line in response['lines'] 
                if line.get('modeName', '').lower() == config["tfl"]["mode"].lower()]
        if lines:
            tfl_station.add_available_lines(lines)
    
    if not tfl_station.available_lines:
        print(f"No {config['tfl']['mode']} lines found for station: {station_id}")
        return None
                
    return tfl_station

def get_intermediate_stops(config, line_id, from_id, to_name):
    """Get intermediate stops between two stations on a line"""
    url = f'https://api.tfl.gov.uk/Line/{line_id}/Route/Sequence/all'
    params = {
        'app_id': config["tfl"]["appId"],
        'app_key': config["tfl"]["appKey"]
    }
    
    response = query_tfl(url, params)
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

def get_tfl_arrivals(config, station):
    if not station or not station.available_lines:
        return []
        
    url = f'https://api.tfl.gov.uk/Line/{",".join(station.available_lines)}/Arrivals/{station.id}'
    params = {
        'app_id': config["tfl"]["appId"],
        'app_key': config["tfl"]["appKey"],
        'direction': config["tfl"]["direction"]
    }
    
    response = query_tfl(url, params)
    if not response:
        return []
        
    # Sort by arrival time
    arrivals = sorted(response, key=lambda k: k['timeToStation'])
    
    tfl_arrivals = []
    for arrival in arrivals:
        tfl_arrival = TflArrival(arrival, config)
        # Get intermediate stops
        if tfl_arrival.line and station.id:
            tfl_arrival.stops = get_intermediate_stops(
                config, 
                arrival.get('lineId', ''), 
                station.id, 
                tfl_arrival.destination
            )
        tfl_arrivals.append(tfl_arrival)
    
    return tfl_arrivals

def convert_tfl_arrivals(arrivals, mode):
    """Convert TfL arrivals to match National Rail format"""
    print("\nConverting TfL arrivals:")
    converted_arrivals = []
    for arr in arrivals:
        status = arr.status
        # Format calling points if available
        if hasattr(arr, 'stops') and arr.stops:
            calling_at = f"This is a {arr.line} line service to {arr.destination}, calling at " + ", ".join(arr.stops)
        else:
            calling_at = f"This is a {arr.line} line service to {arr.destination}"
            
        converted = {
            "platform": arr.platform,  # Use number for filtering
            "display_platform": arr.display_platform,  # Use direction for display
            "aimed_departure_time": status,
            "expected_departure_time": "On time",  # Always on time since TfL API doesn't provide delay info
            "destination_name": arr.destination,
            "calling_at_list": calling_at,
            "is_tfl": True,  # Mark as TfL service
            "line": arr.line,  # Add line info for announcements
            "mode": "tfl"  # Explicitly mark as TfL mode
        }
        print(f"Converted TfL arrival: {arr.line} line to {arr.destination} from {arr.display_platform} in {status}")
        converted_arrivals.append(converted)
    print(f"Returning {len(converted_arrivals)} converted TfL arrivals")
    return converted_arrivals
