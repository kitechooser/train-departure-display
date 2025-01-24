from typing import List, Dict, Any, Optional
import math
import time

class Service:
    """Base service model"""
    def __init__(self):
        self.platform: str = ''
        self.display_platform: str = ''
        self.destination: str = ''
        self.calling_points: List[str] = []

class TflService(Service):
    """TfL specific service model"""
    def __init__(self, item: Dict[str, Any], config: Dict[str, Any]):
        super().__init__()
        self.line = item.get('lineName', 'Underground')
        self._process_platform(item.get('platformName', ''), config["tfl"].get("platformStyle", "direction"))
        self.destination = self._format_destination(item.get('destinationName', ''))
        self.time_to_station = item.get('timeToStation', 0)
        self.expected_arrival = time.time() + self.time_to_station
        self.line_id = item.get('lineId', '')
        self.stops: Optional[List[str]] = None
        self.status = self._get_status()
        
    def _process_platform(self, platform: str, platform_style: str) -> None:
        """Process platform information"""
        if not platform:
            self.platform = ''
            self.display_platform = ''
            return
            
        # Extract platform number for filtering
        numbers = ''.join(c for c in platform if c.isdigit())
        platform_num = numbers if numbers else platform
        
        # Map TfL platform numbers to display platform numbers
        # At Northfields:
        # Platform 1 (Westbound) -> Platform 3 (Display)
        # Platform 2 (Eastbound) -> Platform 4 (Display)
        platform_lower = platform.lower()
        if 'westbound' in platform_lower:
            self.platform = '3'  # Westbound is platform 3
        elif 'eastbound' in platform_lower:
            self.platform = '4'  # Eastbound is platform 4
        else:
            self.platform = platform_num
        
        # Set display format based on style
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
        
    def _format_destination(self, name: str) -> str:
        """Format destination name"""
        return name.replace('Underground Station', '').replace('DLR Station', '').strip()
        
    def _get_status(self) -> str:
        """Get human-readable status"""
        if self.time_to_station < 30:
            return "Due"
        elif self.time_to_station < 60:
            return "1 min"
        else:
            return f"{math.ceil(self.time_to_station/60)} mins"
            
    def is_delayed(self) -> bool:
        """Check if service is significantly delayed"""
        return False  # TfL API doesn't provide delay information
        
    def to_display_format(self) -> Dict[str, Any]:
        """Convert to format expected by display system"""
        # Format calling points if available
        if self.stops:
            calling_at = f"This is a {self.line} line service to {self.destination}, calling at " + ", ".join(self.stops)
        else:
            calling_at = f"This is a {self.line} line service to {self.destination}"
            
        return {
            "platform": self.platform,  # Use number for filtering
            "display_platform": self.display_platform,  # Use direction for display
            "aimed_departure_time": self.status,
            "expected_departure_time": "On time",  # Always on time since TfL API doesn't provide delay info
            "destination_name": self.destination,
            "calling_at_list": calling_at,
            "is_tfl": True,  # Mark as TfL service
            "line": self.line,  # Add line info for announcements
            "mode": "tfl"  # Explicitly mark as TfL mode
        }

    @classmethod
    def from_api_response(cls, response: Dict[str, Any], config: Dict[str, Any]) -> List['TflService']:
        """Create TflService instances from API response"""
        if not response:
            return []
            
        # Sort by arrival time
        arrivals = sorted(response, key=lambda k: k.get('timeToStation', 0))
        
        return [cls(arrival, config) for arrival in arrivals]
