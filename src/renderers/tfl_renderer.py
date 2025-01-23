from PIL import Image, ImageDraw
from luma.core.virtual import viewport, snapshot
from .base_renderer import BaseRenderer
import time
import logging
from src.tfl_status_detailed import get_detailed_line_status

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TflRenderer(BaseRenderer):
    def __init__(self, font, fontBold, fontBoldTall, fontBoldLarge, config):
        super().__init__(font, fontBold, fontBoldTall, fontBoldLarge, config)
        # Status tracking
        self.last_status_query = 0
        self.last_status_announcement = 0
        self.current_line_status = None
        self.status_display_start = 0
        self.last_shown_status = None  # Track last shown status
        
        # Status animation states
        self.showing_status = False
        self.statusElevated = False
        self.statusPixelsUp = 0
        self.statusPixelsLeft = 0  # Start from left edge
        self.statusPauseCount = 0

        # Calling points animation states
        self.stationPixelsLeft = 0  # Start from left edge
        self.stationPixelsUp = 0
        self.stationElevated = False
        self.stationPauseCount = 0
        self.stationRenderCount = 0

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
            rowFourStatus = snapshot(width, 10, self.renderLineStatus, interval=0.02)  # Match calling points speed

        rowTime = snapshot(width, 14, self.renderTime, interval=0.1)

        if len(virtualViewport._hotspots) > 0:
            for vhotspot, xy in virtualViewport._hotspots:
                virtualViewport.remove_hotspot(vhotspot, xy)

        # Don't reset any animation states to keep calling points scrolling

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
                new_status = get_detailed_line_status(line_name)
                logger.info(f"Checking status update - Current: {self.current_line_status}, New: {new_status}, Last shown: {self.last_shown_status}, Showing: {self.showing_status}")
                # Always update current status if it's different
                if new_status != self.current_line_status:
                    logger.info(f"New status different from current - Current: {self.current_line_status}, New: {new_status}, Last shown: {self.last_shown_status}")
                    if not self.showing_status:
                        logger.info("Setting new status since not currently showing")
                        self.current_line_status = new_status
                    else:
                        logger.info("Deferring status update until current display completes")
                else:
                    logger.info("Status unchanged")
                self.last_status_query = current_time
                
                # Only process announcements if they are enabled in config and we have a status
                if (self.config["announcements"]["enabled"] and 
                    self.config["announcements"]["announcement_types"]["line_status"] and
                    self.current_line_status):  # Only announce if we have a status
                    # Check if it's time to announce the status
                    if current_time - self.last_status_announcement >= self.config["tfl"]["status"]["announcementInterval"]:
                        if hasattr(self, 'announcer'):
                            self.announcer.announce_line_status(self.current_line_status)
                            self.last_status_announcement = current_time

    def calculate_scroll_duration(self, text_width):
        """Calculate how long it will take to scroll the text"""
        # Calculate frames needed:
        # - Roll up animation: text_height frames (10)
        # - Pause after roll up: 20 frames
        # - Scroll animation: text_width frames
        # - Pause at end: 8 frames
        # - Add display width to ensure full scroll
        # Calculate frames needed for each animation phase:
        roll_up_frames = 10  # Roll up animation
        roll_up_pause = 20  # Pause after roll up
        scroll_frames = text_width // 2  # Scroll animation (faster scroll)
        end_pause = 8  # Final pause
        
        # Total frames needed for complete animation
        frames_needed = roll_up_frames + roll_up_pause + scroll_frames + end_pause
        
        # Convert frames to seconds (0.02s per frame)
        duration = frames_needed * 0.02
        
        # Add fixed buffer for long messages
        duration += 1  # Add 1 second buffer
        
        logger.info(f"Calculated scroll duration: {duration}s for text width {text_width} (frames: {frames_needed})")
        return duration

    def should_show_status(self):
        """Determine if we should show status instead of third departure"""
        if not self.config["tfl"]["status"]["enabled"] or not self.current_line_status:
            self.showing_status = False
            return False
            
        # If we're not showing status, check if we should start
        if not self.showing_status and self.current_line_status != self.last_shown_status:  # Only show if status changed
            if len(self.current_departures) > 2:  # Only show status if we have a third departure to replace
                # Calculate text width and set display duration
                status_text = self.current_line_status.replace("\n", " ")
                text_width, _, _ = self.cachedBitmapText(status_text, self.font)
                self.status_display_start = time.time()
                self.status_duration = self.calculate_scroll_duration(text_width)
                logger.info(f"Starting status display, duration: {self.status_duration}s")
                self.showing_status = True
                self.statusElevated = False
                self.statusPixelsUp = 0
                self.statusPixelsLeft = 0  # Start from left edge
                return True
        # If we are showing status, check if we should continue
        else:
            current_time = time.time()
            if current_time - self.status_display_start < self.status_duration:
                return True
            else:
                # Reset status display and animation states
                logger.info(f"Status display complete - Current: {self.current_line_status}, Last shown: {self.last_shown_status}")
                self.showing_status = False
                self.statusPauseCount = 0
                self.statusPixelsLeft = 0  # Reset to left edge
                self.statusElevated = False
                self.statusPixelsUp = 0
                if self.current_line_status:  # Only update last shown if we have a status
                    logger.info(f"Marking status as shown: {self.current_line_status}")
                    self.last_shown_status = self.current_line_status
                    self.current_line_status = None  # Reset current status to prevent re-showing
                logger.info("Returning to departure 3")
                return False
                
        return False

    def renderLineStatus(self, draw=None, width=None, height=None):
        """Render the current line status"""
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                if self.current_line_status:
                    # Replace newlines with spaces
                    status_text = self.current_line_status.replace("\n", " ")
                    text_width, text_height, bitmap = self.cachedBitmapText(status_text, self.font)
                    
                    # Always start with roll-up animation
                    if not self.statusElevated:
                        draw.bitmap((x, y + text_height - self.statusPixelsUp), bitmap, fill="yellow")
                        if self.statusPixelsUp == text_height:
                            self.statusPauseCount += 1
                            if self.statusPauseCount > 20:
                                self.statusElevated = True
                                self.statusPixelsUp = 0
                                self.statusPixelsLeft = 0  # Start from left edge
                        else:
                            self.statusPixelsUp = self.statusPixelsUp + 1
                    else:
                        # Horizontal scroll after elevation
                        draw.bitmap((x + self.statusPixelsLeft - 1, y), bitmap, fill="yellow")
                        if -self.statusPixelsLeft > text_width:  # If scrolled past end
                            if self.statusPauseCount < 8:  # Pause briefly at end
                                self.statusPauseCount += 1
                            else:
                                # End status display
                                logger.info(f"Status animation complete - Current: {self.current_line_status}, Last shown: {self.last_shown_status}")
                                self.showing_status = False
                                self.statusPauseCount = 0
                                self.statusPixelsLeft = 0
                                self.statusElevated = False
                                self.statusPixelsUp = 0
                                # Don't update last_shown_status here, it's handled in should_show_status
                        else:
                            self.statusPixelsLeft = self.statusPixelsLeft - 1  # Scroll slower
            return drawText
        else:
            if self.current_line_status:
                # Replace newlines with spaces
                status_text = self.current_line_status.replace("\n", " ")
                text_width, text_height, bitmap = self.cachedBitmapText(status_text, self.font)
                
                # Always start with roll-up animation
                if not self.statusElevated:
                    draw.bitmap((0, text_height - self.statusPixelsUp), bitmap, fill="yellow")
                    if self.statusPixelsUp == text_height:
                        self.statusPauseCount += 1
                        if self.statusPauseCount > 20:
                            self.statusElevated = True
                            self.statusPixelsUp = 0
                            self.statusPixelsLeft = 0  # Start from left edge
                    else:
                        self.statusPixelsUp = self.statusPixelsUp + 1
                else:
                    # Horizontal scroll after elevation
                    draw.bitmap((self.statusPixelsLeft - 1, 0), bitmap, fill="yellow")
                    if -self.statusPixelsLeft > text_width:  # If scrolled past end
                        if self.statusPauseCount < 8:  # Pause briefly at end
                            self.statusPauseCount += 1
                        else:
                            # End status display
                            logger.info(f"Status animation complete - Current: {self.current_line_status}, Last shown: {self.last_shown_status}")
                            self.showing_status = False
                            self.statusPauseCount = 0
                            self.statusPixelsLeft = 0
                            self.statusElevated = False
                            self.statusPixelsUp = 0
                            # Don't update last_shown_status here, it's handled in should_show_status
                    else:
                        self.statusPixelsLeft = self.statusPixelsLeft - 1  # Scroll slower

    def drawBlankSignage(self, device, width, height, departureStation):
        virtualViewport = viewport(device, width=width, height=height)
        image = Image.new('1', (width, height), 0)
        draw = ImageDraw.Draw(image)

        noTrains = "No trains from " + departureStation
        noTrainsWidth = int(self.font.getlength(noTrains))
        noTrainsX = (width - noTrainsWidth) / 2

        rowOne = snapshot(width, 10, self.renderNoTrains(noTrains, noTrainsX), interval=10)
        rowTime = snapshot(width, 14, self.renderTime, interval=0.1)

        if len(virtualViewport._hotspots) > 0:
            for hotspot, xy in virtualViewport._hotspots:
                virtualViewport.remove_hotspot(hotspot, xy)

        virtualViewport.add_hotspot(rowOne, (0, 0))
        virtualViewport.add_hotspot(rowTime, (0, 50))

        device.display(image)
        return virtualViewport

    def renderNoTrains(self, text, xOffset, draw=None, width=None, height=None):
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                _, _, bitmap = self.cachedBitmapText(text, self.font)
                draw.bitmap((x + int(xOffset), y), bitmap, fill="yellow")
            return drawText
        else:
            _, _, bitmap = self.cachedBitmapText(text, self.font)
            draw.bitmap((int(xOffset), 0), bitmap, fill="yellow")

    def renderCallingAt(self, draw=None, width=None, height=None):
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                text = "Calling at: "
                _, _, bitmap = self.cachedBitmapText(text, self.font)
                draw.bitmap((x, y), bitmap, fill="yellow")
            return drawText
        else:
            text = "Calling at: "
            _, _, bitmap = self.cachedBitmapText(text, self.font)
            draw.bitmap((0, 0), bitmap, fill="yellow")

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

    def renderStations(self, stations, draw=None, width=None, height=None):
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                if len(stations) == self.stationRenderCount - 5:
                    self.stationRenderCount = 0

                txt_width, txt_height, bitmap = self.cachedBitmapText(stations, self.font)

                # Always start with roll-up animation
                if not self.stationElevated:
                    draw.bitmap((x, y + txt_height - self.stationPixelsUp), bitmap, fill="yellow")
                    if self.stationPixelsUp == txt_height:
                        self.stationPauseCount += 1
                        if self.stationPauseCount > 20:
                            self.stationElevated = True
                            self.stationPixelsUp = 0
                            self.stationPixelsLeft = 0  # Start from left edge
                    else:
                        self.stationPixelsUp = self.stationPixelsUp + 1
                else:
                    # Horizontal scroll after elevation
                    draw.bitmap((x + self.stationPixelsLeft - 1, y), bitmap, fill="yellow")
                    if -self.stationPixelsLeft > txt_width and self.stationPauseCount < 8:
                        self.stationPauseCount += 1
                        self.stationPixelsLeft = 0
                        self.stationElevated = False
                    else:
                        self.stationPauseCount = 0
                        self.stationPixelsLeft = self.stationPixelsLeft - 1
            return drawText
        else:
            if len(stations) == self.stationRenderCount - 5:
                self.stationRenderCount = 0

            txt_width, txt_height, bitmap = self.cachedBitmapText(stations, self.font)

            # Always start with roll-up animation
            if not self.stationElevated:
                draw.bitmap((0, txt_height - self.stationPixelsUp), bitmap, fill="yellow")
                if self.stationPixelsUp == txt_height:
                    self.stationPauseCount += 1
                    if self.stationPauseCount > 20:
                        self.stationElevated = True
                        self.stationPixelsUp = 0
                        self.stationPixelsLeft = 0  # Start from left edge
                    else:
                        self.stationPixelsUp = self.stationPixelsUp + 1
                else:
                    # Horizontal scroll after elevation
                    draw.bitmap((self.stationPixelsLeft - 1, 0), bitmap, fill="yellow")
                    if -self.stationPixelsLeft > txt_width and self.stationPauseCount < 8:
                        self.stationPauseCount += 1
                        self.stationPixelsLeft = 0
                        self.stationElevated = False
                    else:
                        self.stationPauseCount = 0
                        self.stationPixelsLeft = self.stationPixelsLeft - 1
