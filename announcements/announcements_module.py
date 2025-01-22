import logging
from typing import Optional, Dict, Any
import time
import threading
from queue import Queue
import subprocess
import os

class AnnouncementConfig:
    """Configuration for the announcements module"""
    def __init__(self,
                enabled: bool = True,
                volume: int = 90,  # 0-100
                rate: int = 150,   # Words per minute
                voice: Optional[str] = None,
                announcement_gap: float = 2.0,  # seconds between announcements
                max_queue_size: int = 10,
                log_level: str = "INFO",
                announcement_types: Optional[Dict[str, bool]] = None,
                audio_config: Optional[Dict[str, str]] = None):
        
        self.enabled = enabled
        self.volume = volume
        self.rate = rate
        self.voice = voice
        self.announcement_gap = announcement_gap
        self.max_queue_size = max_queue_size
        self.log_level = log_level
        
        # Audio configuration
        self.audio_config = audio_config or {
            "driver": "auto",      # auto, nsss (macOS), espeak (Linux/Pi)
            "device": "default",   # audio device name/id
            "macos_voice": "",     # specific voice for macOS
            "espeak_voice": "english-us",  # specific voice for espeak
            "echo": {
                "enabled": True,       # Enable/disable echo effect
                "delay": 0.3,         # Delay between echoes in seconds
                "decay": 0.5,         # Volume reduction for each echo (0-1)
                "num_echoes": 3       # Number of echo repetitions
            }
        }
        
        # Default announcement types if none provided
        self.announcement_types = announcement_types or {
            "delays": True,
            "platform_changes": True,
            "cancellations": True,
            "on_time": False,
            "departures": False,
            "next_train": True,  # Announce next train to arrive
            "arriving": True     # Announce trains arriving at platform
        }
        
        # Validate volume
        if not 0 <= self.volume <= 100:
            raise ValueError("Volume must be between 0 and 100")

class AnnouncementManager:
    """Manages train announcements with text-to-speech"""
    
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
        
        # Lock for synchronizing announcements
        self.announcement_lock = threading.Lock()
        
        # Initialize announcement queue and worker thread
        self.announcement_queue = Queue(maxsize=self.config.max_queue_size)
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.running = True
        self.worker_thread.start()
        
        # Track last announcement times separately for each screen
        # Initialize to negative values to ensure first announcement triggers immediately
        self.last_next_train_screen1 = -60  # -60 seconds for National Rail
        self.last_next_train_screen2 = -30  # -30 seconds for TfL
        
        self.logger.info("Announcement Manager initialized with config: %s", 
                        vars(self.config))
    
    def _process_queue(self):
        """Process announcements from the queue"""
        while self.running:
            try:
                if not self.announcement_queue.empty():
                    announcement = self.announcement_queue.get()
                    self._speak_announcement(announcement)
                    time.sleep(self.config.announcement_gap)
                else:
                    time.sleep(0.1)  # Prevent busy-waiting
            except Exception as e:
                self.logger.error("Error processing announcement queue: %s", str(e))
    
    def _format_time(self, time_str: str) -> str:
        """Format time string for announcement"""
        if time_str == "Delayed":
            return "delayed"
            
        try:
            if ':' in time_str:
                hours, minutes = map(int, time_str.split(':'))
                
                # Convert hours to spoken format
                if hours == 0:
                    hours_spoken = "midnight"
                elif hours == 12:
                    hours_spoken = "twelve"
                else:
                    hours_map = {
                        1: "one", 2: "two", 3: "three", 4: "four",
                        5: "five", 6: "six", 7: "seven", 8: "eight",
                        9: "nine", 10: "ten", 11: "eleven",
                        13: "thirteen", 14: "fourteen", 15: "fifteen",
                        16: "sixteen", 17: "seventeen", 18: "eighteen",
                        19: "nineteen", 20: "twenty", 21: "twenty one",
                        22: "twenty two", 23: "twenty three"
                    }
                    hours_spoken = hours_map.get(hours, str(hours))
                
                # Format minutes
                if minutes == 0:
                    if hours == 0:
                        return "midnight"
                    else:
                        return f"{hours_spoken} hundred"
                elif minutes < 10:
                    return f"{hours_spoken} oh {minutes}"
                else:
                    return f"{hours_spoken} {minutes}"
            else:
                # For TfL announcements that use "X minutes" format
                return time_str
        except Exception as e:
            self.logger.error(f"Failed to format time {time_str}: {str(e)}")
            return time_str
    
    def _speak_announcement(self, announcement: Dict[str, Any]):
        """Speak an announcement using text-to-speech"""
        try:
            message = ""
            
            if announcement["type"] == "delay":
                message = (
                    f"Attention please. "
                    f"The {self._format_time(announcement['scheduled_time'])} service "
                    f"to {announcement['destination']} "
                )
                if announcement['expected_time'] == "Delayed":
                    message += "is delayed."
                else:
                    message += f"is delayed until {self._format_time(announcement['expected_time'])}."
                
            elif announcement["type"] == "platform_change":
                message = (
                    f"Attention please. "
                    f"The {self._format_time(announcement['scheduled_time'])} service "
                    f"to {announcement['destination']} "
                    f"has been moved from platform {announcement['old_platform']} "
                    f"to platform {announcement['new_platform']}."
                )
                
            elif announcement["type"] == "cancellation":
                message = (
                    f"Attention please. "
                    f"We regret to announce that the "
                    f"{self._format_time(announcement['scheduled_time'])} service "
                    f"to {announcement['destination']} has been cancelled."
                )
                
            elif announcement["type"] == "departure":
                message = (
                    f"The {self._format_time(announcement['scheduled_time'])} service "
                    f"to {announcement['destination']} "
                    f"from platform {announcement['platform']} "
                    f"is now departing."
                )
                
            elif announcement["type"] == "next_train":
                message = announcement["message"]
            
            if message:
                with self.announcement_lock:
                    try:
                        self.logger.debug("Starting speech subprocess")
                        script_path = os.path.join(os.path.dirname(__file__), 'speak.py')
                        cmd = [
                            'python3', script_path,
                            message,
                            '--rate', str(self.config.rate),
                            '--volume', str(self.config.volume / 100.0),
                            '--driver', self.config.audio_config["driver"],
                            '--device', self.config.audio_config["device"]
                        ]
                        
                        # Add voice parameter based on driver
                        if self.config.audio_config["driver"] == "nsss" and self.config.audio_config["macos_voice"]:
                            cmd.extend(['--voice', self.config.audio_config["macos_voice"]])
                        elif self.config.audio_config["driver"] == "espeak" and self.config.audio_config["espeak_voice"]:
                            cmd.extend(['--voice', self.config.audio_config["espeak_voice"]])
                        
                        self.logger.debug(f"Running speech command: {' '.join(cmd)}")
                        subprocess.run(cmd, check=True)
                        self.logger.info("Announced: %s", message)
                    except Exception as e:
                        self.logger.error("Error in speech subprocess: %s", str(e))
                        raise
            
        except Exception as e:
            self.logger.error("Failed to speak announcement: %s", str(e))
    
    def announce_delay(self, train_data: Dict[str, Any]):
        """Queue a delay announcement"""
        if not self.config.enabled:
            self.logger.debug("Announcements disabled, skipping delay announcement")
            return
        if not self.config.announcement_types["delays"]:
            self.logger.debug("Delay announcements disabled, skipping")
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
        if not self.config.enabled:
            self.logger.debug("Announcements disabled, skipping platform change announcement")
            return
        if not self.config.announcement_types["platform_changes"]:
            self.logger.debug("Platform change announcements disabled, skipping")
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
        if not self.config.enabled:
            self.logger.debug("Announcements disabled, skipping cancellation announcement")
            return
        if not self.config.announcement_types["cancellations"]:
            self.logger.debug("Cancellation announcements disabled, skipping")
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
        if not self.config.enabled:
            self.logger.debug("Announcements disabled, skipping departure announcement")
            return
        if not self.config.announcement_types["departures"]:
            self.logger.debug("Departure announcements disabled, skipping")
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
            
    def announce_next_train(self, train_data: Dict[str, Any]):
        """Queue a next train announcement"""
        if not self.config.enabled:
            self.logger.debug("Announcements disabled, skipping next train announcement")
            return
        if not self.config.announcement_types["next_train"]:
            self.logger.debug("Next train announcements disabled, skipping")
            return
            
        try:
            # Handle TfL services which use timeToStation
            if train_data.get("is_tfl"):
                self.logger.info("Processing TfL announcement")
                self.logger.debug(f"TfL train data: {train_data}")
                
                # Verify required fields
                if not train_data.get('destination_name'):
                    self.logger.error("Missing destination_name in TfL data")
                    return
                if not train_data.get('aimed_departure_time'):
                    self.logger.error("Missing aimed_departure_time in TfL data")
                    return
                
                # For TfL services, check if train is arriving (less than 30 seconds away)
                if train_data['aimed_departure_time'] == 'Due':
                    message = (
                        f"The train arriving at platform {train_data.get('platform', '')} "
                        f"is the {train_data.get('line', 'Underground')} line service "
                        f"to {train_data['destination_name']}"
                    )
                else:
                    message = (
                        f"The next {train_data.get('line', 'Underground')} line service "
                        f"to {train_data['destination_name']} "
                    )
                    if train_data.get("platform"):
                        message += f"from platform {train_data.get('platform')} "
                    message += f"will arrive in {train_data['aimed_departure_time']}"
                
                self.logger.info(f"Generated TfL announcement: {message}")
            else:
                # National Rail services
                platform_text = f" on platform {train_data['platform']}" if train_data.get("platform") else ""
                message = (
                    f"The next train{platform_text} is the "
                    f"{self._format_time(train_data['aimed_departure_time'])} service "
                    f"to {train_data['destination_name']}"
                )
                if train_data["expected_departure_time"] != "On time":
                    message += f", expected at {self._format_time(train_data['expected_departure_time'])}"
            
            announcement = {
                "type": "next_train",
                "message": message,
                "timestamp": time.time()
            }
            
            if self.announcement_queue.full():
                self.logger.warning("Announcement queue full - dropping announcement")
                return
                
            self.announcement_queue.put(announcement)
            
        except Exception as e:
            self.logger.error("Error creating next train announcement: %s", str(e))
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5.0)
        self.logger.info("Announcement Manager cleaned up")

def test_announcement_manager():
    """Test function for the Announcement Manager"""
    # Configure logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Create test configuration
    config = AnnouncementConfig(
        enabled=True,
        volume=90,
        rate=150,
        announcement_gap=3.0,
        log_level="DEBUG",  # Enable debug logging
        announcement_types={
            "delays": True,
            "platform_changes": True,
            "cancellations": True,
            "on_time": False,
            "departures": True,
            "next_train": True
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
        time.sleep(5)  # Increased delay between tests
        
        # Test platform change
        manager.announce_platform_change(test_train, "6")
        time.sleep(5)  # Increased delay between tests
        
        # Test cancellation
        manager.announce_cancellation(test_train)
        time.sleep(5)  # Increased delay between tests
        
        # Test departure
        manager.announce_departure(test_train)
        time.sleep(5)  # Increased delay between tests
        
        # Test next train
        manager.announce_next_train(test_train)
        time.sleep(5)  # Increased delay between tests
        
    finally:
        # Clean up
        manager.cleanup()

if __name__ == "__main__":
    test_announcement_manager()
