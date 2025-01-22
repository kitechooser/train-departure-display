import time
from datetime import datetime
from luma.core.sprite_system import framerate_regulator
from open import isRun
from config import loadConfig
from utilities import get_version_number, initialize_fonts
from display_manager import create_display
from train_manager import load_data, platform_filter
from renderers import create_renderer
from src.announcements.announcements_module import AnnouncementManager, AnnouncementConfig

def main():
    try:
        print('Starting Train Departure Display v' + get_version_number())
        config = loadConfig()
        print(f"Loaded config - Refresh time: {config['refreshTime']} seconds")

        # Initialize announcements
        announcement_config = AnnouncementConfig(
            enabled=config["announcements"]["enabled"],
            volume=config["announcements"]["volume"],
            announcement_gap=config["announcements"]["announcement_gap"],
            max_queue_size=config["announcements"]["max_queue_size"],
            log_level=config["announcements"]["log_level"],
            announcement_types=config["announcements"]["announcement_types"],
            audio_config=config["announcements"]["audio"]
        )
        announcer = AnnouncementManager(announcement_config)

        # Initialize fonts and renderers
        font, fontBold, fontBoldTall, fontBoldLarge = initialize_fonts()
        renderer1 = create_renderer(font, fontBold, fontBoldTall, fontBoldLarge, config, config["screen1"]["mode"])
        renderer2 = None
        if config['dualScreen']:
            renderer2 = create_renderer(font, fontBold, fontBoldTall, fontBoldLarge, config, config["screen2"]["mode"])

        # Initialize display settings
        widgetWidth = 256
        widgetHeight = 64

        regulator = framerate_regulator(config['targetFPS'])

        # Initialize displays
        device = create_display(config, widgetWidth, widgetHeight)
        device1 = None
        if config['dualScreen']:
            device1 = create_display(config, widgetWidth, widgetHeight, is_secondary=True)

        if (config['debug'] > 1):
            # render screen and sleep for specified seconds
            virtual = renderer1.drawDebugScreen(device, width=widgetWidth, height=widgetHeight)
            virtual.refresh()
            if config['dualScreen']:
                virtual = renderer2.drawDebugScreen(device1, width=widgetWidth, height=widgetHeight, screen="2")
                virtual.refresh()
            time.sleep(config['debug'])
        else:
            # display NRE attribution while data loads
            virtual = renderer1.drawStartup(device, width=widgetWidth, height=widgetHeight)
            virtual.refresh()
            if config['dualScreen']:
                virtual = renderer2.drawStartup(device1, width=widgetWidth, height=widgetHeight)
                virtual.refresh()
            if config['headless'] is not True:
                time.sleep(5)

        timeAtStart = time.time() - config["refreshTime"]
        timeNow = time.time()
        timeFPS = time.time()

        blankHours = []
        if config['hoursPattern'].match(config['screenBlankHours']):
            blankHours = [int(x) for x in config['screenBlankHours'].split('-')]

        running = True
        while running:
            # Check if we need to stop (for preview mode)
            if config.get("previewMode", False):
                running = device.running
                if device1:
                    running = running and device1.running

            with regulator:
                if len(blankHours) == 2 and isRun(blankHours[0], blankHours[1]):
                    device.clear()
                    if config['dualScreen']:
                        device1.clear()
                    time.sleep(10)
                else:
                    if timeNow - timeFPS >= config['fpsTime']:
                        timeFPS = time.time()
                        print('Effective FPS: ' + str(round(regulator.effective_FPS(), 2)))
                    
                    # Calculate time until next refresh
                    time_until_refresh = config["refreshTime"] - (timeNow - timeAtStart)
                    if time_until_refresh <= 0:
                        print(f"Refreshing departures after {round(timeNow - timeAtStart)} seconds (configured for every {config['refreshTime']} seconds)")
                        
                        # check if debug mode is enabled 
                        if config["debug"] == True:
                            print(config["debug"])
                            virtual = renderer1.drawDebugScreen(device, width=widgetWidth, height=widgetHeight, showTime=True)
                            if config['dualScreen']:
                                virtual1 = renderer2.drawDebugScreen(device1, width=widgetWidth, height=widgetHeight, showTime=True, screen="2")
                        else:
                            # Screen 1 update
                            data = load_data(config["api"], config["screen1"], config)
                            if data[0] is False:
                                virtual = renderer1.drawBlankSignage(
                                    device, width=widgetWidth, height=widgetHeight, departureStation=data[2])
                            else:
                                departureData = data[0]
                                nextStations = data[1]
                                station = data[2]
                                
                                # Filter departures by platform first
                                screenData = platform_filter(departureData, config["screen1"]["platform"], station)
                                platformDepartures = screenData[0] if screenData[0] else []
                                
                                # Check for announcements only for the filtered departures
                                if not config["announcements"]["muted"]:
                                    print("\nChecking announcements for screen1 (not muted)")
                                    print(f"Screen mode: {config['screen1']['mode']}")
                                    
                                    # Check operating hours
                                    announce_hours = []
                                    if config['hoursPattern'].match(config['announcements']['operating_hours']):
                                        announce_hours = [int(x) for x in config['announcements']['operating_hours'].split('-')]
                                        print(f"Announcement hours: {announce_hours}")
                                    
                                    # Only announce if within operating hours (or if no hours specified)
                                    if not announce_hours or isRun(announce_hours[0], announce_hours[1]):
                                        print(f"Processing announcements for platform {config['screen1']['platform'] or 'all'} departures:")
                                        
                                        # Announce next train if we have departures and enough time has passed
                                        if platformDepartures:
                                            current_time = time.time()
                                            next_train = platformDepartures[0]
                                            
                                            print(f"\nNext train data (screen1):")
                                            print(f"is_tfl: {next_train.get('is_tfl')}")
                                            print(f"destination: {next_train.get('destination_name')}")
                                            print(f"platform: {next_train.get('display_platform') or next_train.get('platform')}")
                                            print(f"time: {next_train.get('aimed_departure_time')}")
                                            
                                            # Use configured announcement intervals for TfL vs National Rail
                                            min_interval = config["announcements"]["repeat_interval"]["tfl"] if next_train.get("is_tfl") else config["announcements"]["repeat_interval"]["rail"]
                                            
                                            time_since_last = current_time - announcer.last_next_train_screen1
                                            print(f"Time since last screen1 announcement: {time_since_last:.1f}s (minimum interval: {min_interval}s)")
                                            
                                            if time_since_last >= min_interval:
                                                print(f"Announcing next {'TfL' if next_train.get('is_tfl') else 'National Rail'} service")
                                                announcer.announce_next_train(next_train)
                                                announcer.last_next_train_screen1 = current_time
                                            else:
                                                print(f"Skipping announcement - too soon (need to wait {min_interval - time_since_last:.1f}s more)")
                                        
                                        # Process other announcements for non-TfL services
                                        for departure in platformDepartures:
                                            # Skip TfL services for delay/cancellation announcements since TfL API doesn't provide this info
                                            if departure.get("is_tfl"):
                                                print(f"Skipping TfL service to {departure.get('destination_name')} - No delay information available")
                                                continue
                                                
                                            print(f"Checking departure: {departure.get('destination_name')} - Status: {departure.get('expected_departure_time')} - Platform: {departure.get('platform', 'None')}")
                                            if departure["expected_departure_time"] == "Cancelled":
                                                print("Found cancelled service - announcing")
                                                announcer.announce_cancellation(departure)
                                            elif departure["expected_departure_time"] == "Delayed":
                                                print("Found delayed service - announcing")
                                                announcer.announce_delay(departure)
                                            elif departure["expected_departure_time"] != "On time" and \
                                                departure["expected_departure_time"] != departure["aimed_departure_time"]:
                                                print("Found service with different expected time - announcing delay")
                                                announcer.announce_delay(departure)
                                    else:
                                        print("Outside announcement hours - skipping announcements")
                                else:
                                    print("Announcements are muted - skipping")
                                
                                virtual = renderer1.drawSignage(device, width=widgetWidth, height=widgetHeight, data=screenData)

                            # Screen 2 update (if enabled)
                            if config['dualScreen']:
                                data = load_data(config["api"], config["screen2"], config)
                                if data[0] is False:
                                    virtual1 = renderer2.drawBlankSignage(
                                        device1, width=widgetWidth, height=widgetHeight, departureStation=data[2])
                                else:
                                    departureData = data[0]
                                    nextStations = data[1]
                                    station = data[2]
                                    screenData = platform_filter(departureData, config["screen2"]["platform"], station)
                                    platformDepartures = screenData[0] if screenData[0] else []
                                    
                                    # Process announcements for screen2 (TfL)
                                    if not config["announcements"]["muted"]:
                                        print("\nChecking announcements for screen2 (not muted)")
                                        print(f"Screen mode: {config['screen2']['mode']}")
                                        
                                        # Check operating hours
                                        announce_hours = []
                                        if config['hoursPattern'].match(config['announcements']['operating_hours']):
                                            announce_hours = [int(x) for x in config['announcements']['operating_hours'].split('-')]
                                            print(f"Announcement hours: {announce_hours}")
                                        
                                        # Only announce if within operating hours (or if no hours specified)
                                        if not announce_hours or isRun(announce_hours[0], announce_hours[1]):
                                            print(f"Processing announcements for platform {config['screen2']['platform'] or 'all'} departures:")
                                            
                                            # Announce next train if we have departures and enough time has passed
                                            if platformDepartures:
                                                current_time = time.time()
                                                next_train = platformDepartures[0]
                                                
                                                print(f"\nNext train data (screen2):")
                                                print(f"is_tfl: {next_train.get('is_tfl')}")
                                                print(f"destination: {next_train.get('destination_name')}")
                                                print(f"platform: {next_train.get('display_platform') or next_train.get('platform')}")
                                                print(f"time: {next_train.get('aimed_departure_time')}")
                                                
                                                # Use configured announcement intervals for TfL vs National Rail
                                                min_interval = config["announcements"]["repeat_interval"]["tfl"] if next_train.get("is_tfl") else config["announcements"]["repeat_interval"]["rail"]
                                                
                                                time_since_last = current_time - announcer.last_next_train_screen2
                                                print(f"Time since last screen2 announcement: {time_since_last:.1f}s (minimum interval: {min_interval}s)")
                                                
                                                if time_since_last >= min_interval:
                                                    print(f"Announcing next {'TfL' if next_train.get('is_tfl') else 'National Rail'} service")
                                                    announcer.announce_next_train(next_train)
                                                    announcer.last_next_train_screen2 = current_time
                                                else:
                                                    print(f"Skipping announcement - too soon (need to wait {min_interval - time_since_last:.1f}s more)")
                                        else:
                                            print("Outside announcement hours - skipping announcements")
                                    else:
                                        print("Announcements are muted - skipping")
                                    
                                    virtual1 = renderer2.drawSignage(device1, width=widgetWidth, height=widgetHeight, data=screenData)

                        timeAtStart = time.time()

                    timeNow = time.time()
                    virtual.refresh()
                    if config['dualScreen']:
                        virtual1.refresh()

    except KeyboardInterrupt:
        if 'announcer' in locals():
            announcer.cleanup()
    except ValueError as err:
        if 'announcer' in locals():
            announcer.cleanup()
        print(f"Error: {err}")

if __name__ == "__main__":
    main()
