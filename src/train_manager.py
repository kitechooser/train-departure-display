import requests
from trains import loadDeparturesForStation
from tfl import get_tfl_station, get_tfl_arrivals, convert_tfl_arrivals
from open import isRun

def platform_filter(departureData, platformNumber, station):
    """Filter departures by platform number, handling both TfL and National Rail formats"""
    print(f"\nFiltering departures for platform {platformNumber}")
    platformDepartures = []
    for sub in departureData:
        # If no platform filter specified, include all departures
        if platformNumber == "":
            platformDepartures.append(sub)
            continue
            
        # For TfL services, check both platform and display_platform
        if sub.get("is_tfl"):
            print(f"Checking TfL service: platform={sub.get('platform')}, display_platform={sub.get('display_platform')}")
            platform = str(sub.get('platform', '')).strip()
            if platform == str(platformNumber).strip():
                print(f"Matched TfL service on platform {platform}")
                platformDepartures.append(sub)
                continue
                
        # For National Rail services, check platform field
        elif sub.get('platform') is not None:
            platform = str(sub['platform']).strip()
            if platform == str(platformNumber).strip():
                print(f"Matched National Rail service on platform {platform}")
                platformDepartures.append(sub)
                continue
                
    print(f"Found {len(platformDepartures)} departures for platform {platformNumber}")
    
    if len(platformDepartures) > 0:
        firstDepartureDestinations = platformDepartures[0]["calling_at_list"]
        platformData = platformDepartures, firstDepartureDestinations, station
    else:
        # Return False to trigger blank signage with station name
        platformData = False, False, station

    return platformData

def load_data(apiConfig, screenConfig, config):
    """Load departure data based on screen mode (rail or tfl)"""
    if screenConfig["mode"] == "tfl" and config["tfl"]["enabled"]:
        print(f"\nProcessing TfL data for station {screenConfig['departureStation']}")
        # Try TfL data
        tfl_station = get_tfl_station(config, screenConfig)
        if tfl_station:
            print(f"Got TfL station: {tfl_station.name}")
            arrivals = get_tfl_arrivals(config, tfl_station)
            if arrivals:
                print(f"Got {len(arrivals)} TfL arrivals")
                converted_arrivals = convert_tfl_arrivals(arrivals, config["tfl"]["mode"])
                if converted_arrivals:
                    print(f"Converted {len(converted_arrivals)} TfL arrivals:")
                    for arr in converted_arrivals:
                        print(f"- {arr.get('line', 'Unknown')} line to {arr['destination_name']} from {arr.get('display_platform', 'Unknown platform')} in {arr['aimed_departure_time']}")
                    print("Setting is_tfl flag for announcements")
                    for arr in converted_arrivals:
                        arr['is_tfl'] = True
                    return converted_arrivals, converted_arrivals[0]["calling_at_list"], tfl_station.name
                else:
                    print("No arrivals after conversion")
            else:
                print("No TfL arrivals found")
        else:
            print("Could not get TfL station data")
        return False, False, screenConfig["outOfHoursName"]
    else:
        # Load National Rail data
        runHours = []
        if config['hoursPattern'].match(apiConfig['operatingHours']):
            runHours = [int(x) for x in apiConfig['operatingHours'].split('-')]

        if len(runHours) == 2 and isRun(runHours[0], runHours[1]) is False:
            return False, False, screenConfig['outOfHoursName']

        # set rows to 10 (max allowed) to get as many departure as poss
        rows = "10"

        try:
            departures, stationName = loadDeparturesForStation(
                screenConfig, apiConfig["apiKey"], rows)

            if departures is None:
                return False, False, stationName

            firstDepartureDestinations = departures[0]["calling_at_list"]
            return departures, firstDepartureDestinations, stationName
        except requests.RequestException as err:
            print("Error: Failed to fetch data from OpenLDBWS")
            print(err.__context__)
            return False, False, screenConfig['outOfHoursName']
