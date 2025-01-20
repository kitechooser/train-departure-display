import logging
from typing import Optional, Dict, Any
import json
import os
from dataclasses import dataclass
import time
import subprocess
import threading
from queue import Queue

@dataclass
class AnnouncementConfig:
    """Configuration for the announcements module"""
    enabled: bool = True
    volume: int = 100  # 0-100
    announcement_gap: float = 2.0  # seconds between announcements
    max_queue_size: int = 10
    log_level: str = "INFO"
    announcement_types: Dict[str, bool] = None
    
    def __post_init__(self):
        # Default announcement types if none provided
        if self.announcement_types is None:
            self.announcement_types = {
                "delays": True,
                "platform_changes": True,
                "cancellations": True,
                "on_time": False,
                "departures": False
            }
        
        # Validate volume
        if not 0 <= self.volume <= 100:
            raise ValueError("Volume must be between 0 and 100")

class AnnouncementManager:
    """Manages train announcements with configuration and error handling"""
    
    def __init__(self, config: Optional[AnnouncementConfig] = None):
        """Initialize the announcement manager with optional configuration"""
        self.config = config or AnnouncementConfig()
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        self.logger.setLevel(log_level)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # Initialize announcement queue and worker thread
        self.announcement_queue = Queue(maxsize=self.config.max_queue_size)
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.running = True
        self.worker_thread.start()
        
        self.logger.info("Announcement Manager initialized with config: %s", 
                        self.config.__dict__)
        
        # Check for required dependencies
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check if required system dependencies are installed"""
        try:
            subprocess.run(['mpg321', '--version'], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            self.logger.error("mpg321 not found. Please install it with: "
                            "sudo apt-get install mpg321")
            raise RuntimeError("Required dependency mpg321 not found")
    
    def _process_queue(self):
        """Process announcements from the queue"""
        while self.running:
            try:
                if not self.announcement_queue.empty():
                    announcement = self.announcement_queue.get()
                    self._play_announcement(announcement)
                    time.sleep(self.config.announcement_gap)
                else:
                    time.sleep(0.1)  # Prevent busy-waiting
            except Exception as e:
                self.logger.error("Error processing announcement queue: %s", str(e))
    
    def _play_announcement(self, announcement: Dict[str, Any]):
        """Play an announcement using the rail-announcements API"""
        try:
            # Here we'll add the actual rail-announcements API integration
            # For now, just log what would be announced
            self.logger.info("Playing announcement: %s", announcement)
            # TODO: Integrate with rail-announcements API
            pass
        except Exception as e:
            self.logger.error("Failed to play announcement: %s", str(e))
    
    def announce_delay(self, train_data: Dict[str, Any]):
        """Queue a delay announcement"""
        if not self.config.enabled or not self.config.announcement_types["delays"]:
            return
        
        try:
            announcement = {
                "type": "delay",
                "scheduled_time": train_data.get("aimed_departure_time"),
                "expected_time": train_data.get("expected_departure_time"),
                "destination": train_data.get("destination_name"),
                "platform": train_data.get("platform", ""),
                "timestamp": time.time()
            }
            
            if self.announcement_queue.full():
                self.logger.warning("Announcement queue full - dropping announcement")
                return
                
            self.announcement_queue.put(announcement)
            
        except Exception as e:
            self.logger.error("Error creating delay announcement: %s", str(e))
    
    def announce_platform_change(self, train_data: Dict[str, Any], 
                               new_platform: str):
        """Queue a platform change announcement"""
        if not self.config.enabled or \
           not self.config.announcement_types["platform_changes"]:
            return
            
        try:
            announcement = {
                "type": "platform_change",
                "scheduled_time": train_data.get("aimed_departure_time"),
                "destination": train_data.get("destination_name"),
                "old_platform": train_data.get("platform", ""),
                "new_platform": new_platform,
                "timestamp": time.time()
            }
            
            if self.announcement_queue.full():
                self.logger.warning("Announcement queue full - dropping announcement")
                return
                
            self.announcement_queue.put(announcement)
            
        except Exception as e:
            self.logger.error("Error creating platform change announcement: %s", 
                            str(e))
    
    def announce_cancellation(self, train_data: Dict[str, Any]):
        """Queue a cancellation announcement"""
        if not self.config.enabled or \
           not self.config.announcement_types["cancellations"]:
            return
            
        try:
            announcement = {
                "type": "cancellation",
                "scheduled_time": train_data.get("aimed_departure_time"),
                "destination": train_data.get("destination_name"),
                "platform": train_data.get("platform", ""),
                "timestamp": time.time()
            }
            
            if self.announcement_queue.full():
                self.logger.warning("Announcement queue full - dropping announcement")
                return
                
            self.announcement_queue.put(announcement)
            
        except Exception as e:
            self.logger.error("Error creating cancellation announcement: %s", str(e))
    
    def announce_departure(self, train_data: Dict[str, Any]):
        """Queue a departure announcement"""
        if not self.config.enabled or \
           not self.config.announcement_types["departures"]:
            return
            
        try:
            announcement = {
                "type": "departure",
                "scheduled_time": train_data.get("aimed_departure_time"),
                "destination": train_data.get("destination_name"),
                "platform": train_data.get("platform", ""),
                "timestamp": time.time()
            }
            
            if self.announcement_queue.full():
                self.logger.warning("Announcement queue full - dropping announcement")
                return
                
            self.announcement_queue.put(announcement)
            
        except Exception as e:
            self.logger.error("Error creating departure announcement: %s", str(e))
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5.0)
        self.logger.info("Announcement Manager cleaned up")

def test_announcement_manager():
    """Test function for the Announcement Manager"""
    # Create test configuration
    config = AnnouncementConfig(
        enabled=True,
        volume=80,
        announcement_gap=1.0,
        announcement_types={
            "delays": True,
            "platform_changes": True,
            "cancellations": True,
            "on_time": False,
            "departures": True
        }
    )
    
    # Create manager instance
    manager = AnnouncementManager(config)
    
    # Test data
    test_train = {
        "aimed_departure_time": "14:30",
        "expected_departure_time": "14:45",
        "destination_name": "London Paddington",
        "platform": "4"
    }
    
    try:
        # Test delay announcement
        manager.announce_delay(test_train)
        
        # Test platform change
        manager.announce_platform_change(test_train, "6")
        
        # Test cancellation
        manager.announce_cancellation(test_train)
        
        # Test departure
        manager.announce_departure(test_train)
        
        # Wait for announcements to process
        time.sleep(5)
        
    finally:
        # Clean up
        manager.cleanup()

if __name__ == "__main__":
    test_announcement_manager()
