#!/usr/bin/env python3
import sys
import signal
import logging
import os
import glob
from datetime import datetime, timedelta
import json
from src.services.main_service import MainService

def setup_logging():
    """Configure logging with daily files and retention policy
    
    Returns:
        tuple: (logger, log_file_path)
    """
    # Load config
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    log_config = config.get('logging', {})
    logs_dir = log_config.get('directory', 'logs')
    retention_days = log_config.get('retention_days', 10)
    file_prefix = log_config.get('file_prefix', 'train_display')
    
    # Create logs directory if it doesn't exist
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Clean up old log files
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    for old_log_file in glob.glob(os.path.join(logs_dir, f"{file_prefix}_*.log")):
        try:
            # Extract date from filename (format: train_display_YYYYMMDD_HHMMSS.log)
            file_date_str = os.path.basename(old_log_file).split('_')[2]
            file_date = datetime.strptime(file_date_str, "%Y%m%d")
            if file_date < cutoff_date:
                os.remove(old_log_file)
        except (ValueError, IndexError):
            continue  # Skip files that don't match expected format
    
    # Generate log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = os.path.join(logs_dir, f"{file_prefix}_{timestamp}.log")
    
    # Configure handlers
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Configure root logger with debug level for development
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Set display manager logger to DEBUG specifically
    display_logger = logging.getLogger('src.display_manager')
    display_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Set display loggers to DEBUG for file only
    for logger_name in [
        'src.presentation.displays.base_display',
        'src.presentation.displays.rail_display',
        'src.presentation.displays.tfl_display'
    ]:
        display_logger = logging.getLogger(logger_name)
        display_logger.setLevel(logging.DEBUG)
        display_logger.propagate = False
        display_logger.addHandler(file_handler)
    
    return logging.getLogger(__name__), log_file_path

logger, log_file = setup_logging()
logger.info(f"Logging to file: {log_file}")

def signal_handler(signum, frame):
    """Handle system signals"""
    logger.info("Received signal %d, shutting down...", signum)
    if 'main_service' in globals() and main_service:
        main_service.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    main_service = None
    try:
        # Initialize main service
        main_service = MainService()
        
        # Start service
        logger.info("Starting train departure display...")
        main_service.start()
        
        # Import tkinter for root window
        import tkinter as tk
        
        class DisplayUpdater:
            def __init__(self, service):
                self.service = service
                self.last_timer_tick = datetime.now()
                self.timer_interval = timedelta(seconds=1)
                self.root = tk.Tk()
                self.root.withdraw()  # Hide the root window
                
            def update(self):
                """Update function called by tkinter"""
                # Update displays
                self.service.display_service.update_all()
                
                # Handle timer tick
                now = datetime.now()
                if now - self.last_timer_tick >= self.timer_interval:
                    self.service.event_bus.emit('timer_tick', {
                        'timestamp': now.timestamp()
                    })
                    self.last_timer_tick = now
                
                # Schedule next update
                self.root.after(100, self.update)
                
            def run(self):
                """Start the update loop"""
                self.root.after(100, self.update)
                self.root.mainloop()
        
        # Create and run display updater
        updater = DisplayUpdater(main_service)
        updater.run()
        
    except Exception as e:
        logger.error("Error running application: %s", str(e))
        if main_service:
            try:
                main_service.stop()
            except Exception as cleanup_error:
                logger.error("Error during cleanup: %s", str(cleanup_error))
        sys.exit(1)
