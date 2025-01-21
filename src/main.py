import os
import time
import tkinter as tk
import requests

from datetime import datetime
from PIL import ImageFont, Image, ImageDraw, ImageTk

from trains import loadDeparturesForStation
from config import loadConfig
from open import isRun

from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.oled.device import ssd1322
from luma.core.virtual import viewport, snapshot
from luma.core.sprite_system import framerate_regulator

import socket, re, uuid

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

class MockCanvas:
    """Mock implementation of Luma canvas context manager"""
    def __init__(self, device):
        self.device = device
        self.image = Image.new('1', (device.width, device.height), 0)  # 0 = black in mode "1"
        self.draw = ImageDraw.Draw(self.image)
        print("MockCanvas initialized")

    def __enter__(self):
        return self.draw

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("MockCanvas exit - displaying image")
        # Use the device's display method which handles image management
        self.device.display(self.image)

class MockViewport:
    """Mock implementation of Luma viewport"""
    def __init__(self, device, width, height):
        self.device = device
        self.width = width
        self.height = height
        self._hotspots = []

    def add_hotspot(self, source, xy):
        self._hotspots.append((source, xy))

    def remove_hotspot(self, source, xy):
        self._hotspots.remove((source, xy))

    def refresh(self):
        print("MockViewport refresh: starting")
        # Create a new image for drawing - use mode "1" for hardware displays
        image = Image.new('1', (self.width, self.height), 0)  # 0 = black in mode "1"
        draw = ImageDraw.Draw(image)
        print("MockViewport refresh: created image and draw")

        # Draw all hotspots
        for hotspot, (x, y) in self._hotspots:
            print(f"MockViewport refresh: drawing hotspot at ({x}, {y})")
            if hasattr(hotspot, 'compose'):
                print("MockViewport refresh: using compose")
                hotspot.compose(draw, x, y)
            else:
                print("MockViewport refresh: using direct draw")
                # Handle plain rendering functions
                if callable(hotspot):
                    drawFunc = hotspot()
                    drawFunc(draw, width=self.width, height=self.height, x=x, y=y)
                else:
                    hotspot(draw, width=self.width, height=self.height, x=x, y=y)

        print("MockViewport refresh: updating display")
        # Update the display
        if isinstance(self.device, MockDisplay):
            self.device.display(image)
        elif not config['headless']:
            # Only try to update physical hardware displays
            self.device.display(image)

class DisplayFactory:
    """Factory for creating either hardware or preview displays"""
    @staticmethod
    def create_display(config, is_secondary=False):
        """
        Create appropriate display based on config
        is_secondary: True if this is the second display in dual screen mode
        """
        preview_mode = config.get("previewMode", False)
        
        if preview_mode:
            return MockDisplay(
                width=256,
                height=64,
                mode="1",
                rotate=config['screenRotation'],
                is_secondary=is_secondary
            )
        else:
            # Hardware display initialization
            if is_secondary:
                serial = spi(port=1, gpio_DC=5, gpio_RST=6)
            else:
                if config['headless']:
                    serial = noop()
                else:
                    serial = spi(port=0)
            return ssd1322(serial, mode="1", rotate=config['screenRotation'])

class MockSnapshot:
    """Mock implementation of snapshot for testing"""
    def __init__(self, width, height, source, interval=1):
        self.width = width
        self.height = height
        self.source = source
        self.interval = interval
        self.last_updated = 0

    def compose(self, draw, x, y):
        if time.time() - self.last_updated >= self.interval:
            print(f"MockSnapshot compose: source={self.source.__name__}, x={x}, y={y}")
            # Handle both direct function calls and function-returning functions
            if callable(self.source):
                # Check if it's a render function that returns a drawing function
                try:
                    drawFunc = self.source()
                    print("MockSnapshot compose: calling drawFunc")
                    drawFunc(draw, width=self.width, height=self.height, x=x, y=y)
                except TypeError:
                    # If it's a direct render function, call it with the expected args
                    print("MockSnapshot compose: calling source directly")
                    self.source(draw, self.width, self.height)
            else:
                # For non-callable sources
                print("MockSnapshot compose: using source directly")
                self.source(draw, self.width, self.height)
            self.last_updated = time.time()

def initialize_displays(config):
    """Initialize displays based on configuration"""
    preview_mode = config.get("previewMode", False)
    
    # Set up displays
    device = DisplayFactory.create_display(config)
    device1 = None
    
    if config['dualScreen']:
        device1 = DisplayFactory.create_display(config, is_secondary=True)
    
    # Always use mock classes in preview mode
    if preview_mode:
        canvas_class = MockCanvas
        viewport_class = MockViewport
        snapshot_class = MockSnapshot
        
        # Wrap the hardware viewport and snapshot if needed
        if not isinstance(device, MockDisplay):
            device = MockDisplay(width=256, height=64, mode="1", rotate=config['screenRotation'])
        if device1 and not isinstance(device1, MockDisplay):
            device1 = MockDisplay(width=256, height=64, mode="1", rotate=config['screenRotation'], is_secondary=True)
    else:
        canvas_class = canvas
        viewport_class = viewport
        snapshot_class = snapshot
        
    return device, device1, canvas_class, viewport_class, snapshot_class

def makeFont(name, size):
    font_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            'fonts',
            name
        )
    )
    return ImageFont.truetype(font_path, size, layout_engine=ImageFont.Layout.BASIC)


def renderDestination(departure, font, pos, draw=None, width=None, height=None):
    if draw is None:
        # Return drawing function when called with no arguments
        def drawText(draw, width=None, height=None, x=0, y=0):
            if config["showDepartureNumbers"]:
                train = f"{pos}  {departure['aimed_departure_time']}  {departure['destination_name']}"
            else:
                train = f"{departure['aimed_departure_time']}  {departure['destination_name']}"
            _, _, bitmap = cachedBitmapText(train, font)
            draw.bitmap((x, y), bitmap, fill="yellow")
        return drawText
    else:
        # Direct call with arguments
        if config["showDepartureNumbers"]:
            train = f"{pos}  {departure['aimed_departure_time']}  {departure['destination_name']}"
        else:
            train = f"{departure['aimed_departure_time']}  {departure['destination_name']}"
        _, _, bitmap = cachedBitmapText(train, font)
        draw.bitmap((0, 0), bitmap, fill="yellow")

def renderServiceStatus(departure, draw=None, width=None, height=None):
    if draw is None:
        # Return drawing function when called with no arguments
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
        # Direct call with arguments
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
        # Return drawing function when called with no arguments
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
        # Direct call with arguments
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
        # Return drawing function when called with no arguments
        def drawText(draw, width=None, height=None, x=0, y=0):
            stations = "Calling at: "
            _, _, bitmap = cachedBitmapText(stations, font)
            draw.bitmap((x, y), bitmap, fill="yellow")
        return drawText
    else:
        # Direct call with arguments
        stations = "Calling at: "
        _, _, bitmap = cachedBitmapText(stations, font)
        draw.bitmap((0, 0), bitmap, fill="yellow")

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

pixelsLeft = 1
pixelsUp = 0
hasElevated = 0
pauseCount = 0

def renderStations(stations, draw=None, width=None, height=None):
    if draw is None:
        # Return drawing function when called with no arguments
        def drawText(draw, width=None, height=None, x=0, y=0):
            global stationRenderCount, pauseCount, pixelsLeft, pixelsUp, hasElevated

            if len(stations) == stationRenderCount - 5:
                stationRenderCount = 0

            txt_width, txt_height, bitmap = cachedBitmapText(stations, font)

            if hasElevated:
                # slide the bitmap left until it's fully out of view
                draw.bitmap((x + pixelsLeft - 1, y), bitmap, fill="yellow")
                if -pixelsLeft > txt_width and pauseCount < 8:
                    pauseCount += 1
                    pixelsLeft = 0
                    hasElevated = 0
                else:
                    pauseCount = 0
                    pixelsLeft = pixelsLeft - 1
            else:
                # slide the bitmap up from the bottom of its viewport until it's fully in view
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
        # Direct call with arguments
        global stationRenderCount, pauseCount, pixelsLeft, pixelsUp, hasElevated

        if len(stations) == stationRenderCount - 5:
            stationRenderCount = 0

        txt_width, txt_height, bitmap = cachedBitmapText(stations, font)

        if hasElevated:
            # slide the bitmap left until it's fully out of view
            draw.bitmap((pixelsLeft - 1, 0), bitmap, fill="yellow")
            if -pixelsLeft > txt_width and pauseCount < 8:
                pauseCount += 1
                pixelsLeft = 0
                hasElevated = 0
            else:
                pauseCount = 0
                pixelsLeft = pixelsLeft - 1
        else:
            # slide the bitmap up from the bottom of its viewport until it's fully in view
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
        # Return drawing function when called with no arguments
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
        # Direct call with arguments
        rawTime = datetime.now().time()
        hour, minute, second = str(rawTime).split('.')[0].split(':')

        w1, _, HMBitmap = cachedBitmapText("{}:{}".format(hour, minute), fontBoldLarge)
        w2, _, _ = cachedBitmapText(':00', fontBoldTall)
        _, _, SBitmap = cachedBitmapText(':{}'.format(second), fontBoldTall)

        draw.bitmap(((width - w1 - w2) / 2, 0), HMBitmap, fill="yellow")
        draw.bitmap(((width - w1 - w2) / 2 + w1, 5), SBitmap, fill="yellow")

def renderDebugScreen(lines, draw=None, width=None, height=None):
    if draw is None:
        # Return drawing function when called with no arguments
        def drawText(draw, width=None, height=None, x=0, y=0):
            # draw a box
            draw.rectangle((x + 1, y + 1, x + 254, y + 45), outline="yellow", fill=None)

            # coords for each line of text
            coords = {
                '1A': (x + 5, y + 5),
                '1B': (x + 45, y + 5),
                '2A': (x + 5, y + 18),
                '2B': (x + 45, y + 18),
                '3A': (x + 5, y + 31),
                '3B': (x + 45, y + 31),
                '3C': (x + 140, y + 31)
            }

            # loop through lines and check if cached
            for key, text in lines.items():
                w, _, bitmap = cachedBitmapText(text, font)
                draw.bitmap(coords[key], bitmap, fill="yellow")        
        return drawText
    else:
        # Direct call with arguments
        # draw a box
        draw.rectangle((1, 1, 254, 45), outline="yellow", fill=None)

        # coords for each line of text
        coords = {
            '1A': (5, 5),
            '1B': (45, 5),
            '2A': (5, 18),
            '2B': (45, 18),
            '3A': (5, 31),
            '3B': (45, 31),
            '3C': (140, 31)
        }

        # loop through lines and check if cached
        for key, text in lines.items():
            w, _, bitmap = cachedBitmapText(text, font)
            draw.bitmap(coords[key], bitmap, fill="yellow")

def renderWelcomeTo(xOffset, draw=None, width=None, height=None):
    if draw is None:
        # Return drawing function when called with no arguments
        def drawText(draw, width=None, height=None, x=0, y=0):
            text = "Welcome to"
            _, _, bitmap = cachedBitmapText(text, fontBold)
            draw.bitmap((x + int(xOffset), y), bitmap, fill="yellow")
        return drawText
    else:
        # Direct call with arguments
        text = "Welcome to"
        _, _, bitmap = cachedBitmapText(text, fontBold)
        draw.bitmap((int(xOffset), 0), bitmap, fill="yellow")

def renderPoweredBy(xOffset, draw=None, width=None, height=None):
    if draw is None:
        # Return drawing function when called with no arguments
        def drawText(draw, width=None, height=None, x=0, y=0):
            text = "Powered by"
            _, _, bitmap = cachedBitmapText(text, fontBold)
            draw.bitmap((x + int(xOffset), y), bitmap, fill="yellow")
        return drawText
    else:
        # Direct call with arguments
        text = "Powered by"
        _, _, bitmap = cachedBitmapText(text, fontBold)
        draw.bitmap((int(xOffset), 0), bitmap, fill="yellow")

def renderNRE(xOffset, draw=None, width=None, height=None):
    if draw is None:
        # Return drawing function when called with no arguments
        def drawText(draw, width=None, height=None, x=0, y=0):
            text = "National Rail Enquiries"
            _, _, bitmap = cachedBitmapText(text, fontBold)
            draw.bitmap((x + int(xOffset), y), bitmap, fill="yellow")
        return drawText
    else:
        # Direct call with arguments
        text = "National Rail Enquiries"
        _, _, bitmap = cachedBitmapText(text, fontBold)
        draw.bitmap((int(xOffset), 0), bitmap, fill="yellow")

def renderName(xOffset, draw=None, width=None, height=None):
    if draw is None:
        # Return drawing function when called with no arguments
        def drawText(draw, width=None, height=None, x=0, y=0):
            text = "UK Train Departure Display"
            _, _, bitmap = cachedBitmapText(text, fontBold)
            draw.bitmap((x + int(xOffset), y), bitmap, fill="yellow")
        return drawText
    else:
        # Direct call with arguments
        text = "UK Train Departure Display"
        _, _, bitmap = cachedBitmapText(text, fontBold)
        draw.bitmap((int(xOffset), 0), bitmap, fill="yellow")

def renderDepartureStation(departureStation, xOffset, draw=None, width=None, height=None):
    if draw is None:
        # Return drawing function when called with no arguments
        def drawText(draw, width=None, height=None, x=0, y=0):
            text = departureStation
            _, _, bitmap = cachedBitmapText(text, fontBold)
            draw.bitmap((x + int(xOffset), y), bitmap, fill="yellow")
        return drawText
    else:
        # Direct call with arguments
        text = departureStation
        _, _, bitmap = cachedBitmapText(text, fontBold)
        draw.bitmap((int(xOffset), 0), bitmap, fill="yellow")

def renderDots(draw=None, width=None, height=None):
    if draw is None:
        # Return drawing function when called with no arguments
        def drawText(draw, width=None, height=None, x=0, y=0):
            text = ".  .  ."
            draw.text((x, y), text=text, font=fontBold, fill="yellow")
        return drawText
    else:
        # Direct call with arguments
        text = ".  .  ."
        draw.text((0, 0), text=text, font=fontBold, fill="yellow")


from tfl import get_tfl_station, get_tfl_arrivals, convert_tfl_arrivals

def loadData(apiConfig, screenConfig, config):
    """Load departure data based on screen mode (rail or tfl)"""
    if screenConfig["mode"] == "tfl" and config["tfl"]["enabled"]:
        # Try TfL data
        tfl_station = get_tfl_station(config, screenConfig)
        if tfl_station:
            arrivals = get_tfl_arrivals(config, tfl_station)
            if arrivals:
                converted_arrivals = convert_tfl_arrivals(arrivals, config["tfl"]["mode"])
                if converted_arrivals:
                    return converted_arrivals, converted_arrivals[0]["calling_at_list"], tfl_station.name
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

def drawDebugScreen(device, width, height, screen="1", showTime=False):
    virtualViewport = viewport(device, width=width, height=height)

    versionNumber = getVersionNumber().strip()
    
    ipAddress = getIp()

    macAddress = ':'.join(re.findall('..', '%012x' % uuid.getnode())).upper()

    debugLines = {}

    # ok let's build the strings, there's a bit of optional data here so let's do it the old fashioned way with appends

    debugLines["1A"] = "Display"

    screen_config = config["screen1"] if screen == "1" else config["screen2"]
    
    debugLines["1B"] = f"= {screen_config['departureStation']}"

    # has a destination been set? add it in!
    if screen_config["destinationStation"]:
        debugLines["1B"] += f"->{screen_config['destinationStation']}"

    # what about a platform?
    if screen_config["platform"]:
        debugLines["1B"] += f" (Plat{screen_config['platform']}) "
    else:
        debugLines["1B"] += " (PlatAll) "
        
    # Add mode information
    debugLines["1B"] += f" [{screen_config['mode'].upper()}]"

    # refresh time
    debugLines["1B"] += f"{config['refreshTime']}s "
    
    # this wasn't set on my default so will wrap it in if, just in case
    if(config['api']['operatingHours']):
        debugLines["1B"] += f"{config['api']['operatingHours']}h"
    
    debugLines["2A"] = "Script"
    debugLines["2B"] = f"= T_D_D:  {versionNumber}"

    debugLines["3A"] = "Address"
    debugLines["3B"] = f"= {macAddress}"
    debugLines["3C"] = f"IP={ipAddress}"

    theBox = snapshot(width, 64, renderDebugScreen(debugLines), interval=config["refreshTime"])
    virtualViewport.add_hotspot(theBox, (0, 0))

    if(showTime):
        rowTime = snapshot(width, 14, renderTime, interval=0.1)
        virtualViewport.add_hotspot(rowTime, (0, 50))

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
    # this will skip a second sometimes if set to 1, but a hotspot burns CPU
    # so set to snapshot of 0.1; you won't notice
    rowTime = snapshot(width, 14, renderTime, interval=0.1)

    if len(virtualViewport._hotspots) > 0:
        for vhotspot, xy in virtualViewport._hotspots:
            virtualViewport.remove_hotspot(vhotspot, xy)

    virtualViewport.add_hotspot(rowOne, (0, 0))
    virtualViewport.add_hotspot(rowTwo, (0, 12))
    virtualViewport.add_hotspot(rowThree, (0, 24))
    virtualViewport.add_hotspot(rowTime, (0, 50))

    return virtualViewport


def platform_filter(departureData, platformNumber, station):
    platformDepartures = []
    for sub in departureData:
        if platformNumber == "":
            platformDepartures.append(sub)
        elif sub.get('platform') is not None:
            # Convert both to strings for comparison
            platform = str(sub['platform']).strip()
            if platform == str(platformNumber).strip():
                platformDepartures.append(sub)

    if len(platformDepartures) > 0:
        firstDepartureDestinations = platformDepartures[0]["calling_at_list"]
        platformData = platformDepartures, firstDepartureDestinations, station
    else:
        # Return False to trigger blank signage with station name
        platformData = False, False, station

    return platformData


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

try:
    print('Starting Train Departure Display v' + getVersionNumber())
    config = loadConfig()

    # Initialize displays and required classes
    device, device1, canvas_class, viewport_class, snapshot_class = initialize_displays(config)
    
    font = makeFont("Dot Matrix Regular.ttf", 10)
    fontBold = makeFont("Dot Matrix Bold.ttf", 10)
    fontBoldTall = makeFont("Dot Matrix Bold Tall.ttf", 10)
    fontBoldLarge = makeFont("Dot Matrix Bold.ttf", 20)

    widgetWidth = 256
    widgetHeight = 64

    stationRenderCount = 0
    pauseCount = 0
    loop_count = 0

    regulator = framerate_regulator(config['targetFPS'])

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
                if timeNow - timeAtStart >= config["refreshTime"]:
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
                            print("Raw departure data:")
                            for dep in departureData:
                                print(f"Platform: '{dep.get('platform', 'None')}' for {dep.get('destination_name', 'Unknown')}")
                            screenData = platform_filter(departureData, config["screen1"]["platform"], station)
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
                                virtual1 = drawSignage(device1, width=widgetWidth, height=widgetHeight, data=screenData)

                    timeAtStart = time.time()

                timeNow = time.time()
                virtual.refresh()
                if config['dualScreen']:
                    virtual1.refresh()

except KeyboardInterrupt:
    pass
except ValueError as err:
    print(f"Error: {err}")
# except KeyError as err:
#     print(f"Error: Please ensure the {err} environment variable is set")
