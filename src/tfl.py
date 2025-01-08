import requests
import math
import time

class TflStation:
    def __init__(self, station_data):
        self.id = station_data.get('id')
        self.name = station_data.get('name')
        self.available_lines = []
        
    def add_available_lines(self, lines):
        self.available_lines = lines

class TflArrival:
    def __init__(self, item):
        self.platform = item.get('platformName', '')
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
    # Convert station codes to full names for TfL API
    station_names = {
        'VIC': 'Victoria Underground Station',
        'PAD': 'Paddington Underground Station',
        'WAT': 'Waterloo Underground Station',
        'KGX': 'King\'s Cross St. Pancras Underground Station',
        'LBG': 'London Bridge Underground Station',
        'EUS': 'Euston Underground Station'
    }
    
    station = screen_config["departureStation"]
    station_name = station_names.get(station, station)
    print(f"Searching for TfL station: {station_name}")
    
    # Query TfL API for station
    url = 'https://api.tfl.gov.uk/StopPoint/Search'
    params = {
        'query': station_name,
        'modes': config["tfl"]["mode"],
        'app_id': config["tfl"]["appId"],
        'app_key': config["tfl"]["appKey"],
        'faresOnly': 'false',
        'maxResults': 1,
        'includeHubs': 'false'
    }
    
    response = query_tfl(url, params)
    if not response:
        print(f"No response from TfL API for station search: {station}")
        return None
        
    matches = response.get('matches', [])
    if not matches:
        print(f"No matches found for station: {station}")
        return None
        
    station_data = matches[0]
    if not station_data.get('id'):
        print(f"No station ID found in response for: {station}")
        return None
        
    tfl_station = TflStation(station_data)
    
    # Get available lines
    url = f'https://api.tfl.gov.uk/StopPoint/{tfl_station.id}'
    params = {
        'app_id': config["tfl"]["appId"],
        'app_key': config["tfl"]["appKey"]
    }
    
    response = query_tfl(url, params)
    if not response:
        print(f"No response from TfL API for stop point details: {tfl_station.id}")
        return None
        
    line_groups = response.get('lineModeGroups', [])
    if not line_groups:
        print(f"No line groups found for station: {tfl_station.id}")
        return None
        
    for group in line_groups:
        if group['modeName'].lower() == config["tfl"]["mode"].lower():
            tfl_station.add_available_lines(group['lineIdentifier'])
            break
    
    if not tfl_station.available_lines:
        print(f"No {config['tfl']['mode']} lines found for station: {tfl_station.id}")
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
    return [TflArrival(arrival) for arrival in arrivals]

def convert_tfl_arrivals(arrivals, mode):
    """Convert TfL arrivals to match National Rail format"""
    converted_arrivals = []
    for arr in arrivals:
        converted = {
            "platform": arr.platform,
            "aimed_departure_time": arr.status,
            "expected_departure_time": arr.status,
            "destination_name": arr.destination,
            "calling_at_list": f"This is a {mode.upper()} service to {arr.destination}"
        }
        converted_arrivals.append(converted)
    return converted_arrivals
