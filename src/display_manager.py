import tkinter as tk
from PIL import Image, ImageDraw, ImageTk
from luma.core.interface.serial import spi
from luma.oled.device import ssd1322

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
        # Get station name from config
        from config import loadConfig
        config = loadConfig()
        station_name = config['screen2' if is_secondary else 'screen1']['outOfHoursName']
        self.root.title(f"Screen {2 if is_secondary else 1} - {station_name}")
        
        # Add padding to window size
        padding = 20
        window_width = width + padding * 2
        window_height = height + padding * 2
        
        # Configure window size and position
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        y = (screen_height - window_height) // 2
        
        # Position primary window on the left, secondary on the right
        x = 50 if not is_secondary else screen_width - window_width - 50
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Create canvas with padding
        self.canvas = tk.Canvas(self.root, width=window_width, height=window_height)
        self.canvas.pack()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.running = True
        
        # Initialize PhotoImage with padding
        self.photo = ImageTk.PhotoImage(self.image)
        self.canvas.create_image(padding, padding, image=self.photo, anchor=tk.NW)
        self.root.update()
        print(f"MockDisplay initialized {'Secondary' if is_secondary else 'Primary'}")

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
        try:
            # Create new PhotoImage
            new_photo = ImageTk.PhotoImage(self.image)
            
            # Update canvas with new image (with padding)
            padding = 20
            self.canvas.delete("all")
            self.image_id = self.canvas.create_image(padding, padding, image=new_photo, anchor=tk.NW)
            
            # Keep reference and update
            self.photo = new_photo
            self.root.update()
        except Exception as e:
            print(f"Display update error: {e}")

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
