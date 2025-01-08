import requests
from typing import List, Dict, Any
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class Station:
    id: str
    name: str
    short_name: str
    station_code: str  # Added station_code field for three-letter code
    lat: float
    lon: float
    lines: List[str]

class TflAPI:
    def __init__(self, app_id: str, app_key: str):
        self.app_id = app_id
        self.app_key = app_key
        self.base_url = "https://api.tfl.gov.uk"
        
    def _make_request(self, endpoint: str) -> Dict[str, Any]:
        """Make a GET request to the TfL API."""
        url = f"{self.base_url}{endpoint}"
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_rail_lines(self) -> List[Dict[str, Any]]:
        """Fetch all rail lines including tube and Elizabeth line."""
        tube_lines = self._make_request("/Line/Mode/tube")
        elizabeth_line = self._make_request("/Line/Mode/elizabeth-line")
        return tube_lines + elizabeth_line
    
    def get_stations_for_line(self, line_id: str) -> List[Dict[str, Any]]:
        """Fetch all stations for a specific line."""
        return self._make_request(f"/Line/{line_id}/StopPoints")
    
    def extract_station_code(self, station: Dict[str, Any]) -> str:
        """Extract the three-letter station code from station data."""
        # Try different potential locations for the station code
        if "stationNaptan" in station:
            return station["stationNaptan"]
        
        # Try to extract from additional properties
        additional_properties = station.get("additionalProperties", [])
        for prop in additional_properties:
            if prop.get("key") == "NaptanCode":
                return prop["value"][:3]  # Take first 3 letters if longer
        
        # Check if it's in the station codes
        station_codes = station.get("stationCodes", [])
        if station_codes and len(station_codes) > 0:
            return station_codes[0][:3]
            
        # If no code found, create one from the name
        name = station["commonName"].replace(" Underground Station", "").replace(" Station", "")
        words = name.split()
        if len(words) >= 3:
            return f"{words[0][0]}{words[1][0]}{words[2][0]}".upper()
        elif len(words) == 2:
            return f"{words[0][:2]}{words[1][0]}".upper()
        else:
            return name[:3].upper()

    def get_all_stations(self) -> List[Station]:
        """Fetch and process all tube stations."""
        lines = self.get_rail_lines()
        stations_dict = {}
        
        for line in lines:
            line_id = line["id"]
            try:
                stations = self.get_stations_for_line(line_id)
                
                for station in stations:
                    station_id = station["id"]
                    
                    if station_id not in stations_dict:
                        # Create new station entry
                        stations_dict[station_id] = Station(
                            id=station_id,
                            name=station["commonName"],
                            short_name=station.get("shortName", station["commonName"]),
                            station_code=self.extract_station_code(station),
                            lat=station["lat"],
                            lon=station["lon"],
                            lines=[line_id]
                        )
                    else:
                        # Add line to existing station
                        if line_id not in stations_dict[station_id].lines:
                            stations_dict[station_id].lines.append(line_id)
                            
            except requests.exceptions.RequestException as e:
                print(f"Error fetching stations for line {line_id}: {e}")
        
        return list(stations_dict.values())

def analyze_stations(stations: List[Station]) -> None:
    """Analyze and print information about the stations."""
    print(f"\nTotal number of stations: {len(stations)}")
    
    interchange_stations = [s for s in stations if len(s.lines) > 1]
    print(f"\nNumber of interchange stations: {len(interchange_stations)}")
    
    stations_by_lines = defaultdict(list)
    for station in stations:
        stations_by_lines[len(station.lines)].append(station)
    
    print("\nStations by number of lines served:")
    for num_lines in sorted(stations_by_lines.keys()):
        stations = stations_by_lines[num_lines]
        print(f"\n{num_lines} line{'s' if num_lines > 1 else ''} "
              f"({len(stations)} stations):")
        for station in sorted(stations, key=lambda x: x.name):
            print(f"  - {station.name} ({station.short_name}) [{station.station_code}]: "
                  f"{', '.join(sorted(station.lines))}")

def main():
    # Replace with your API credentials
    APP_ID = "DepartureBoard"
    APP_KEY = "a432a817f61d4a65ba62e226e48e665b"
    
    try:
        tfl = TflAPI(APP_ID, APP_KEY)
        print("Fetching stations...")
        stations = tfl.get_all_stations()
        analyze_stations(stations)
        
    except requests.exceptions.RequestException as e:
        print(f"Error accessing TfL API: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()