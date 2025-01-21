import os
import time
import tkinter as tk
import requests

from datetime import datetime
from PIL import ImageFont, Image, ImageDraw, ImageTk

from trains import loadDeparturesForStation
from config import loadConfig
from open import isRun
from announcements.announcements_module import AnnouncementManager, AnnouncementConfig

from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.oled.device import ssd1322
from luma.core.virtual import viewport, snapshot
from luma.core.sprite_system import framerate_regulator

import socket, re, uuid

from tfl import get_tfl_station, get_tfl_arrivals, convert_tfl_arrivals

class MockDisplay:
    """Mock implementation of the SSD1322 display"""
    def __init__(self, width=256, height=64, mode="1", rotate=0, is_secondary=False):
        self.width = width
        self.height = height
        self.mode = mode
        self.rotate = rotate
        self.size = (width, height)  # Required by luma
        self.image = Image.new('1', self.size, 0)  # 0 = black in mode "1"
        self.draw = ImageDraw.Draw(self.image)
        
        # Create tkinter window for display
        self.root = tk.Toplevel() if is_secondary else tk.Tk()
        self.root.title(f"Train Display Preview {'Secondary' if is_secondary else 'Primary'}")
        
        # Add padding to window size
        padding = 20
        window_width = width + padding * 2
        window_height = height + padding * 2
        
        # Configure window size and position
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        y = (screen_height - window_height) // 2
        
        # Position primary window on the left, secondary on the right
        x = 50 if not is_secondary else screen_width - window_width - 50
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Create canvas with padding
        self.canvas = tk.Canvas(self.root, width=window_width, height=window_height)
        self.canvas.pack()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.running = True
        
        # Initialize PhotoImage with padding
        self.photo = ImageTk.PhotoImage(self.image)
        self.canvas.create_image(padding, padding, image=self.photo, anchor=tk.NW)
        self.root.update()
        print(f"MockDisplay initialized {'Secondary' if is_secondary else 'Primary'}")

    def on_closing(self):
        self.running = False
        self.root.destroy()

    def clear(self):
        self.draw.rectangle([0, 0, self.width, self.height], fill='black')
        self.update_display()

    def display(self, image):
        self.image = image.convert('RGB')
        self.update_display()

    def update_display(self):
        try:
            # Create new PhotoImage
            new_photo = ImageTk.PhotoImage(self.image)
            
            # Update canvas with new image (with padding)
            padding = 20
            self.canvas.delete("all")
            self.image_id = self.canvas.create_image(padding, padding, image=new_photo, anchor=tk.NW)
            
            # Keep reference and update
            self.photo = new_photo
            self.root.update()
        except Exception as e:
            print(f"Display update error: {e}")

def getVersionNumber():
    version_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..',
            'VERSION'
        )
    )
    version_file = open(version_path, 'r')
    return version_file.read()

def getIp():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def makeFont(name, size):
    font_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            'fonts',
            name
        )
    )
    return ImageFont.truetype(font_path, size, layout_engine=ImageFont.Layout.BASIC)

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

def loadData(apiConfig, screenConfig, config):
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

def renderDebugScreen(debugLines, draw=None, width=None, height=None):
    """Render debug information on the display"""
    if draw is None:
        def drawText(draw, width=None, height=None, x=0, y=0):
            # Draw each line of debug info
            y_offset = 0
            for key in sorted(debugLines.keys()):
                text = debugLines[key]
                _, _, bitmap = cachedBitmapText(text, font)
                draw.bitmap((x, y + y_offset), bitmap, fill="yellow")
                y_offset += 12  # Space between lines
        return drawText
    else:
        # Draw each line of debug info
        y_offset = 0
        for key in sorted(debugLines.keys()):
            text = debugLines[key]
            _, _, bitmap = cachedBitmapText(text, font)
            draw.bitmap((0, y_offset), bitmap, fill="yellow")
            y_offset += 12  # Space between lines

def drawStartup(device, width, height):
    virtualViewport = viewport(device, width=width, height=height)

    # Create a new image for drawing - use mode "1" for hardware displays
    image = Image.new('1', (width, height), 0)  # 0 = black in mode "1"
    draw = ImageDraw.Draw(image)

    nameSize = int(fontBold.getlength("UK Train Departure Display"))
    poweredSize = int(fontBold.getlength("Powered by"))
    NRESize = int(fontBold.getlength("National Rail Enquiries"))

    rowOne = snapshot(width, 10, renderName((width - nameSize) / 2), interval=10)
    rowThree = snapshot(width, 10, renderPoweredBy((width - poweredSize) / 2), interval=10)
    rowFour = snapshot(width, 10, renderNRE((width - NRESize) / 2), interval=10)

    if len(virtualViewport._hotspots) > 0:
        for hotspot, xy in virtualViewport._hotspots:
            virtualViewport.remove_hotspot(hotspot, xy)

    virtualViewport.add_hotspot(rowOne, (0, 0))
    virtualViewport.add_hotspot(rowThree, (0, 24))
    virtualViewport.add_hotspot(rowFour, (0, 36))

    # Draw directly to the device
    if isinstance(device, MockDisplay):
        device.update_display()
    else:
        device.display(image)

    return virtualViewport

def drawBlankSignage(device, width, height, departureStation):
    global stationRenderCount, pauseCount

    welcomeSize = int(fontBold.getlength("Welcome to"))
    stationSize = int(fontBold.getlength(departureStation))

    device.clear()

    virtualViewport = viewport(device, width=width, height=height)

    rowOne = snapshot(width, 10, renderWelcomeTo(
        (width - welcomeSize) / 2), interval=config["refreshTime"])
    rowTwo = snapshot(width, 10, renderDepartureStation(
        departureStation, (width - stationSize) / 2), interval=config["refreshTime"])
    rowThree = snapshot(width, 10, renderDots, interval=config["refreshTime"])
    rowTime = snapshot(width, 14, renderTime, interval=0.1)

    if len(virtualViewport._hotspots) > 0:
        for vhotspot, xy in virtualViewport._hotspots:
            virtualViewport.remove_hotspot(vhotspot, xy)

    virtualViewport.add_hotspot(rowOne, (0, 0))
    virtualViewport.add_hotspot(rowTwo, (0, 12))
    virtualViewport.add_hotspot(rowThree, (0, 24))
    virtualViewport.add_hotspot(rowTime, (0, 50))

    return virtualViewport

def drawSignage(device, width, height, data):
    global stationRenderCount, pauseCount

    virtualViewport = viewport(device, width=width, height=height)

    status = "Exp 00:00"
    callingAt = "Calling at: "

    departures, firstDepartureDestinations, departureStation = data

    w = int(font.getlength(callingAt))

    callingWidth = w
    width = virtualViewport.width

    # First measure the text size
    w = int(font.getlength(status))
    pw = int(font.getlength("Plat 88"))

    if not departures:
        noTrains = drawBlankSignage(device, width=width, height=height, departureStation=departureStation)
        return noTrains

    firstFont = font
    if config['firstDepartureBold']:
        firstFont = fontBold

    rowOneA = snapshot(
        width - w - pw - 5, 10, renderDestination(departures[0], firstFont, '1st'), interval=config["refreshTime"])
    rowOneB = snapshot(w, 10, renderServiceStatus(
        departures[0]), interval=10)
    rowOneC = snapshot(pw, 10, renderPlatform(departures[0]), interval=config["refreshTime"])
    rowTwoA = snapshot(callingWidth, 10, renderCallingAt, interval=config["refreshTime"])
    rowTwoB = snapshot(width - callingWidth, 10,
                       renderStations(firstDepartureDestinations), interval=0.02)

    if len(departures) > 1:
        rowThreeA = snapshot(width - w - pw, 10, renderDestination(
            departures[1], font, '2nd'), interval=config["refreshTime"])
        rowThreeB = snapshot(w, 10, renderServiceStatus(
            departures[1]), interval=config["refreshTime"])
        rowThreeC = snapshot(pw, 10, renderPlatform(departures[1]), interval=config["refreshTime"])

    if len(departures) > 2:
        rowFourA = snapshot(width - w - pw, 10, renderDestination(
            departures[2], font, '3rd'), interval=10)
        rowFourB = snapshot(w, 10, renderServiceStatus(
            departures[2]), interval=10)
        rowFourC = snapshot(pw, 10, renderPlatform(departures[2]), interval=config["refreshTime"])

    rowTime = snapshot(width, 14, renderTime, interval=0.1)

    if len(virtualViewport._hotspots) > 0:
        for vhotspot, xy in virtualViewport._hotspots:
            virtualViewport.remove_hotspot(vhotspot, xy)

    stationRenderCount = 0
    pauseCount = 0

    virtualViewport.add_hotspot(rowOneA, (0, 0))
    virtualViewport.add_hotspot(rowOneB, (width - w, 0))
    virtualViewport.add_hotspot(rowOneC, (width - w - pw, 0))
    virtualViewport.add_hotspot(rowTwoA, (0, 12))
    virtualViewport.add_hotspot(rowTwoB, (callingWidth, 12))

    if len(departures) > 1:
        virtualViewport.add_hotspot(rowThreeA, (0, 24))
        virtualViewport.add_hotspot(rowThreeB, (width - w, 24))
        virtualViewport.add_hotspot(rowThreeC, (width - w - pw, 24))

    if len(departures) > 2:
        virtualViewport.add_hotspot(rowFourA, (0, 36))
        virtualViewport.add_hotspot(rowFourB, (width - w, 36))
        virtualViewport.add_hotspot(rowFourC, (width - w - pw, 36))

    virtualViewport.add_hotspot(rowTime, (0, 50))

    return virtualViewport

def renderDestination(departure, font, pos, draw=None, width=None, height=None):
    if draw is None:
        def drawText(draw, width=None, height=None, x=0, y=0):
            if config["showDepartureNumbers"]:
                train = f"{pos}  {departure['aimed_departure_time']}  {departure['destination_name']}"
            else:
                train = f"{departure['aimed_departure_time']}  {departure['destination_name']}"
            _, _, bitmap = cachedBitmapText(train, font)
            draw.bitmap((x, y), bitmap, fill="yellow")
        return drawText
    else:
        if config["showDepartureNumbers"]:
            train = f"{pos}  {departure['aimed_departure_time']}  {departure['destination_name']}"
        else:
            train = f"{departure['aimed_departure_time']}  {departure['destination_name']}"
        _, _, bitmap = cachedBitmapText(train, font)
        draw.bitmap((0, 0), bitmap, fill="yellow")

def renderServiceStatus(departure, draw=None, width=None, height=None):
    if draw is None:
        def drawText(draw, width=None, height=None, x=0, y=0):
            train = ""
            if departure["expected_departure_time"] == "On time":
                train = "On time"
            elif departure["expected_departure_time"] == "Cancelled":
                train = "Cancelled"
            elif departure["expected_departure_time"] == "Delayed":
                train = "Delayed"
            else:
                if isinstance(departure["expected_departure_time"], str):
                    train = 'Exp ' + departure["expected_departure_time"]
                if departure["aimed_departure_time"] == departure["expected_departure_time"]:
                    train = "On time"
            w, _, bitmap = cachedBitmapText(train, font)
            draw.bitmap((x + width - w, y), bitmap, fill="yellow")
        return drawText
    else:
        train = ""
        if departure["expected_departure_time"] == "On time":
            train = "On time"
        elif departure["expected_departure_time"] == "Cancelled":
            train = "Cancelled"
        elif departure["expected_departure_time"] == "Delayed":
            train = "Delayed"
        else:
            if isinstance(departure["expected_departure_time"], str):
                train = 'Exp ' + departure["expected_departure_time"]
            if departure["aimed_departure_time"] == departure["expected_departure_time"]:
                train = "On time"
        w, _, bitmap = cachedBitmapText(train, font)
        draw.bitmap((width - w, 0), bitmap, fill="yellow")

def renderPlatform(departure, draw=None, width=None, height=None):
    if draw is None:
        def drawText(draw, width=None, height=None, x=0, y=0):
            if "display_platform" in departure:
                platform = departure["display_platform"]
            elif "platform" in departure:
                platform = "Plat " + departure["platform"]
                if departure["platform"].lower() == "bus":
                    platform = "BUS"
            else:
                return
            _, _, bitmap = cachedBitmapText(platform, font)
            draw.bitmap((x, y), bitmap, fill="yellow")
        return drawText
    else:
        if "display_platform" in departure:
            platform = departure["display_platform"]
        elif "platform" in departure:
            platform = "Plat " + departure["platform"]
            if departure["platform"].lower() == "bus":
                platform = "BUS"
        else:
            return
        _, _, bitmap = cachedBitmapText(platform, font)
        draw.bitmap((0, 0), bitmap, fill="yellow")

def renderCallingAt(draw=None, width=None, height=None):
    if draw is None:
        def drawText(draw, width=None, height=None, x=0, y=0):
            stations = "Calling at: "
            _, _, bitmap = cachedBitmapText(stations, font)
            draw.bitmap((x, y), bitmap, fill="yellow")
        return drawText
    else:
        stations = "Calling at: "
        _, _, bitmap = cachedBitmapText(stations, font)
        draw.bitmap((0, 0), bitmap, fill="yellow")

def renderStations(stations, draw=None, width=None, height=None):
    if draw is None:
        def drawText(draw, width=None, height=None, x=0, y=0):
            global stationRenderCount, pauseCount, pixelsLeft, pixelsUp, hasElevated

            if len(stations) == stationRenderCount - 5:
                stationRenderCount = 0

            txt_width, txt_height, bitmap = cachedBitmapText(stations, font)

            if hasElevated:
                draw.bitmap((x + pixelsLeft - 1, y), bitmap, fill="yellow")
                if -pixelsLeft > txt_width and pauseCount < 8:
                    pauseCount += 1
                    pixelsLeft = 0
                    hasElevated = 0
                else:
                    pauseCount = 0
                    pixelsLeft = pixelsLeft - 1
            else:
                draw.bitmap((x, y + txt_height - pixelsUp), bitmap, fill="yellow")
                if pixelsUp == txt_height:
                    pauseCount += 1
                    if pauseCount > 20:
                        hasElevated = 1
                        pixelsUp = 0
                else:
                    pixelsUp = pixelsUp + 1
        return drawText
    else:
        global stationRenderCount, pauseCount, pixelsLeft, pixelsUp, hasElevated

        if len(stations) == stationRenderCount - 5:
            stationRenderCount = 0

        txt_width, txt_height, bitmap = cachedBitmapText(stations, font)

        if hasElevated:
            draw.bitmap((pixelsLeft - 1, 0), bitmap, fill="yellow")
            if -pixelsLeft > txt_width and pauseCount < 8:
                pauseCount += 1
                pixelsLeft = 0
                hasElevated = 0
            else:
                pauseCount = 0
                pixelsLeft = pixelsLeft - 1
        else:
            draw.bitmap((0, txt_height - pixelsUp), bitmap, fill="yellow")
            if pixelsUp == txt_height:
                pauseCount += 1
                if pauseCount > 20:
                    hasElevated = 1
                    pixelsUp = 0
            else:
                pixelsUp = pixelsUp + 1

def renderTime(draw=None, width=None, height=None):
    if draw is None:
        def drawText(draw, width=None, height=None, x=0, y=0):
            rawTime = datetime.now().time()
            hour, minute, second = str(rawTime).split('.')[0].split(':')

            w1, _, HMBitmap = cachedBitmapText("{}:{}".format(hour, minute), fontBoldLarge)
            w2, _, _ = cachedBitmapText(':00', fontBoldTall)
            _, _, SBitmap = cachedBitmapText(':{}'.format(second), fontBoldTall)

            draw.bitmap((x + (width - w1 - w2) / 2, y), HMBitmap, fill="yellow")
            draw.bitmap((x + (width - w1 - w2) / 2 + w1, y + 5), SBitmap, fill="yellow")
        return drawText
    else:
        rawTime = datetime.now().time()
        hour, minute, second = str(rawTime).split('.')[0].split(':')

        w1, _, HMBitmap = cachedBitmapText("{}:{}".format(hour, minute), fontBoldLarge)
        w2, _, _ = cachedBitmapText(':00', fontBoldTall)
        _, _, SBitmap = cachedBitmapText(':{}'.format(second), fontBoldTall)

        draw.bitmap(((width - w1 - w2) / 2, 0), HMBitmap, fill="yellow")
        draw.bitmap(((width - w1 - w2) / 2 + w1, 5), SBitmap, fill="yellow")

def renderWelcomeTo(xOffset, draw=None, width=None, height=None):
    if draw is None:
        def drawText(draw, width=None, height=None, x=0, y=0):
            text = "Welcome to"
            _, _, bitmap = cachedBitmapText(text, fontBold)
            draw.bitmap((x + int(xOffset), y), bitmap, fill="yellow")
        return drawText
    else:
        text = "Welcome to"
        _, _, bitmap = cachedBitmapText(text, fontBold)
        draw.bitmap((int(xOffset), 0), bitmap, fill="yellow")

def renderPoweredBy(xOffset, draw=None, width=None, height=None):
    if draw is None:
        def drawText(draw, width=None, height=None, x=0, y=0):
            text = "Powered by"
            _, _, bitmap = cachedBitmapText(text, fontBold)
            draw.bitmap((x + int(xOffset), y), bitmap, fill="yellow")
        return drawText
    else:
        text = "Powered by"
        _, _, bitmap = cachedBitmapText(text, fontBold)
        draw.bitmap((int(xOffset), 0), bitmap, fill="yellow")

def renderNRE(xOffset, draw=None, width=None, height=None):
    if draw is None:
        def drawText(draw, width=None, height=None, x=0, y=0):
            text = "National Rail Enquiries"
            _, _, bitmap = cachedBitmapText(text, fontBold)
            draw.bitmap((x + int(xOffset), y), bitmap, fill="yellow")
        return drawText
    else:
        text = "National Rail Enquiries"
        _, _, bitmap = cachedBitmapText(text, fontBold)
        draw.bitmap((int(xOffset), 0), bitmap, fill="yellow")

def renderName(xOffset, draw=None, width=None, height=None):
    if draw is None:
        def drawText(draw, width=None, height=None, x=0, y=0):
            text = "UK Train Departure Display"
            _, _, bitmap = cachedBitmapText(text, fontBold)
            draw.bitmap((x + int(xOffset), y), bitmap, fill="yellow")
        return drawText
    else:
        text = "UK Train Departure Display"
        _, _, bitmap = cachedBitmapText(text, fontBold)
        draw.bitmap((int(xOffset), 0), bitmap, fill="yellow")

def renderDepartureStation(departureStation, xOffset, draw=None, width=None, height=None):
    if draw is None:
        def drawText(draw, width=None, height=None, x=0, y=0):
            text = departureStation
            _, _, bitmap = cachedBitmapText(text, fontBold)
            draw.bitmap((x + int(xOffset), y), bitmap, fill="yellow")
        return drawText
    else:
        text = departureStation
        _, _, bitmap = cachedBitmapText(text, fontBold)
        draw.bitmap((int(xOffset), 0), bitmap, fill="yellow")

def renderDots(draw=None, width=None, height=None):
    if draw is None:
        def drawText(draw, width=None, height=None, x=0, y=0):
            text = ".  .  ."
            draw.text((x, y), text=text, font=fontBold, fill="yellow")
        return drawText
    else:
        text = ".  .  ."
        draw.text((0, 0), text=text, font=fontBold, fill="yellow")

bitmapRenderCache = {}

def cachedBitmapText(text, font):
    # cache the bitmap representation of the stations string
    nameTuple = font.getname()
    fontKey = ''
    for item in nameTuple:
        fontKey = fontKey + item
    key = text + fontKey
    if key in bitmapRenderCache:
        # found in cache; re-use it
        pre = bitmapRenderCache[key]
        bitmap = pre['bitmap']
        txt_width = pre['txt_width']
        txt_height = pre['txt_height']
    else:
        # not cached; create a new image containing the string as a monochrome bitmap
        _, _, txt_width, txt_height = font.getbbox(text)
        bitmap = Image.new('L', [txt_width, txt_height], color=0)
        pre_render_draw = ImageDraw.Draw(bitmap)
        pre_render_draw.text((0, 0), text=text, font=font, fill=255)
        # save to render cache
        bitmapRenderCache[key] = {'bitmap': bitmap, 'txt_width': txt_width, 'txt_height': txt_height}
    return txt_width, txt_height, bitmap

# Initialize global variables
font = None
fontBold = None
fontBoldTall = None
fontBoldLarge = None
config = None
pixelsLeft = 1
pixelsUp = 0
hasElevated = 0
pauseCount = 0
stationRenderCount = 0

# Main program
try:
    print('Starting Train Departure Display v' + getVersionNumber())
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

    # Initialize fonts
    font = makeFont("Dot Matrix Regular.ttf", 10)
    fontBold = makeFont("Dot Matrix Bold.ttf", 10)
    fontBoldTall = makeFont("Dot Matrix Bold Tall.ttf", 10)
    fontBoldLarge = makeFont("Dot Matrix Bold.ttf", 20)

    # Initialize display settings
    widgetWidth = 256
    widgetHeight = 64

    stationRenderCount = 0
    pauseCount = 0
    loop_count = 0

    regulator = framerate_regulator(config['targetFPS'])

    # Initialize displays
    device = None
    device1 = None
    if config['previewMode']:
        device = MockDisplay(width=widgetWidth, height=widgetHeight)
        if config['dualScreen']:
            device1 = MockDisplay(width=widgetWidth, height=widgetHeight, is_secondary=True)
    else:
        # Hardware display initialization
        serial = spi(port=0, device=0, gpio_DC=24, gpio_RST=25, bus_speed_hz=8000000)
        device = ssd1322(serial, mode="1", rotate=config['screenRotation'])
        if config['dualScreen']:
            serial1 = spi(port=1, device=0, gpio_DC=27, gpio_RST=31, bus_speed_hz=8000000)
            device1 = ssd1322(serial1, mode="1", rotate=config['screenRotation'])

    if (config['debug'] > 1):
        # render screen and sleep for specified seconds
        virtual = drawDebugScreen(device, width=widgetWidth, height=widgetHeight)
        virtual.refresh()
        if config['dualScreen']:
            virtual = drawDebugScreen(device, width=widgetWidth, height=widgetHeight, screen="2")
            virtual.refresh()
        time.sleep(config['debug'])
    else:
        # display NRE attribution while data loads
        virtual = drawStartup(device, width=widgetWidth, height=widgetHeight)
        virtual.refresh()
        if config['dualScreen']:
            virtual = drawStartup(device1, width=widgetWidth, height=widgetHeight)
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
                        virtual = drawDebugScreen(device, width=widgetWidth, height=widgetHeight, showTime=True)
                        if config['dualScreen']:
                            virtual1 = drawDebugScreen(device1, width=widgetWidth, height=widgetHeight, showTime=True, screen="2")
                    else:
                        # Screen 1 update
                        data = loadData(config["api"], config["screen1"], config)
                        if data[0] is False:
                            virtual = drawBlankSignage(
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
                                        
                                        # Use different announcement intervals for TfL vs National Rail
                                        min_interval = 30 if next_train.get("is_tfl") else 60
                                        
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
                            
                            virtual = drawSignage(device, width=widgetWidth, height=widgetHeight, data=screenData)

                        # Screen 2 update (if enabled)
                        if config['dualScreen']:
                            data = loadData(config["api"], config["screen2"], config)
                            if data[0] is False:
                                virtual1 = drawBlankSignage(
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
                                            
                                            # Use different announcement intervals for TfL vs National Rail
                                            min_interval = 30 if next_train.get("is_tfl") else 60
                                            
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
                                
                                virtual1 = drawSignage(device1, width=widgetWidth, height=widgetHeight, data=screenData)

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
# except KeyError as err:
#     print(f"Error: Please ensure the {err} environment variable is set")
