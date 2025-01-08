"""
# .env.local
departureStation=PAD
apiKey=your_api_key
headless=False
dualScreen=True  # if you want to test both displays
"""

import os
import time
import tkinter as tk
from PIL import Image, ImageDraw, ImageTk

class MockDisplay:
    """Mock implementation of the SSD1322 display"""
    def __init__(self, width=256, height=64, mode="1", rotate=0):
        self.width = width
        self.height = height
        self.mode = mode
        self.rotate = rotate
        self.image = Image.new('RGB', (width, height), 'black')
        self.draw = ImageDraw.Draw(self.image)
        
        # Create tkinter window for display
        self.root = tk.Tk()
        self.root.title("Train Display Preview")
        self.canvas = tk.Canvas(self.root, width=width, height=height)
        self.canvas.pack()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.running = True

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
        # Convert PIL image to PhotoImage for tkinter
        photo = ImageTk.PhotoImage(self.image)
        self.canvas.create_image(0, 0, image=photo, anchor=tk.NW)
        self.canvas.photo = photo  # Keep a reference
        self.root.update()

class MockCanvas:
    """Mock implementation of Luma canvas context manager"""
    def __init__(self, device):
        self.device = device
        self.image = Image.new('RGB', (device.width, device.height), 'black')
        self.draw = ImageDraw.Draw(self.image)

    def __enter__(self):
        return self.draw

    def __exit__(self, exc_type, exc_val, exc_tb):
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
        with MockCanvas(self.device) as draw:
            for hotspot, (x, y) in self._hotspots:
                if hasattr(hotspot, 'compose'):
                    hotspot.compose(draw, x, y)
                else:
                    # Handle plain rendering functions
                    hotspot(draw)

def create_preview_display(config):
    """Create a mock display instead of hardware SSD1322"""
    return MockDisplay(
        width=256,
        height=64,
        mode="1",
        rotate=config['screenRotation']
    )

# Mock implementation of snapshot for testing
class MockSnapshot:
    def __init__(self, width, height, source, interval=1):
        self.width = width
        self.height = height
        self.source = source
        self.interval = interval
        self.last_updated = 0

    def compose(self, draw, x, y):
        if time.time() - self.last_updated >= self.interval:
            self.source(draw, self.width, self.height)
            self.last_updated = time.time()

# Example usage in main.py:
if __name__ == "__main__":
    config = loadConfig()
    
    # Use preview display instead of hardware
    device = create_preview_display(config)
    if config['dualScreen']:
        device1 = create_preview_display(config)
    
    # Replace hardware-specific imports
    canvas = MockCanvas
    viewport = MockViewport
    snapshot = MockSnapshot
    
    try:
        while device.running:  # Check if window is still open
            virtual = drawSignage(device, widgetWidth, widgetHeight, 
                               loadData(config["api"], config["journey"], config))
            virtual.refresh()
            
            if config['dualScreen'] and device1.running:
                virtual1 = drawSignage(device1, widgetWidth, widgetHeight,
                                    loadData(config["api"], config["journey"], config))
                virtual1.refresh()
            
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Preview closed")
