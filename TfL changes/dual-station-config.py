"""
# Screen 1 (original station)
departureStation=PAD
destinationStation=BRI
screen1Platform=1
screen1Mode=rail

# Screen 2 (new station)
screen2DepartureStation=VIC
screen2DestinationStation=
screen2Platform=
screen2Mode=tfl
"""



# config.py modifications

def loadConfig():
    data = {
        "journey": {},
        "api": {},
        "tfl": {},
        "screen1": {},  # New screen-specific configs
        "screen2": {}
    }
    
    # Base config loading stays the same
    data["targetFPS"] = int(os.getenv("targetFPS") or 70)
    data["refreshTime"] = int(os.getenv("refreshTime") or 180)
    # ... other base configs ...
    
    # Screen 1 configuration (default/backwards compatible)
    data["screen1"]["departureStation"] = os.getenv("departureStation") or "PAD"
    data["screen1"]["destinationStation"] = os.getenv("destinationStation") or ""
    data["screen1"]["platform"] = parsePlatformData(os.getenv("screen1Platform"))
    data["screen1"]["mode"] = os.getenv("screen1Mode") or "rail"  # 'rail' or 'tfl'
    
    # Screen 2 configuration (new)
    data["screen2"]["departureStation"] = os.getenv("screen2DepartureStation") or ""
    data["screen2"]["destinationStation"] = os.getenv("screen2DestinationStation") or ""
    data["screen2"]["platform"] = parsePlatformData(os.getenv("screen2Platform"))
    data["screen2"]["mode"] = os.getenv("screen2Mode") or "rail"
    
    # Move journey config into screen1 for backwards compatibility
    data["journey"] = data["screen1"]
    
    return data

# New station_data.py file for handling multiple station data
class StationData:
    def __init__(self, config, screen_config):
        self.config = config
        self.screen_config = screen_config
        self.departures = []
        self.station_name = ""
        self.last_update = 0
    
    def needs_refresh(self):
        refresh_time = self.config["refreshTime"]
        if self.screen_config["mode"] == "tfl":
            refresh_time = self.config["tfl"]["refreshTime"]
        return (time.time() - self.last_update) >= refresh_time
    
    def load_data(self):
        if self.screen_config["mode"] == "tfl":
            tfl_station = get_tfl_station(self.config)
            if tfl_station:
                arrivals = get_tfl_arrivals(self.config, tfl_station)
                if arrivals:
                    self.departures = convert_tfl_arrivals(arrivals)
                    self.station_name = tfl_station.name
        else:
            departures, _, station_name = loadDeparturesForStation(
                self.screen_config,
                self.config["api"]["apiKey"],
                "10"
            )
            if departures:
                self.departures = platform_filter(
                    departures,
                    self.screen_config["platform"],
                    station_name
                )
            self.station_name = station_name
        
        self.last_update = time.time()
        return self.departures, self.station_name

# Modifications to main.py

def main():
    config = loadConfig()
    
    # Initialize displays
    device = init_primary_display(config)
    device1 = init_secondary_display(config) if config["dualScreen"] else None
    
    # Initialize station data handlers
    screen1_data = StationData(config, config["screen1"])
    screen2_data = StationData(config, config["screen2"])
    
    while True:
        # Update screen 1
        if screen1_data.needs_refresh():
            departures, station_name = screen1_data.load_data()
            virtual = draw_signage(device, departures, station_name)
            virtual.refresh()
        
        # Update screen 2 if enabled
        if device1 and screen2_data.needs_refresh():
            departures, station_name = screen2_data.load_data()
            virtual1 = draw_signage(device1, departures, station_name)
            virtual1.refresh()
        
        time.sleep(0.1)  # Prevent CPU overload
