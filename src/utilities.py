import os
import socket
from PIL import ImageFont

def get_version_number():
    """Get the version number from the VERSION file"""
    version_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..',
            'VERSION'
        )
    )
    version_file = open(version_path, 'r')
    return version_file.read()

def get_ip():
    """Get the IP address of the current machine"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def make_font(name, size):
    """Create a font object from a font file"""
    font_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            'fonts',
            name
        )
    )
    return ImageFont.truetype(font_path, size, layout_engine=ImageFont.Layout.BASIC)

def initialize_fonts():
    """Initialize and return all required fonts"""
    font = make_font("Dot Matrix Regular.ttf", 10)
    fontBold = make_font("Dot Matrix Bold.ttf", 10)
    fontBoldTall = make_font("Dot Matrix Bold Tall.ttf", 10)
    fontBoldLarge = make_font("Dot Matrix Bold.ttf", 20)
    return font, fontBold, fontBoldTall, fontBoldLarge
