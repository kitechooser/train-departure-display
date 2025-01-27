import tkinter as tk
from PIL import Image, ImageDraw, ImageTk
from luma.core.interface.serial import spi
from luma.oled.device import ssd1322
import logging
import numpy as np

logger = logging.getLogger(__name__)

class MockDisplay:
    """Mock implementation of the SSD1322 display"""
    def __init__(self, width=256, height=64, mode="1", rotate=0, is_secondary=False):
        self.width = width
        self.height = height
        self.mode = mode
        self.rotate = rotate
        self.size = (width, height)  # Required by luma
        self.image = Image.new('1', self.size, 0)  # 0 = black in mode "1"
        self.draw = ImageDraw.Draw(self.image)
        
        # Create tkinter window for display
        self.root = tk.Toplevel() if is_secondary else tk.Tk()
        self.root.configure(bg='black')
        # Get station name from config
        from config import loadConfig
        config = loadConfig()
        station_name = config['screen2' if is_secondary else 'screen1']['outOfHoursName']
        self.root.title(f"Screen {2 if is_secondary else 1} - {station_name}")
        
        # Configure window size and position
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Set window size to exact display dimensions (no padding)
        self.root.geometry(f"{width}x{height}")
        
        # Position primary window on the left, secondary on the right
        x = 50 if not is_secondary else screen_width - width - 50
        y = (screen_height - height) // 2
        self.root.geometry(f"+{x}+{y}")
        
        # Create canvas with black background and no padding
        self.canvas = tk.Canvas(self.root, width=width, height=height, bg='black', highlightthickness=0)
        self.canvas.configure(bg='black')  # Ensure black background
        self.canvas.pack()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.running = True
        
        # Initialize PhotoImage
        self.photo = None
        self.canvas_image = None
        self.update_display()
        logger.info(f"MockDisplay initialized {'Secondary' if is_secondary else 'Primary'} ({width}x{height})")

    def on_closing(self):
        self.running = False
        if self.photo:
            self.photo = None
        if self.canvas_image:
            self.canvas.delete(self.canvas_image)
            self.canvas_image = None
        self.root.destroy()

    def clear(self):
        self.draw.rectangle([0, 0, self.width, self.height], fill=0)  # 0 = black
        self.update_display()

    def display(self, image):
        logger.debug(f"Received image mode: {image.mode}, size: {image.size}")
        # Keep image in mode '1' (binary) for monochrome display
        if image.mode != '1':
            logger.debug(f"Converting image from {image.mode} to mode '1'")
            self.image = image.convert('1')
        else:
            self.image = image
            
        # Debug log image content
        pixels = np.array(self.image)
        white_pixels = np.sum(pixels == 1)
        total_pixels = pixels.size
        logger.debug(f"Image size: {self.image.size}, White pixels: {white_pixels}/{total_pixels} ({white_pixels/total_pixels*100:.2f}%)")
        
        # Verify image has white pixels before updating display
        if white_pixels == 0:
            logger.warning("No white pixels found in image - text may not be visible")
            
        self.update_display()

    def update_display(self):
        try:
            if not self.running:
                return
                
            # Delete old image if it exists
            if self.canvas_image:
                self.canvas.delete(self.canvas_image)
                self.canvas_image = None
            if self.photo:
                self.photo = None
            
            # Create new PhotoImage
            self.photo = ImageTk.PhotoImage(self.image)
            
            # Create new canvas image
            self.canvas_image = self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
            
            # Update window
            try:
                if self.running:
                    self.root.update()
            except tk.TclError:
                # Window was closed
                self.running = False
                self.photo = None
                self.canvas_image = None
        except Exception as e:
            logger.error(f"Display update error: {e}")

def create_display(config, width, height, is_secondary=False):
    """Factory function to create either a mock or hardware display"""
    if config['previewMode']:
        return MockDisplay(width=width, height=height, is_secondary=is_secondary)
    else:
        # Hardware display initialization
        if not is_secondary:
            serial = spi(port=0, device=0, gpio_DC=24, gpio_RST=25, bus_speed_hz=8000000)
        else:
            serial = spi(port=1, device=0, gpio_DC=27, gpio_RST=31, bus_speed_hz=8000000)
        return ssd1322(serial, mode="1", rotate=config['screenRotation'])
