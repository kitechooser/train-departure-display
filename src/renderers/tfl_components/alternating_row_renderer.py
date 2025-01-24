import logging
import time

logger = logging.getLogger(__name__)

class AlternatingRowRenderer:
    def __init__(self, config, font, fontBold):
        self.config = config
        self.font = font
        self.fontBold = fontBold
        # Animation states
        self.pixelsUp = 0
        self.elevated = False
        self.pauseCount = 0
        self.last_switch_time = 0
        self.current_departure_index = 1  # Start with second departure

    def render_departure_row(self, departures, font, dimensions, width, draw=None, width_param=None, height=None, cached_bitmap_text=None):
        """Render alternating departures with roll-up animation"""
        current_time = time.time()
        
        # Check if it's time to switch departures
        if current_time - self.last_switch_time >= self.config["tfl"]["status"]["alternatingRowInterval"]:
            self.last_switch_time = current_time
            self.current_departure_index = 2 if self.current_departure_index == 1 else 1
            # Reset animation states for roll-up
            self.pixelsUp = 0
            self.elevated = False
            self.pauseCount = 0

        departure = departures[self.current_departure_index]
        pos = '3rd' if self.current_departure_index == 2 else '2nd'

        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                # Get text dimensions
                train = f"{pos}  {departure['destination_name']}" if self.config["showDepartureNumbers"] else departure['destination_name']
                _, txt_height, bitmap = cached_bitmap_text(train, font)

                # Roll-up animation
                if not self.elevated:
                    draw.bitmap((x, y + txt_height - self.pixelsUp), bitmap, fill="yellow")
                    if self.pixelsUp >= txt_height - 1:
                        self.pauseCount += 1
                        if self.pauseCount > 10:  # Shorter pause than calling points
                            self.elevated = True
                    else:
                        self.pixelsUp = min(txt_height - 1, self.pixelsUp + 2)  # Speed up roll-up but don't overshoot
                else:
                    draw.bitmap((x, y + 1), bitmap, fill="yellow")  # Match the vertical position of other rows

            return drawText
        else:
            train = f"{pos}  {departure['destination_name']}" if self.config["showDepartureNumbers"] else departure['destination_name']
            _, txt_height, bitmap = cached_bitmap_text(train, font)

            # Roll-up animation
            if not self.elevated:
                draw.bitmap((0, txt_height - self.pixelsUp), bitmap, fill="yellow")
                if self.pixelsUp >= txt_height - 1:
                    self.pauseCount += 1
                    if self.pauseCount > 10:
                        self.elevated = True
                else:
                    self.pixelsUp = min(txt_height - 1, self.pixelsUp + 2)
            else:
                draw.bitmap((0, 1), bitmap, fill="yellow")  # Match the vertical position of other rows
