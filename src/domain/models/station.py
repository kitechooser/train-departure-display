from typing import List, Optional, Dict, Any

class Station:
    """Base station model"""
    def __init__(self, station_id: str, name: str):
        self.id = station_id
        self.name = name

class TflStation(Station):
    """TfL specific station model"""
    def __init__(self, station_data: Dict[str, Any]):
        station_id = station_data.get('id')
        name = station_data.get('commonName', station_data.get('name', 'Unknown Station'))
        super().__init__(station_id, name)
        self.available_lines: List[str] = []
        
    def add_available_lines(self, lines: List[str]) -> None:
        """Add available lines for this station"""
        self.available_lines = lines

    @classmethod
    def from_api_response(cls, response: Dict[str, Any], mode: str) -> Optional['TflStation']:
        """Create TflStation instance from API response"""
        if not response:
            return None
            
        station = cls(response)
        
        # Get lines from the initial response
        line_groups = response.get('lineModeGroups', [])
        if line_groups:
            for group in line_groups:
                if group['modeName'].lower() == mode.lower():
                    station.add_available_lines(group['lineIdentifier'])
                    break
        
        # If no lines found, try getting them from lines array
        if not station.available_lines and 'lines' in response:
            lines = [line['id'] for line in response['lines'] 
                    if line.get('modeName', '').lower() == mode.lower()]
            if lines:
                station.add_available_lines(lines)
                
        # Only return station if it has available lines
        return station if station.available_lines else None
