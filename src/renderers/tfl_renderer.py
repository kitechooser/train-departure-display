from PIL import Image, ImageDraw
from luma.core.virtual import viewport, snapshot
from .base_renderer import BaseRenderer
import time
from src.tfl_status_detailed import get_detailed_line_status

class TflRenderer(BaseRenderer):
    def __init__(self, font, fontBold, fontBoldTall, fontBoldLarge, config):
        super().__init__(font, fontBold, fontBoldTall, fontBoldLarge, config)
        self.last_status_query = 0
        self.last_status_announcement = 0
        self.current_line_status = None
        self.status_display_start = 0
        self.showing_status = False

    def drawStartup(self, device, width, height):
        virtualViewport = viewport(device, width=width, height=height)

        # Create a new image for drawing - use mode "1" for hardware displays
        image = Image.new('1', (width, height), 0)  # 0 = black in mode "1"
        draw = ImageDraw.Draw(image)

        nameSize = int(self.fontBold.getlength("UK Train Departure Display"))
        poweredSize = int(self.fontBold.getlength("Powered by"))
        attributionSize = int(self.fontBold.getlength("Transport for London"))

        rowOne = snapshot(width, 10, self.renderName((width - nameSize) / 2), interval=10)
        rowThree = snapshot(width, 10, self.renderPoweredBy((width - poweredSize) / 2), interval=10)
        rowFour = snapshot(width, 10, self.renderAttribution((width - attributionSize) / 2), interval=10)

        if len(virtualViewport._hotspots) > 0:
            for hotspot, xy in virtualViewport._hotspots:
                virtualViewport.remove_hotspot(hotspot, xy)

        virtualViewport.add_hotspot(rowOne, (0, 0))
        virtualViewport.add_hotspot(rowThree, (0, 24))
        virtualViewport.add_hotspot(rowFour, (0, 36))

        device.display(image)
        return virtualViewport

    def renderAttribution(self, xOffset, draw=None, width=None, height=None):
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                text = "Transport for London"
                _, _, bitmap = self.cachedBitmapText(text, self.fontBold)
                draw.bitmap((x + int(xOffset), y), bitmap, fill="yellow")
            return drawText
        else:
            text = "Transport for London"
            _, _, bitmap = self.cachedBitmapText(text, self.fontBold)
            draw.bitmap((int(xOffset), 0), bitmap, fill="yellow")

    def check_and_update_line_status(self):
        """Check if it's time to query line status and update if needed"""
        current_time = time.time()
        
        # Check if status updates are enabled
        if not self.config["tfl"]["status"]["enabled"]:
            return
            
        # Check if it's time to query status
        if current_time - self.last_status_query >= self.config["tfl"]["status"]["queryInterval"]:
            # Get the line name from the first departure's line if available
            line_name = None
            if hasattr(self, 'current_departures') and self.current_departures:
                line_name = self.current_departures[0].get('line', '').lower()
            
            if line_name:
                self.current_line_status = get_detailed_line_status(line_name)
                self.last_status_query = current_time
                
                # Check if it's time to announce the status
                if current_time - self.last_status_announcement >= self.config["tfl"]["status"]["announcementInterval"]:
                    if hasattr(self, 'announcer') and self.config["announcements"]["enabled"]:
                        # Format the status message for announcement
                        status_text = self.current_line_status.replace("\n", ". ")
                        self.announcer.announce_line_status(status_text)
                        self.last_status_announcement = current_time

    def should_show_status(self):
        """Determine if we should show status instead of third departure"""
        if not self.config["tfl"]["status"]["enabled"] or not self.current_line_status:
            self.showing_status = False
            return False
            
        current_time = time.time()
        
        # If we're not showing status, check if we should start
        if not self.showing_status:
            if len(self.current_departures) > 2:  # Only show status if we have a third departure to replace
                self.showing_status = True
                self.status_display_start = current_time
                return True
        # If we are showing status, check if we should continue
        else:
            if current_time - self.status_display_start < self.config["tfl"]["status"]["displayDuration"]:
                return True
            else:
                # Reset status display after duration expires
                self.showing_status = False
                self.status_display_start = 0
                return False
                
        return False

    def renderLineStatus(self, draw=None, width=None, height=None):
        """Render the current line status"""
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                if self.current_line_status:
                    # Replace newlines with spaces to create a single scrolling line
                    status_text = self.current_line_status.replace("\n", " ")
                    _, _, bitmap = self.cachedBitmapText(status_text, self.font)
                    draw.bitmap((x + self.pixelsLeft - 1, y), bitmap, fill="yellow")
            return drawText
        else:
            if self.current_line_status:
                # Replace newlines with spaces to create a single scrolling line
                status_text = self.current_line_status.replace("\n", " ")
                _, _, bitmap = self.cachedBitmapText(status_text, self.font)
                draw.bitmap((self.pixelsLeft - 1, 0), bitmap, fill="yellow")

    def drawSignage(self, device, width, height, data):
        virtualViewport = viewport(device, width=width, height=height)

        status = "Exp 00:00"
        callingAt = "Calling at: "

        departures, firstDepartureDestinations, departureStation = data
        self.current_departures = departures  # Store for status checks

        # Check and update line status
        self.check_and_update_line_status()

        w = int(self.font.getlength(callingAt))
        callingWidth = w
        width = virtualViewport.width

        # First measure the text size
        w = int(self.font.getlength(status))
        pw = int(self.font.getlength("Plat 88")) if self.config["tfl"]["showPlatform"] else 0
        tw = int(self.font.getlength("88 mins"))  # Width for time to arrival
        spacing = 5  # Add spacing between columns
        
        # Calculate total spacing based on visible columns
        total_spacing = spacing * (3 if self.config["tfl"]["showPlatform"] else 2)

        if not departures:
            noTrains = self.drawBlankSignage(device, width=width, height=height, departureStation=departureStation)
            return noTrains

        firstFont = self.font
        if self.config['firstDepartureBold']:
            firstFont = self.fontBold

        # First departure
        rowOneA = snapshot(
            width - w - pw - tw - total_spacing, 10, self.renderDestination(departures[0], firstFont, '1st'), interval=self.config["refreshTime"])
        rowOneB = snapshot(tw, 10, self.renderTimeToArrival(
            departures[0]), interval=self.config["refreshTime"])
        rowOneC = snapshot(w, 10, self.renderServiceStatus(
            departures[0]), interval=10)
        if self.config["tfl"]["showPlatform"]:
            rowOneD = snapshot(pw, 10, self.renderPlatform(departures[0]), interval=self.config["refreshTime"])

        # Calling points
        rowTwoA = snapshot(callingWidth, 10, self.renderCallingAt, interval=self.config["refreshTime"])
        rowTwoB = snapshot(width - callingWidth, 10,
                        self.renderStations(firstDepartureDestinations), interval=0.02)

        # Second departure
        if len(departures) > 1:
            rowThreeA = snapshot(width - w - pw - tw - total_spacing, 10, self.renderDestination(
                departures[1], self.font, '2nd'), interval=self.config["refreshTime"])
            rowThreeB = snapshot(tw, 10, self.renderTimeToArrival(
                departures[1]), interval=self.config["refreshTime"])
            rowThreeC = snapshot(w, 10, self.renderServiceStatus(
                departures[1]), interval=self.config["refreshTime"])
            if self.config["tfl"]["showPlatform"]:
                rowThreeD = snapshot(pw, 10, self.renderPlatform(departures[1]), interval=self.config["refreshTime"])

        # Initialize status row
        rowFourStatus = None
        rowFourA = None
        rowFourB = None
        rowFourC = None
        rowFourD = None

        # Third departure or status
        if len(departures) > 2 and not self.should_show_status():
            rowFourA = snapshot(width - w - pw - tw - total_spacing, 10, self.renderDestination(
                departures[2], self.font, '3rd'), interval=10)
            rowFourB = snapshot(tw, 10, self.renderTimeToArrival(
                departures[2]), interval=self.config["refreshTime"])
            rowFourC = snapshot(w, 10, self.renderServiceStatus(
                departures[2]), interval=10)
            if self.config["tfl"]["showPlatform"]:
                rowFourD = snapshot(pw, 10, self.renderPlatform(departures[2]), interval=self.config["refreshTime"])
        elif self.should_show_status():
            rowFourStatus = snapshot(width, 10, self.renderLineStatus, interval=0.02)

        rowTime = snapshot(width, 14, self.renderTime, interval=0.1)

        if len(virtualViewport._hotspots) > 0:
            for vhotspot, xy in virtualViewport._hotspots:
                virtualViewport.remove_hotspot(vhotspot, xy)

        self.stationRenderCount = 0
        self.pauseCount = 0

        # Position hotspots
        virtualViewport.add_hotspot(rowOneA, (0, 0))
        virtualViewport.add_hotspot(rowOneB, (width - w - pw - tw - spacing * (2 if self.config["tfl"]["showPlatform"] else 1), 0))
        virtualViewport.add_hotspot(rowOneC, (width - w - (pw + spacing if self.config["tfl"]["showPlatform"] else 0), 0))
        if self.config["tfl"]["showPlatform"]:
            virtualViewport.add_hotspot(rowOneD, (width - pw, 0))
        virtualViewport.add_hotspot(rowTwoA, (0, 12))
        virtualViewport.add_hotspot(rowTwoB, (callingWidth, 12))

        if len(departures) > 1:
            virtualViewport.add_hotspot(rowThreeA, (0, 24))
            virtualViewport.add_hotspot(rowThreeB, (width - w - pw - tw - spacing * (2 if self.config["tfl"]["showPlatform"] else 1), 24))
            virtualViewport.add_hotspot(rowThreeC, (width - w - (pw + spacing if self.config["tfl"]["showPlatform"] else 0), 24))
            if self.config["tfl"]["showPlatform"]:
                virtualViewport.add_hotspot(rowThreeD, (width - pw, 24))

        # Add hotspots for fourth row
        if rowFourStatus is not None:
            virtualViewport.add_hotspot(rowFourStatus, (0, 36))
        elif rowFourA is not None:
            virtualViewport.add_hotspot(rowFourA, (0, 36))
            virtualViewport.add_hotspot(rowFourB, (width - w - pw - tw - spacing * (2 if self.config["tfl"]["showPlatform"] else 1), 36))
            virtualViewport.add_hotspot(rowFourC, (width - w - (pw + spacing if self.config["tfl"]["showPlatform"] else 0), 36))
            if self.config["tfl"]["showPlatform"] and rowFourD is not None:
                virtualViewport.add_hotspot(rowFourD, (width - pw, 36))

        virtualViewport.add_hotspot(rowTime, (0, 50))

        return virtualViewport

    def renderDestination(self, departure, font, pos, draw=None, width=None, height=None):
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                if self.config["showDepartureNumbers"]:
                    train = f"{pos}  {departure['destination_name']}"
                else:
                    train = departure['destination_name']
                _, _, bitmap = self.cachedBitmapText(train, font)
                draw.bitmap((x, y), bitmap, fill="yellow")
            return drawText
        else:
            if self.config["showDepartureNumbers"]:
                train = f"{pos}  {departure['destination_name']}"
            else:
                train = departure['destination_name']
            _, _, bitmap = self.cachedBitmapText(train, font)
            draw.bitmap((0, 0), bitmap, fill="yellow")

    def renderTimeToArrival(self, departure, draw=None, width=None, height=None):
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                train = departure['aimed_departure_time']
                _, _, bitmap = self.cachedBitmapText(train, self.font)
                draw.bitmap((x, y), bitmap, fill="yellow")
            return drawText
        else:
            train = departure['aimed_departure_time']
            _, _, bitmap = self.cachedBitmapText(train, self.font)
            draw.bitmap((0, 0), bitmap, fill="yellow")

    def renderServiceStatus(self, departure, draw=None, width=None, height=None):
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
                w, _, bitmap = self.cachedBitmapText(train, self.font)
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
            w, _, bitmap = self.cachedBitmapText(train, self.font)
            draw.bitmap((width - w, 0), bitmap, fill="yellow")

    def renderPlatform(self, departure, draw=None, width=None, height=None):
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
                _, _, bitmap = self.cachedBitmapText(platform, self.font)
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
            _, _, bitmap = self.cachedBitmapText(platform, self.font)
            draw.bitmap((0, 0), bitmap, fill="yellow")
