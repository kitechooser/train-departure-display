import logging
from PIL import Image
from luma.core.virtual import viewport, snapshot

logger = logging.getLogger(__name__)

class ViewportManager:
    def __init__(self, config, font, fontBold):
        self.config = config
        self.font = font
        self.fontBold = fontBold
        self.hotspots = []

    def create_viewport(self, device, width, height):
        """Create a new viewport with the given dimensions"""
        return viewport(device, width=width, height=height)

    def create_snapshot(self, width, height, render_func, interval):
        """Create a snapshot with the given dimensions and render function"""
        return snapshot(width, height, render_func, interval=interval)

    def calculate_dimensions(self, status_text):
        """Calculate dimensions for viewport layout"""
        w = int(self.font.getlength(status_text))
        pw = int(self.font.getlength("Plat 88")) if self.config["tfl"]["showPlatform"] else 0
        tw = int(self.font.getlength("88 mins"))  # Width for time to arrival
        spacing = 5  # Add spacing between columns
        
        # Calculate total spacing based on visible columns
        total_spacing = spacing * (3 if self.config["tfl"]["showPlatform"] else 2)

        return {
            'status_width': w,
            'platform_width': pw,
            'time_width': tw,
            'spacing': spacing,
            'total_spacing': total_spacing
        }

    def clear_hotspots(self, viewport):
        """Clear all hotspots from the viewport"""
        if len(viewport._hotspots) > 0:
            for hotspot, xy in viewport._hotspots:
                viewport.remove_hotspot(hotspot, xy)

    def add_hotspot(self, viewport, snapshot, x, y):
        """Add a hotspot to the viewport"""
        viewport.add_hotspot(snapshot, (x, y))

    def create_blank_image(self, width, height):
        """Create a new blank image for drawing"""
        return Image.new('1', (width, height), 0)  # 0 = black in mode "1"

    def position_hotspots(self, viewport, dimensions, rows, platform_enabled=True):
        """Position all hotspots in the viewport"""
        self.clear_hotspots(viewport)
        
        width = viewport.width

        # Add hotspots for each row
        for row_name, row_data in rows.items():
            if row_data['components']:
                y = row_data['y']
                x_offset = 0  # Track x position for calling points row
                
                for component in row_data['components']:
                    if component['type'] == 'full_width':
                        self.add_hotspot(viewport, component['snapshot'], 0, y)
                    elif dimensions:  # Only use dimensions for departure rows
                        w = dimensions['status_width']
                        pw = dimensions['platform_width']
                        tw = dimensions['time_width']
                        spacing = dimensions['spacing']
                        
                        if component['type'] == 'destination':
                            if row_name == 'row_two':  # Calling points row
                                self.add_hotspot(viewport, component['snapshot'], x_offset, y)
                                x_offset += component['snapshot'].width  # Update x position for next component
                            else:
                                self.add_hotspot(viewport, component['snapshot'], 0, y)
                        elif component['type'] == 'time':
                            x = width - w - pw - tw - spacing * (2 if platform_enabled else 1)
                            self.add_hotspot(viewport, component['snapshot'], x, y)
                        elif component['type'] == 'status':
                            x = width - w - (pw + spacing if platform_enabled else 0)
                            self.add_hotspot(viewport, component['snapshot'], x, y)
                        elif component['type'] == 'platform' and platform_enabled:
                            self.add_hotspot(viewport, component['snapshot'], width - pw, y)
