from datetime import datetime
from PIL import Image, ImageDraw
from luma.core.virtual import viewport, snapshot

class BaseRenderer:
    def __init__(self, font, fontBold, fontBoldTall, fontBoldLarge, config):
        self.font = font
        self.fontBold = fontBold
        self.fontBoldTall = fontBoldTall
        self.fontBoldLarge = fontBoldLarge
        self.config = config
        self.stationRenderCount = 0
        self.pauseCount = 0
        self.pixelsLeft = 1
        self.pixelsUp = 0
        self.hasElevated = 0
        self.bitmapRenderCache = {}

    def cachedBitmapText(self, text, font):
        # cache the bitmap representation of the stations string
        nameTuple = font.getname()
        fontKey = ''
        for item in nameTuple:
            fontKey = fontKey + item
        key = text + fontKey
        if key in self.bitmapRenderCache:
            # found in cache; re-use it
            pre = self.bitmapRenderCache[key]
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
            self.bitmapRenderCache[key] = {'bitmap': bitmap, 'txt_width': txt_width, 'txt_height': txt_height}
        return txt_width, txt_height, bitmap

    def drawStartup(self, device, width, height):
        virtualViewport = viewport(device, width=width, height=height)

        # Create a new image for drawing - use mode "1" for hardware displays
        image = Image.new('1', (width, height), 0)  # 0 = black in mode "1"
        draw = ImageDraw.Draw(image)

        nameSize = int(self.fontBold.getlength("UK Train Departure Display"))
        poweredSize = int(self.fontBold.getlength("Powered by"))
        NRESize = int(self.fontBold.getlength("National Rail Enquiries"))

        rowOne = snapshot(width, 10, self.renderName((width - nameSize) / 2), interval=10)
        rowThree = snapshot(width, 10, self.renderPoweredBy((width - poweredSize) / 2), interval=10)
        rowFour = snapshot(width, 10, self.renderNRE((width - NRESize) / 2), interval=10)

        if len(virtualViewport._hotspots) > 0:
            for hotspot, xy in virtualViewport._hotspots:
                virtualViewport.remove_hotspot(hotspot, xy)

        virtualViewport.add_hotspot(rowOne, (0, 0))
        virtualViewport.add_hotspot(rowThree, (0, 24))
        virtualViewport.add_hotspot(rowFour, (0, 36))

        device.display(image)
        return virtualViewport

    def drawBlankSignage(self, device, width, height, departureStation):
        welcomeSize = int(self.fontBold.getlength("Welcome to"))
        stationSize = int(self.fontBold.getlength(departureStation))

        device.clear()

        virtualViewport = viewport(device, width=width, height=height)

        rowOne = snapshot(width, 10, self.renderWelcomeTo(
            (width - welcomeSize) / 2), interval=self.config["refreshTime"])
        rowTwo = snapshot(width, 10, self.renderDepartureStation(
            departureStation, (width - stationSize) / 2), interval=self.config["refreshTime"])
        rowThree = snapshot(width, 10, self.renderDots, interval=self.config["refreshTime"])
        rowTime = snapshot(width, 14, self.renderTime, interval=0.1)

        if len(virtualViewport._hotspots) > 0:
            for vhotspot, xy in virtualViewport._hotspots:
                virtualViewport.remove_hotspot(vhotspot, xy)

        virtualViewport.add_hotspot(rowOne, (0, 0))
        virtualViewport.add_hotspot(rowTwo, (0, 12))
        virtualViewport.add_hotspot(rowThree, (0, 24))
        virtualViewport.add_hotspot(rowTime, (0, 50))

        return virtualViewport

    def renderCallingAt(self, draw=None, width=None, height=None):
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                stations = "Calling at: "
                _, _, bitmap = self.cachedBitmapText(stations, self.font)
                draw.bitmap((x, y), bitmap, fill="yellow")
            return drawText
        else:
            stations = "Calling at: "
            _, _, bitmap = self.cachedBitmapText(stations, self.font)
            draw.bitmap((0, 0), bitmap, fill="yellow")

    def renderStations(self, stations, draw=None, width=None, height=None):
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                if len(stations) == self.stationRenderCount - 5:
                    self.stationRenderCount = 0

                txt_width, txt_height, bitmap = self.cachedBitmapText(stations, self.font)

                if self.hasElevated:
                    draw.bitmap((x + self.pixelsLeft - 1, y), bitmap, fill="yellow")
                    if -self.pixelsLeft > txt_width and self.pauseCount < 8:
                        self.pauseCount += 1
                        self.pixelsLeft = 0
                        self.hasElevated = 0
                    else:
                        self.pauseCount = 0
                        self.pixelsLeft = self.pixelsLeft - 1
                else:
                    draw.bitmap((x, y + txt_height - self.pixelsUp), bitmap, fill="yellow")
                    if self.pixelsUp == txt_height:
                        self.pauseCount += 1
                        if self.pauseCount > 20:
                            self.hasElevated = 1
                            self.pixelsUp = 0
                    else:
                        self.pixelsUp = self.pixelsUp + 1
            return drawText
        else:
            if len(stations) == self.stationRenderCount - 5:
                self.stationRenderCount = 0

            txt_width, txt_height, bitmap = self.cachedBitmapText(stations, self.font)

            if self.hasElevated:
                draw.bitmap((self.pixelsLeft - 1, 0), bitmap, fill="yellow")
                if -self.pixelsLeft > txt_width and self.pauseCount < 8:
                    self.pauseCount += 1
                    self.pixelsLeft = 0
                    self.hasElevated = 0
                else:
                    self.pauseCount = 0
                    self.pixelsLeft = self.pixelsLeft - 1
            else:
                draw.bitmap((0, txt_height - self.pixelsUp), bitmap, fill="yellow")
                if self.pixelsUp == txt_height:
                    self.pauseCount += 1
                    if self.pauseCount > 20:
                        self.hasElevated = 1
                        self.pixelsUp = 0
                else:
                    self.pixelsUp = self.pixelsUp + 1

    def renderTime(self, draw=None, width=None, height=None):
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                rawTime = datetime.now().time()
                hour, minute, second = str(rawTime).split('.')[0].split(':')

                w1, _, HMBitmap = self.cachedBitmapText("{}:{}".format(hour, minute), self.fontBoldLarge)
                w2, _, _ = self.cachedBitmapText(':00', self.fontBoldTall)
                _, _, SBitmap = self.cachedBitmapText(':{}'.format(second), self.fontBoldTall)

                draw.bitmap((x + (width - w1 - w2) / 2, y), HMBitmap, fill="yellow")
                draw.bitmap((x + (width - w1 - w2) / 2 + w1, y + 5), SBitmap, fill="yellow")
            return drawText
        else:
            rawTime = datetime.now().time()
            hour, minute, second = str(rawTime).split('.')[0].split(':')

            w1, _, HMBitmap = self.cachedBitmapText("{}:{}".format(hour, minute), self.fontBoldLarge)
            w2, _, _ = self.cachedBitmapText(':00', self.fontBoldTall)
            _, _, SBitmap = self.cachedBitmapText(':{}'.format(second), self.fontBoldTall)

            draw.bitmap(((width - w1 - w2) / 2, 0), HMBitmap, fill="yellow")
            draw.bitmap(((width - w1 - w2) / 2 + w1, 5), SBitmap, fill="yellow")

    def renderWelcomeTo(self, xOffset, draw=None, width=None, height=None):
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                text = "Welcome to"
                _, _, bitmap = self.cachedBitmapText(text, self.fontBold)
                draw.bitmap((x + int(xOffset), y), bitmap, fill="yellow")
            return drawText
        else:
            text = "Welcome to"
            _, _, bitmap = self.cachedBitmapText(text, self.fontBold)
            draw.bitmap((int(xOffset), 0), bitmap, fill="yellow")

    def renderPoweredBy(self, xOffset, draw=None, width=None, height=None):
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                text = "Powered by"
                _, _, bitmap = self.cachedBitmapText(text, self.fontBold)
                draw.bitmap((x + int(xOffset), y), bitmap, fill="yellow")
            return drawText
        else:
            text = "Powered by"
            _, _, bitmap = self.cachedBitmapText(text, self.fontBold)
            draw.bitmap((int(xOffset), 0), bitmap, fill="yellow")

    def renderNRE(self, xOffset, draw=None, width=None, height=None):
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                text = "National Rail Enquiries"
                _, _, bitmap = self.cachedBitmapText(text, self.fontBold)
                draw.bitmap((x + int(xOffset), y), bitmap, fill="yellow")
            return drawText
        else:
            text = "National Rail Enquiries"
            _, _, bitmap = self.cachedBitmapText(text, self.fontBold)
            draw.bitmap((int(xOffset), 0), bitmap, fill="yellow")

    def renderName(self, xOffset, draw=None, width=None, height=None):
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                text = "UK Train Departure Display"
                _, _, bitmap = self.cachedBitmapText(text, self.fontBold)
                draw.bitmap((x + int(xOffset), y), bitmap, fill="yellow")
            return drawText
        else:
            text = "UK Train Departure Display"
            _, _, bitmap = self.cachedBitmapText(text, self.fontBold)
            draw.bitmap((int(xOffset), 0), bitmap, fill="yellow")

    def renderDepartureStation(self, departureStation, xOffset, draw=None, width=None, height=None):
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                text = departureStation
                _, _, bitmap = self.cachedBitmapText(text, self.fontBold)
                draw.bitmap((x + int(xOffset), y), bitmap, fill="yellow")
            return drawText
        else:
            text = departureStation
            _, _, bitmap = self.cachedBitmapText(text, self.fontBold)
            draw.bitmap((int(xOffset), 0), bitmap, fill="yellow")

    def renderDots(self, draw=None, width=None, height=None):
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                text = ".  .  ."
                draw.text((x, y), text=text, font=self.fontBold, fill="yellow")
            return drawText
        else:
            text = ".  .  ."
            draw.text((0, 0), text=text, font=self.fontBold, fill="yellow")

    def drawDebugScreen(self, device, width, height, showTime=False, screen="1"):
        """Draw debug information screen"""
        virtualViewport = viewport(device, width=width, height=height)

        # Create a new image for drawing
        image = Image.new('1', (width, height), 0)
        draw = ImageDraw.Draw(image)

        # Draw debug text
        text = f"Screen {screen} - Debug Mode"
        _, _, bitmap = self.cachedBitmapText(text, self.fontBold)
        draw.bitmap((10, 10), bitmap, fill="yellow")

        if showTime:
            rawTime = datetime.now().time()
            timeText = rawTime.strftime("%H:%M:%S")
            _, _, timeBitmap = self.cachedBitmapText(timeText, self.fontBold)
            draw.bitmap((10, 30), timeBitmap, fill="yellow")

        device.display(image)
        return virtualViewport

class RailRenderer(BaseRenderer):
    def drawSignage(self, device, width, height, data):
        virtualViewport = viewport(device, width=width, height=height)

        status = "Exp 00:00"
        callingAt = "Calling at: "

        departures, firstDepartureDestinations, departureStation = data

        w = int(self.font.getlength(callingAt))

        callingWidth = w
        width = virtualViewport.width

        # First measure the text size
        w = int(self.font.getlength(status))
        pw = int(self.font.getlength("Plat 88"))

        if not departures:
            noTrains = self.drawBlankSignage(device, width=width, height=height, departureStation=departureStation)
            return noTrains

        firstFont = self.font
        if self.config['firstDepartureBold']:
            firstFont = self.fontBold

        rowOneA = snapshot(
            width - w - pw - 5, 10, self.renderDestination(departures[0], firstFont, '1st'), interval=self.config["refreshTime"])
        rowOneB = snapshot(w, 10, self.renderServiceStatus(
            departures[0]), interval=10)
        rowOneC = snapshot(pw, 10, self.renderPlatform(departures[0]), interval=self.config["refreshTime"])
        rowTwoA = snapshot(callingWidth, 10, self.renderCallingAt, interval=self.config["refreshTime"])
        rowTwoB = snapshot(width - callingWidth, 10,
                        self.renderStations(firstDepartureDestinations), interval=0.02)

        if len(departures) > 1:
            rowThreeA = snapshot(width - w - pw, 10, self.renderDestination(
                departures[1], self.font, '2nd'), interval=self.config["refreshTime"])
            rowThreeB = snapshot(w, 10, self.renderServiceStatus(
                departures[1]), interval=self.config["refreshTime"])
            rowThreeC = snapshot(pw, 10, self.renderPlatform(departures[1]), interval=self.config["refreshTime"])

        if len(departures) > 2:
            rowFourA = snapshot(width - w - pw, 10, self.renderDestination(
                departures[2], self.font, '3rd'), interval=10)
            rowFourB = snapshot(w, 10, self.renderServiceStatus(
                departures[2]), interval=10)
            rowFourC = snapshot(pw, 10, self.renderPlatform(departures[2]), interval=self.config["refreshTime"])

        rowTime = snapshot(width, 14, self.renderTime, interval=0.1)

        if len(virtualViewport._hotspots) > 0:
            for vhotspot, xy in virtualViewport._hotspots:
                virtualViewport.remove_hotspot(vhotspot, xy)

        self.stationRenderCount = 0
        self.pauseCount = 0

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

    def renderDestination(self, departure, font, pos, draw=None, width=None, height=None):
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                if self.config["showDepartureNumbers"]:
                    train = f"{pos}  {departure['aimed_departure_time']}  {departure['destination_name']}"
                else:
                    train = f"{departure['aimed_departure_time']}  {departure['destination_name']}"
                _, _, bitmap = self.cachedBitmapText(train, font)
                draw.bitmap((x, y), bitmap, fill="yellow")
            return drawText
        else:
            if self.config["showDepartureNumbers"]:
                train = f"{pos}  {departure['aimed_departure_time']}  {departure['destination_name']}"
            else:
                train = f"{departure['aimed_departure_time']}  {departure['destination_name']}"
            _, _, bitmap = self.cachedBitmapText(train, font)
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

class TflRenderer(BaseRenderer):
    def drawSignage(self, device, width, height, data):
        virtualViewport = viewport(device, width=width, height=height)

        status = "Exp 00:00"
        callingAt = "Calling at: "

        departures, firstDepartureDestinations, departureStation = data

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

        rowOneA = snapshot(
            width - w - pw - tw - total_spacing, 10, self.renderDestination(departures[0], firstFont, '1st'), interval=self.config["refreshTime"])
        rowOneB = snapshot(tw, 10, self.renderTimeToArrival(
            departures[0]), interval=self.config["refreshTime"])
        rowOneC = snapshot(w, 10, self.renderServiceStatus(
            departures[0]), interval=10)
        if self.config["tfl"]["showPlatform"]:
            rowOneD = snapshot(pw, 10, self.renderPlatform(departures[0]), interval=self.config["refreshTime"])
        rowTwoA = snapshot(callingWidth, 10, self.renderCallingAt, interval=self.config["refreshTime"])
        rowTwoB = snapshot(width - callingWidth, 10,
                        self.renderStations(firstDepartureDestinations), interval=0.02)

        if len(departures) > 1:
            rowThreeA = snapshot(width - w - pw - tw - total_spacing, 10, self.renderDestination(
                departures[1], self.font, '2nd'), interval=self.config["refreshTime"])
            rowThreeB = snapshot(tw, 10, self.renderTimeToArrival(
                departures[1]), interval=self.config["refreshTime"])
            rowThreeC = snapshot(w, 10, self.renderServiceStatus(
                departures[1]), interval=self.config["refreshTime"])
            if self.config["tfl"]["showPlatform"]:
                rowThreeD = snapshot(pw, 10, self.renderPlatform(departures[1]), interval=self.config["refreshTime"])

        if len(departures) > 2:
            rowFourA = snapshot(width - w - pw - tw - total_spacing, 10, self.renderDestination(
                departures[2], self.font, '3rd'), interval=10)
            rowFourB = snapshot(tw, 10, self.renderTimeToArrival(
                departures[2]), interval=self.config["refreshTime"])
            rowFourC = snapshot(w, 10, self.renderServiceStatus(
                departures[2]), interval=10)
            if self.config["tfl"]["showPlatform"]:
                rowFourD = snapshot(pw, 10, self.renderPlatform(departures[2]), interval=self.config["refreshTime"])

        rowTime = snapshot(width, 14, self.renderTime, interval=0.1)

        if len(virtualViewport._hotspots) > 0:
            for vhotspot, xy in virtualViewport._hotspots:
                virtualViewport.remove_hotspot(vhotspot, xy)

        self.stationRenderCount = 0
        self.pauseCount = 0

        # Position hotspots based on visible columns
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

        if len(departures) > 2:
            virtualViewport.add_hotspot(rowFourA, (0, 36))
            virtualViewport.add_hotspot(rowFourB, (width - w - pw - tw - spacing * (2 if self.config["tfl"]["showPlatform"] else 1), 36))
            virtualViewport.add_hotspot(rowFourC, (width - w - (pw + spacing if self.config["tfl"]["showPlatform"] else 0), 36))
            if self.config["tfl"]["showPlatform"]:
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

def create_renderer(font, fontBold, fontBoldTall, fontBoldLarge, config, mode):
    """Factory function to create the appropriate renderer based on mode"""
    if mode == "tfl":
        return TflRenderer(font, fontBold, fontBoldTall, fontBoldLarge, config)
    else:
        return RailRenderer(font, fontBold, fontBoldTall, fontBoldLarge, config)
