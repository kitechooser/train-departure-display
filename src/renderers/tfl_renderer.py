from PIL import Image, ImageDraw
from luma.core.virtual import viewport, snapshot
from .base_renderer import BaseRenderer

class TflRenderer(BaseRenderer):
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
