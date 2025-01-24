import requests
import logging
from src.trains import loadDeparturesForStation
from src.tfl import get_tfl_station, get_tfl_arrivals, convert_tfl_arrivals
from src.open import isRun
from src.api import TflClient
from src.domain.processors import TflProcessor

logger = logging.getLogger(__name__)

# Initialize clients and processors when migration is enabled
_tfl_client = None
_tfl_processor = None

def _get_tfl_client(config):
    """Get or create TfL client"""
    global _tfl_client
    if not _tfl_client and config["migration"]["use_new_tfl_client"]:
        _tfl_client = TflClient(
            app_id=config["tfl"]["appId"],
            app_key=config["tfl"]["appKey"]
        )
    return _tfl_client

def _get_tfl_processor(config):
    """Get or create TfL processor"""
    global _tfl_processor
    if not _tfl_processor and config["migration"]["use_new_tfl_client"]:
        _tfl_processor = TflProcessor(_get_tfl_client(config), config)
    return _tfl_processor

def platform_filter(departureData, platformNumber, station):
    """Filter departures by platform number, handling both TfL and National Rail formats"""
    logger.info(f"\nFiltering departures for platform {platformNumber}")
    platformDepartures = []
    for sub in departureData:
        # If no platform filter specified, include all departures
        if platformNumber == "":
            platformDepartures.append(sub)
            continue
            
        # For TfL services, check both platform and display_platform
        if sub.get("is_tfl"):
            logger.info(f"Checking TfL service: platform={sub.get('platform')}, display_platform={sub.get('display_platform')}")
            platform = str(sub.get('platform', '')).strip()
            if platform == str(platformNumber).strip():
                logger.info(f"Matched TfL service on platform {platform}")
                platformDepartures.append(sub)
                continue
                
        # For National Rail services, check platform field
        elif sub.get('platform') is not None:
            platform = str(sub['platform']).strip()
            if platform == str(platformNumber).strip():
                logger.info(f"Matched National Rail service on platform {platform}")
                platformDepartures.append(sub)
                continue
                
    logger.info(f"Found {len(platformDepartures)} departures for platform {platformNumber}")
    
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
        logger.info(f"\nProcessing TfL data for station {screenConfig['departureStation']}")
        
        # Use new implementation if enabled
        if config["migration"]["use_new_tfl_client"]:
            processor = _get_tfl_processor(config)
            departures, calling_points, station_name = processor.get_station_data(screenConfig)
            
            # If we got departures, filter by platform
            if departures:
                return processor.filter_platform_departures(departures, screenConfig["platform"], station_name)
            return False, False, screenConfig["outOfHoursName"]
            
        # Fall back to old implementation
        tfl_station = get_tfl_station(config, screenConfig)
        if tfl_station:
            logger.info(f"Got TfL station: {tfl_station.name}")
            arrivals = get_tfl_arrivals(config, tfl_station)
            if arrivals:
                logger.info(f"Got {len(arrivals)} TfL arrivals")
                converted_arrivals = convert_tfl_arrivals(arrivals, config["tfl"]["mode"])
                if converted_arrivals:
                    logger.info(f"Converted {len(converted_arrivals)} TfL arrivals:")
                    for arr in converted_arrivals:
                        logger.info(f"- {arr.get('line', 'Unknown')} line to {arr['destination_name']} from {arr.get('display_platform', 'Unknown platform')} in {arr['aimed_departure_time']}")
                    logger.info("Setting is_tfl flag for announcements")
                    for arr in converted_arrivals:
                        arr['is_tfl'] = True
                    return converted_arrivals, converted_arrivals[0]["calling_at_list"], tfl_station.name
                else:
                    logger.warning("No arrivals after conversion")
            else:
                logger.warning("No TfL arrivals found")
        else:
            logger.warning("Could not get TfL station data")
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
            logger.error("Error: Failed to fetch data from OpenLDBWS")
            logger.error(err.__context__)
            return False, False, screenConfig['outOfHoursName']
