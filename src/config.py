import os
import re

# validate platform number
def parsePlatformData(platform):
    if platform is None:
        return ""
    elif bool(re.match(r'^(?:\d{1,2}[A-D]|[A-D]|\d{1,2})$', platform)):
        return platform
    else:
        return ""

def loadConfig():
    data = {
        "journey": {},
        "api": {},
        "tfl": {},
        "screen1": {},  # Screen-specific configs
        "screen2": {}
    }

    # Load base configuration
    data["targetFPS"] = int(os.getenv("targetFPS") or 70)
    data["refreshTime"] = int(os.getenv("refreshTime") or 180)
    data["fpsTime"] = int(os.getenv("fpsTime") or 180)
    data["screenRotation"] = int(os.getenv("screenRotation") or 2)
    data["screenBlankHours"] = os.getenv("screenBlankHours") or ""
    data["headless"] = os.getenv("headless") == "True"
    data["previewMode"] = os.getenv("previewMode") == "True"
    data["debug"] = False
    if os.getenv("debug") == "True":
        data["debug"] = True
    elif os.getenv("debug") and os.getenv("debug").isnumeric():
        data["debug"] = int(os.getenv("debug"))

    data["dualScreen"] = os.getenv("dualScreen") == "True"
    data["firstDepartureBold"] = os.getenv("firstDepartureBold") != "False"
    data["hoursPattern"] = re.compile("^((2[0-3]|[0-1]?[0-9])-(2[0-3]|[0-1]?[0-9]))$")
    data["showDepartureNumbers"] = os.getenv("showDepartureNumbers") == "True"

    # Screen 1 configuration (default/backwards compatible)
    data["screen1"]["departureStation"] = os.getenv("departureStation") or "PAD"
    data["screen1"]["destinationStation"] = os.getenv("destinationStation") or ""
    data["screen1"]["platform"] = parsePlatformData(os.getenv("screen1Platform"))
    data["screen1"]["mode"] = os.getenv("screen1Mode") or "rail"  # 'rail' or 'tfl'
    data["screen1"]["outOfHoursName"] = os.getenv("outOfHoursName") or "London Paddington"
    data["screen1"]["individualStationDepartureTime"] = os.getenv("individualStationDepartureTime") == "True"
    data["screen1"]["timeOffset"] = os.getenv("timeOffset") or "0"
    
    # Screen 2 configuration
    data["screen2"]["departureStation"] = os.getenv("screen2DepartureStation") or ""
    data["screen2"]["destinationStation"] = os.getenv("screen2DestinationStation") or ""
    data["screen2"]["platform"] = parsePlatformData(os.getenv("screen2Platform"))
    data["screen2"]["mode"] = os.getenv("screen2Mode") or "rail"
    data["screen2"]["outOfHoursName"] = os.getenv("outOfHoursName") or data["screen2"]["departureStation"]
    data["screen2"]["individualStationDepartureTime"] = os.getenv("individualStationDepartureTime") == "True"
    data["screen2"]["timeOffset"] = os.getenv("timeOffset") or "0"

    # Move screen1 config into journey for backwards compatibility
    data["journey"] = data["screen1"]
    data["journey"]["stationAbbr"] = {"International": "Intl."}

    # Load API configs
    data["api"]["apiKey"] = os.getenv("apiKey") or None
    data["api"]["operatingHours"] = os.getenv("operatingHours") or ""
    
    # Add TfL specific configuration
    data["tfl"]["enabled"] = os.getenv("tflEnabled") == "True"
    data["tfl"]["appId"] = os.getenv("tflAppId") or None
    data["tfl"]["appKey"] = os.getenv("tflAppKey") or None
    data["tfl"]["direction"] = os.getenv("tflDirection") or "inbound"
    data["tfl"]["refreshTime"] = int(os.getenv("tflRefreshTime") or 90)
    data["tfl"]["mode"] = os.getenv("tflMode") or "tube"

    return data
