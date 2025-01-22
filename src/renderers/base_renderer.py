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
