import json
import os
import re

def loadConfig():
    """Load configuration from config.json file with environment variable fallbacks
    
    Configuration fields:
    - refreshTime: Time in seconds between departure data updates (e.g., 180 = 3 minutes)
                  Controls how often new departure data is fetched and announcements are checked
    - fpsTime: Time in seconds between logging the effective FPS (frames per second) to the console
              Used for monitoring display performance (e.g., 180 = log FPS every 3 minutes)
              This only affects debug logging, not the actual display refresh rate
    - targetFPS: Target frames per second for the display (e.g., 70 = aim for 70 FPS)
                Controls how smoothly animations and updates are rendered
    """
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    
    try:
        with open(config_path, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # If config file doesn't exist or is invalid, start with empty dict
        data = {
            "journey": {},
            "api": {},
            "tfl": {},
            "screen1": {},
            "screen2": {}
        }
    
    # Add compiled regex pattern for hours
    data["hoursPattern"] = re.compile("^((2[0-3]|[0-1]?[0-9])-(2[0-3]|[0-1]?[0-9]))$")
    
    # Set defaults for core settings
    data.setdefault("refreshTime", 180)  # 3 minutes
    data.setdefault("targetFPS", 70)
    data.setdefault("fpsTime", 180)
    data.setdefault("screenRotation", 2)
    data.setdefault("screenBlankHours", "")
    data.setdefault("dualScreen", True)
    data.setdefault("previewMode", True)
    data.setdefault("debug", False)
    data.setdefault("headless", False)
    data.setdefault("firstDepartureBold", True)
    data.setdefault("showDepartureNumbers", True)
    
    # API settings
    data.setdefault("api", {})
    api = data["api"]
    api.setdefault("apiKey", os.getenv("apiKey"))  # Only required env var
    api.setdefault("operatingHours", "")
    
    # Screen 1 settings
    data.setdefault("screen1", {})
    screen1 = data["screen1"]
    screen1.setdefault("departureStation", "EAL")
    screen1.setdefault("destinationStation", "")
    screen1.setdefault("platform", "")
    screen1.setdefault("mode", "rail")
    screen1.setdefault("outOfHoursName", "London Paddington")
    screen1.setdefault("individualStationDepartureTime", False)
    screen1.setdefault("timeOffset", "0")
    
    # Screen 2 settings
    data.setdefault("screen2", {})
    screen2 = data["screen2"]
    screen2.setdefault("departureStation", "NFD")
    screen2.setdefault("destinationStation", "")
    screen2.setdefault("platform", "")
    screen2.setdefault("mode", "rail")
    screen2.setdefault("outOfHoursName", "Northfields")
    screen2.setdefault("individualStationDepartureTime", False)
    screen2.setdefault("timeOffset", "0")
    
    # TfL settings
    data.setdefault("tfl", {})
    tfl = data["tfl"]
    tfl.setdefault("enabled", True)
    tfl.setdefault("appId", "DepartureBoard")
    tfl.setdefault("appKey", "")
    tfl.setdefault("direction", "all")
    tfl.setdefault("refreshTime", 90)
    tfl.setdefault("mode", "tube")
    tfl.setdefault("platformStyle", "number")
        
    # Announcement settings with defaults
    data.setdefault("announcements", {})
    announcements = data["announcements"]
    announcements.setdefault("enabled", True)
    announcements.setdefault("muted", False)
    announcements.setdefault("volume", 80)
    announcements.setdefault("announcement_gap", 2.0)
    announcements.setdefault("max_queue_size", 10)
    announcements.setdefault("log_level", "DEBUG")  # Set to DEBUG for more verbose logging
    announcements.setdefault("operating_hours", "")  # Empty string means 24/7
    
    # Audio configuration defaults
    announcements.setdefault("audio", {
        "driver": "auto",      # auto, nsss (macOS), espeak (Linux/Pi)
        "device": "default",   # audio device name/id
        "macos_voice": "com.apple.voice.compact.en-GB.Daniel",     # specific voice for macOS
        "espeak_voice": "english-uk",  # specific voice for espeak (British English)
    })
    
    # Echo effect configuration
    announcements.setdefault("echo", {
        "enabled": True,       # Enable/disable echo effect
        "delay": 0.3,         # Delay between echoes in seconds
        "decay": 0.5,         # Volume reduction for each echo (0-1)
        "num_echoes": 3       # Number of echo repetitions
    })
    
    # Announcement types defaults
    announcements.setdefault("announcement_types", {
        "delays": True,
        "platform_changes": True,
        "cancellations": True,
        "on_time": False,
        "departures": False,
        "next_train": True  # Announce next train to arrive
    })
    
    # Add journey config for backwards compatibility
    data["journey"] = data.get("screen1", {}).copy()
    data["journey"]["stationAbbr"] = {"International": "Intl."}
    
    return data
