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

def summarize_log(log_path):
    """
    Summarize a log file by counting unique message occurrences and removing variable data.
    
    Args:
        log_path (str): Path to the log file
        
    Returns:
        str: A summarized version of the log with message counts
        
    Example output:
        [INFO] Starting application (3 occurrences)
        [ERROR] Failed to connect to database (2 occurrences)
        [WARN] Cache miss for key 'xyz' (5 occurrences)
    """
    if not os.path.exists(log_path):
        return "Log file not found"
        
    message_counts = {}
    
    try:
        with open(log_path, 'r') as file:
            for line in file:
                # Skip empty lines
                if not line.strip():
                    continue
                    
                # Remove timestamp if it exists (assumes ISO format)
                parts = line.split(' ')
                if len(parts) > 1 and parts[0].count('-') == 2:
                    message = ' '.join(parts[1:])
                else:
                    message = line
                    
                # Normalize the message by removing variable data
                # Remove timestamps in brackets
                message = ' '.join([
                    part for part in message.split(' ')
                    if not (part.startswith('[20') and part.endswith(']'))
                ])
                
                # Remove specific dates/times
                message = ' '.join([
                    part for part in message.split(' ')
                    if not (
                        part.count(':') == 2 or  # Time HH:MM:SS
                        part.count('/') == 2 or  # Date DD/MM/YYYY
                        part.count('-') == 2     # Date YYYY-MM-DD
                    )
                ])
                
                # Remove IPs and numeric IDs
                message = ' '.join([
                    part for part in message.split(' ')
                    if not (
                        part.replace('.', '').isdigit() or  # IPs
                        part.isdigit()                      # Numeric IDs
                    )
                ])
                
                # Normalize whitespace
                message = ' '.join(message.split())
                
                # Count occurrences
                message_counts[message] = message_counts.get(message, 0) + 1
    
        # Generate summary
        summary = []
        for message, count in sorted(message_counts.items(), key=lambda x: (-x[1], x[0])):
            if count > 1:
                summary.append(f"{message.strip()} ({count} occurrences)")
            else:
                summary.append(message.strip())
                
        return '\n'.join(summary)
        
    except Exception as e:
        return f"Error processing log file: {str(e)}"
