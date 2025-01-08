# config.py additions
def loadConfig():
    data = {
        "journey": {},
        "api": {},
        "tfl": {}  # New TfL section
    }
    
    # Existing config loading...
    
    # Add TfL specific configuration
    data["tfl"]["enabled"] = False
    if os.getenv("tflEnabled") == "True":
        data["tfl"]["enabled"] = True
    
    data["tfl"]["appId"] = os.getenv("tflAppId") or None
    data["tfl"]["appKey"] = os.getenv("tflAppKey") or None
    data["tfl"]["direction"] = os.getenv("tflDirection") or "inbound"
    data["tfl"]["refreshTime"] = int(os.getenv("tflRefreshTime") or 90)
    data["tfl"]["mode"] = os.getenv("tflMode") or "tube"
    
    return data

# New tfl.py file
import requests
import math
from datetime import datetime
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
        raise ValueError(f'TfL API Error: {response.status_code}')
    except Exception as e:
        print(f"TfL API Error: {str(e)}")
        return None

def get_tfl_station(config):
    station = config["journey"]["departureStation"]
    
    # Query TfL API for station
    url = f'https://api.tfl.gov.uk/StopPoint/Search'
    params = {
        'query': station,
        'modes': config["tfl"]["mode"],
        'app_id': config["tfl"]["appId"],
        'app_key': config["tfl"]["appKey"]
    }
    
    response = query_tfl(url, params)
    if not response or not response.get('matches'):
        return None
        
    station_data = response['matches'][0]
    tfl_station = TflStation(station_data)
    
    # Get available lines
    url = f'https://api.tfl.gov.uk/StopPoint/{tfl_station.id}'
    response = query_tfl(url, params)
    
    if response:
        for group in response.get('lineModeGroups', []):
            if group['modeName'] == config["tfl"]["mode"]:
                tfl_station.add_available_lines(group['lineIdentifier'])
                
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

# Modifications to main.py

def loadData(apiConfig, journeyConfig, config):
    if config["tfl"]["enabled"]:
        # Try TfL data first
        tfl_station = get_tfl_station(config)
        if tfl_station:
            arrivals = get_tfl_arrivals(config, tfl_station)
            if arrivals:
                # Convert TfL arrivals to match National Rail format
                converted_arrivals = []
                for arr in arrivals:
                    converted = {
                        "platform": arr.platform,
                        "aimed_departure_time": arr.status,
                        "expected_departure_time": arr.status,
                        "destination_name": arr.destination,
                        "calling_at_list": f"This is a {config['tfl']['mode'].upper()} service to {arr.destination}"
                    }
                    converted_arrivals.append(converted)
                return converted_arrivals, True, tfl_station.name
    
    # Fall back to National Rail if TfL failed or disabled
    return original_loadData(apiConfig, journeyConfig, config)
