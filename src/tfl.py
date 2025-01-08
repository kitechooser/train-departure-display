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
    
    return [TflArrival(arrival, config) for arrival in arrivals]

def convert_tfl_arrivals(arrivals, mode):
    """Convert TfL arrivals to match National Rail format"""
    converted_arrivals = []
    for arr in arrivals:
        converted = {
            "platform": arr.platform,  # Use number for filtering
            "display_platform": arr.display_platform,  # Use direction for display
            "aimed_departure_time": arr.status,
            "expected_departure_time": arr.status,
            "destination_name": arr.destination,
            "calling_at_list": f"This is a {arr.line} line service to {arr.destination}. No intermediate stops available."
        }
        converted_arrivals.append(converted)
    return converted_arrivals
