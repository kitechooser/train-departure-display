import logging

logger = logging.getLogger(__name__)

class RowRenderer:
    def __init__(self, config, font, fontBold):
        self.config = config
        self.font = font
        self.fontBold = fontBold
        # Calling points animation states
        self.stationPixelsLeft = 0
        self.stationPixelsUp = 0
        self.stationElevated = False
        self.stationPauseCount = 0
        self.stationRenderCount = 0

    def render_destination(self, departure, font, pos, draw=None, width=None, height=None, cached_bitmap_text=None):
        """Render the destination text"""
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                if self.config["showDepartureNumbers"]:
                    train = f"{pos}  {departure['destination_name']}"
                else:
                    train = departure['destination_name']
                _, _, bitmap = cached_bitmap_text(train, font)
                draw.bitmap((x, y), bitmap, fill="yellow")
            return drawText
        else:
            if self.config["showDepartureNumbers"]:
                train = f"{pos}  {departure['destination_name']}"
            else:
                train = departure['destination_name']
            _, _, bitmap = cached_bitmap_text(train, font)
            draw.bitmap((0, 0), bitmap, fill="yellow")

    def render_time_to_arrival(self, departure, draw=None, width=None, height=None, cached_bitmap_text=None):
        """Render the arrival time"""
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                train = departure['aimed_departure_time']
                _, _, bitmap = cached_bitmap_text(train, self.font)
                draw.bitmap((x, y), bitmap, fill="yellow")
            return drawText
        else:
            train = departure['aimed_departure_time']
            _, _, bitmap = cached_bitmap_text(train, self.font)
            draw.bitmap((0, 0), bitmap, fill="yellow")

    def render_service_status(self, departure, draw=None, width=None, height=None, cached_bitmap_text=None):
        """Render the service status"""
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
                w, _, bitmap = cached_bitmap_text(train, self.font)
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
            w, _, bitmap = cached_bitmap_text(train, self.font)
            draw.bitmap((width - w, 0), bitmap, fill="yellow")

    def render_platform(self, departure, draw=None, width=None, height=None, cached_bitmap_text=None):
        """Render the platform number"""
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
                _, _, bitmap = cached_bitmap_text(platform, self.font)
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
            _, _, bitmap = cached_bitmap_text(platform, self.font)
            draw.bitmap((0, 0), bitmap, fill="yellow")

    def render_calling_at(self, draw=None, width=None, height=None, cached_bitmap_text=None):
        """Render the 'Calling at:' text"""
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                text = "Calling at: "
                _, _, bitmap = cached_bitmap_text(text, self.font)
                draw.bitmap((x, y), bitmap, fill="yellow")
            return drawText
        else:
            text = "Calling at: "
            _, _, bitmap = cached_bitmap_text(text, self.font)
            draw.bitmap((0, 0), bitmap, fill="yellow")

    def render_stations(self, stations, draw=None, width=None, height=None, cached_bitmap_text=None):
        """Render the calling points with animation"""
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                if len(stations) == self.stationRenderCount - 5:
                    self.stationRenderCount = 0

                txt_width, txt_height, bitmap = cached_bitmap_text(stations, self.font)

                # Always start with roll-up animation
                if not self.stationElevated:
                    draw.bitmap((x, y + txt_height - self.stationPixelsUp), bitmap, fill="yellow")
                    if self.stationPixelsUp >= txt_height - 1:
                        self.stationPauseCount += 1
                        if self.stationPauseCount > 20:
                            self.stationElevated = True
                            self.stationPixelsLeft = 0  # Start from left edge
                    else:
                        self.stationPixelsUp = min(txt_height - 1, self.stationPixelsUp + 2)  # Speed up roll-up but don't overshoot
                else:
                    # Horizontal scroll after elevation
                    draw.bitmap((x + self.stationPixelsLeft - 1, y + 1), bitmap, fill="yellow")
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

            txt_width, txt_height, bitmap = cached_bitmap_text(stations, self.font)

            # Always start with roll-up animation
            if not self.stationElevated:
                draw.bitmap((0, txt_height - self.stationPixelsUp), bitmap, fill="yellow")
                if self.stationPixelsUp >= txt_height - 1:
                    self.stationPauseCount += 1
                    if self.stationPauseCount > 20:
                        self.stationElevated = True
                        self.stationPixelsLeft = 0  # Start from left edge
                else:
                    self.stationPixelsUp = min(txt_height - 1, self.stationPixelsUp + 2)  # Speed up roll-up but don't overshoot
            else:
                # Horizontal scroll after elevation
                draw.bitmap((self.stationPixelsLeft - 1, 1), bitmap, fill="yellow")
                if -self.stationPixelsLeft > txt_width and self.stationPauseCount < 8:
                    self.stationPauseCount += 1
                    self.stationPixelsLeft = 0
                    self.stationElevated = False
                else:
                    self.stationPauseCount = 0
                    self.stationPixelsLeft = self.stationPixelsLeft - 1

    def render_no_trains(self, text, xOffset, draw=None, width=None, height=None, cached_bitmap_text=None):
        """Render the no trains message"""
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                _, _, bitmap = cached_bitmap_text(text, self.font)
                draw.bitmap((x + int(xOffset), y), bitmap, fill="yellow")
            return drawText
        else:
            _, _, bitmap = cached_bitmap_text(text, self.font)
            draw.bitmap((int(xOffset), 0), bitmap, fill="yellow")
