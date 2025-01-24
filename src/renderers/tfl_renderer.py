from PIL import Image, ImageDraw
from luma.core.virtual import viewport, snapshot
from .base_renderer import BaseRenderer
from .tfl_components import StatusManager, ViewportManager, RowRenderer, AlternatingRowRenderer
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TflRenderer(BaseRenderer):
    def __init__(self, font, fontBold, fontBoldTall, fontBoldLarge, config):
        super().__init__(font, fontBold, fontBoldTall, fontBoldLarge, config)
        
        # Initialize components
        self.status_manager = StatusManager(config, font)
        self.viewport_manager = ViewportManager(config, font, fontBold)
        self.row_renderer = RowRenderer(config, font, fontBold)
        self.alternating_renderer = AlternatingRowRenderer(config, font, fontBold)

    def drawSignage(self, device, width, height, data):
        # Create viewport
        virtualViewport = self.viewport_manager.create_viewport(device, width, height)
        
        departures, firstDepartureDestinations, departureStation = data
        self.current_departures = departures  # Store for status checks

        # Check and update line status
        self.check_and_update_line_status()

        # Calculate dimensions
        dimensions = self.viewport_manager.calculate_dimensions("Exp 00:00")
        width = virtualViewport.width

        if not departures:
            return self.drawBlankSignage(device, width, height, departureStation)

        # Create snapshots for each row
        rows = {
            'row_one': {'y': 0, 'components': []},
            'row_two': {'y': 12, 'components': []},
            'row_three': {'y': 24, 'components': []},
            'row_four': {'y': 36, 'components': []},
            'row_time': {'y': 50, 'components': []}
        }

        # First departure
        firstFont = self.fontBold if self.config['firstDepartureBold'] else self.font
        rows['row_one']['components'] = self._create_departure_row(departures[0], firstFont, '1st', dimensions, width)

        # Calling points
        callingWidth = int(self.font.getlength("Calling at: "))
        rows['row_two']['components'] = [
            {'type': 'destination', 'snapshot': self.viewport_manager.create_snapshot(callingWidth, 10, self.renderCallingAt, self.config["refreshTime"])},
            {'type': 'destination', 'snapshot': self.viewport_manager.create_snapshot(width - callingWidth, 10, lambda *args: self.renderStations(firstDepartureDestinations, *args), 0.02)}
        ]

        # Second departure
        if len(departures) > 1:
            rows['row_three']['components'] = self._create_departure_row(departures[1], self.font, '2nd', dimensions, width)

        # Third departure or status
        if len(departures) > 2 and not self.should_show_status():
            rows['row_four']['components'] = self._create_departure_row(departures[2], self.font, '3rd', dimensions, width)
        elif self.should_show_status():
            # Show status in row four
            rows['row_four']['components'] = [
                {'type': 'full_width', 'snapshot': self.viewport_manager.create_snapshot(width, 10, self.renderLineStatus, 0.02)}
            ]
            
            # When showing status, use alternating renderer for row three
            if len(departures) > 2:
                # Extract dimensions
                w, pw, tw, spacing, total_spacing = (
                    dimensions['status_width'],
                    dimensions['platform_width'],
                    dimensions['time_width'],
                    dimensions['spacing'],
                    dimensions['total_spacing']
                )
                
                # Create snapshot with alternating renderer
                rows['row_three']['components'] = [
                    {'type': 'destination', 'snapshot': self.viewport_manager.create_snapshot(
                        width - w - pw - tw - total_spacing, 10,
                        lambda draw, w=None, h=None: self.alternating_renderer.render_departure_row(departures, self.font, dimensions, width, draw, w, h, self.cachedBitmapText),
                        0.02  # Fast refresh for smooth animation
                    )},
                    {'type': 'time', 'snapshot': self.viewport_manager.create_snapshot(
                        tw, 10,
                        lambda draw, w=None, h=None: self.renderTimeToArrival(departures[self.alternating_renderer.current_departure_index], draw, w, h),
                        0.02
                    )},
                    {'type': 'status', 'snapshot': self.viewport_manager.create_snapshot(
                        w, 10,
                        lambda draw, w=None, h=None: self.renderServiceStatus(departures[self.alternating_renderer.current_departure_index], draw, w, h),
                        0.02
                    )}
                ]
                if self.config["tfl"]["showPlatform"]:
                    rows['row_three']['components'].append({
                        'type': 'platform',
                        'snapshot': self.viewport_manager.create_snapshot(
                            pw, 10,
                            lambda draw, w=None, h=None: self.renderPlatform(departures[self.alternating_renderer.current_departure_index], draw, w, h),
                            0.02
                        )
                    })

        # Time row
        rows['row_time']['components'] = [
            {'type': 'full_width', 'snapshot': self.viewport_manager.create_snapshot(width, 14, self.renderTime, 0.1)}
        ]

        # Position all hotspots
        self.viewport_manager.position_hotspots(virtualViewport, dimensions, rows, self.config["tfl"]["showPlatform"])

        return virtualViewport

    def _create_departure_row(self, departure, font, pos, dimensions, width):
        """Helper method to create components for a departure row"""
        w, pw, tw, spacing, total_spacing = (
            dimensions['status_width'],
            dimensions['platform_width'],
            dimensions['time_width'],
            dimensions['spacing'],
            dimensions['total_spacing']
        )
        
        components = [
            {'type': 'destination', 'snapshot': self.viewport_manager.create_snapshot(
                width - w - pw - tw - total_spacing, 10,
                lambda *args: self.renderDestination(departure, font, pos, *args),
                self.config["refreshTime"]
            )},
            {'type': 'time', 'snapshot': self.viewport_manager.create_snapshot(
                tw, 10,
                lambda *args: self.renderTimeToArrival(departure, *args),
                self.config["refreshTime"]
            )},
            {'type': 'status', 'snapshot': self.viewport_manager.create_snapshot(
                w, 10,
                lambda *args: self.renderServiceStatus(departure, *args),
                10
            )}
        ]
        
        if self.config["tfl"]["showPlatform"]:
            components.append({
                'type': 'platform',
                'snapshot': self.viewport_manager.create_snapshot(
                    pw, 10,
                    lambda *args: self.renderPlatform(departure, *args),
                    self.config["refreshTime"]
                )
            })
            
        return components

    def drawStartup(self, device, width, height):
        # Create viewport and image
        virtualViewport = self.viewport_manager.create_viewport(device, width, height)
        image = self.viewport_manager.create_blank_image(width, height)

        # Create rows
        rows = {
            'startup': {'y': 0, 'components': []},
            'powered': {'y': 24, 'components': []},
            'attribution': {'y': 36, 'components': []}
        }

        # Calculate text sizes
        nameSize = int(self.fontBold.getlength("UK Train Departure Display"))
        poweredSize = int(self.fontBold.getlength("Powered by"))
        attributionSize = int(self.fontBold.getlength("Transport for London"))

        # Create snapshots
        rows['startup']['components'] = [{
            'type': 'full_width',
            'snapshot': self.viewport_manager.create_snapshot(width, 10, lambda *args: self.renderName((width - nameSize) / 2, *args), 10)
        }]
        rows['powered']['components'] = [{
            'type': 'full_width',
            'snapshot': self.viewport_manager.create_snapshot(width, 10, lambda *args: self.renderPoweredBy((width - poweredSize) / 2, *args), 10)
        }]
        rows['attribution']['components'] = [{
            'type': 'full_width',
            'snapshot': self.viewport_manager.create_snapshot(width, 10, lambda *args: self.renderAttribution((width - attributionSize) / 2, *args), 10)
        }]

        # Position hotspots
        self.viewport_manager.position_hotspots(virtualViewport, {}, rows)

        device.display(image)
        return virtualViewport

    def drawBlankSignage(self, device, width, height, departureStation):
        # Create viewport and image
        virtualViewport = self.viewport_manager.create_viewport(device, width, height)
        image = self.viewport_manager.create_blank_image(width, height)

        # Create rows
        rows = {
            'no_trains': {'y': 0, 'components': []},
            'time': {'y': 50, 'components': []}
        }

        # Calculate text position
        noTrains = "No trains from " + departureStation
        noTrainsWidth = int(self.font.getlength(noTrains))
        noTrainsX = (width - noTrainsWidth) / 2

        # Create snapshots
        rows['no_trains']['components'] = [{
            'type': 'full_width',
            'snapshot': self.viewport_manager.create_snapshot(width, 10, lambda *args: self.renderNoTrains(noTrains, noTrainsX, *args), 10)
        }]
        rows['time']['components'] = [{
            'type': 'full_width',
            'snapshot': self.viewport_manager.create_snapshot(width, 14, self.renderTime, 0.1)
        }]

        # Position hotspots
        self.viewport_manager.position_hotspots(virtualViewport, {}, rows)

        device.display(image)
        return virtualViewport

    def check_and_update_line_status(self):
        """Check if it's time to query line status and update if needed"""
        if hasattr(self, 'announcer'):
            self.status_manager.check_and_update_line_status(self.current_departures, self.announcer)
        else:
            self.status_manager.check_and_update_line_status(self.current_departures)

    def should_show_status(self):
        """Determine if we should show status instead of third departure"""
        return self.status_manager.should_show_status(self.current_departures, self.cachedBitmapText)

    def renderLineStatus(self, draw=None, width=None, height=None):
        """Render the current line status"""
        return self.status_manager.render_line_status(draw, width, height, self.cachedBitmapText)

    def renderName(self, xOffset, draw=None, width=None, height=None):
        """Render the display name"""
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

    def renderPoweredBy(self, xOffset, draw=None, width=None, height=None):
        """Render the powered by text"""
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

    def renderAttribution(self, xOffset, draw=None, width=None, height=None):
        """Render the attribution text"""
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

    def renderNoTrains(self, text, xOffset, draw=None, width=None, height=None):
        """Render the no trains message"""
        return self.row_renderer.render_no_trains(text, xOffset, draw, width, height, self.cachedBitmapText)

    def renderCallingAt(self, draw=None, width=None, height=None):
        return self.row_renderer.render_calling_at(draw, width, height, self.cachedBitmapText)

    def renderDestination(self, departure, font, pos, draw=None, width=None, height=None):
        return self.row_renderer.render_destination(departure, font, pos, draw, width, height, self.cachedBitmapText)

    def renderTimeToArrival(self, departure, draw=None, width=None, height=None):
        return self.row_renderer.render_time_to_arrival(departure, draw, width, height, self.cachedBitmapText)

    def renderServiceStatus(self, departure, draw=None, width=None, height=None):
        return self.row_renderer.render_service_status(departure, draw, width, height, self.cachedBitmapText)

    def renderPlatform(self, departure, draw=None, width=None, height=None):
        return self.row_renderer.render_platform(departure, draw, width, height, self.cachedBitmapText)

    def renderStations(self, stations, draw=None, width=None, height=None):
        return self.row_renderer.render_stations(stations, draw, width, height, self.cachedBitmapText)
