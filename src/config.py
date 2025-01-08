import json
import os
import re

def loadConfig():
    """Load configuration from config.json file with environment variable fallbacks"""
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
    
    # Use environment variables as fallback for critical settings
    if not data.get("api", {}).get("apiKey"):
        data.setdefault("api", {})["apiKey"] = os.getenv("apiKey")
    
    # TfL settings
    data.setdefault("tfl", {})
    if not data["tfl"].get("enabled"):
        data["tfl"]["enabled"] = os.getenv("tflEnabled") == "True"
    
    # Screen 1 fallbacks
    data.setdefault("screen1", {})
    if not data["screen1"].get("departureStation"):
        data["screen1"]["departureStation"] = os.getenv("departureStation") or "EAL"
    if not data["screen1"].get("mode"):
        data["screen1"]["mode"] = os.getenv("screen1Mode") or "rail"
    
    # Screen 2 fallbacks
    data.setdefault("screen2", {})
    if not data["screen2"].get("departureStation"):
        data["screen2"]["departureStation"] = os.getenv("screen2DepartureStation") or "NFD"
    if not data["screen2"].get("mode"):
        data["screen2"]["mode"] = os.getenv("screen2Mode") or "rail"
    
    # Add journey config for backwards compatibility
    data["journey"] = data.get("screen1", {}).copy()
    data["journey"]["stationAbbr"] = {"International": "Intl."}
    
    return data
