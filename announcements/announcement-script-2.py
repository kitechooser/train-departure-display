import logging
from typing import Optional, Dict, Any
import json
import os
from dataclasses import dataclass
import time
import subprocess
import threading
from queue import Queue
from pathlib import Path

@dataclass
class AnnouncementConfig:
    """Configuration for the announcements module"""
    enabled: bool = True
    volume: int = 90  # 0-100
    audio_device: str = "plughw:0,0"  # Default to first USB audio device
    announcement_gap: float = 2.0  # seconds between announcements
    max_queue_size: int = 10
    log_level: str = "INFO"
    audio_dir: str = "audio"  # Directory containing audio files
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
    
    # Define audio file mappings
    AUDIO_FILES = {
        "prefix": "prefix.wav",
        "delay": "delay.wav",
        "platform_change": "platform_change.wav",
        "cancellation": "cancellation.wav",
        "departure": "departure.wav",
        "suffix": "suffix.wav",
        # Add number files for time announcements
        **{str(i): f"numbers/{i}.wav" for i in range(10)},
        **{
            "10": "numbers/10.wav",
            "11": "numbers/11.wav",
            "12": "numbers/12.wav",
            "13": "numbers/13.wav",
            "14": "numbers/14.wav",
            "15": "numbers/15.wav",
            "16": "numbers/16.wav",
            "17": "numbers/17.wav",
            "18": "numbers/18.wav",
            "19": "numbers/19.wav",
            "20": "numbers/20.wav",
            "30": "numbers/30.wav",
            "40": "numbers/40.wav",
            "50": "numbers/50.wav",
            "oclock": "numbers/oclock.wav",
            "hours": "numbers/hours.wav",
            "minutes": "numbers/minutes.wav",
        }
    }
    
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
        
        # Ensure audio directory exists
        self.audio_dir = Path(self.config.audio_dir)
        if not self.audio_dir.exists():
            self.logger.warning(f"Creating audio directory: {self.audio_dir}")
            self.audio_dir.mkdir(parents=True)
        
        # Initialize announcement queue and worker thread
        self.announcement_queue = Queue(maxsize=self.config.max_queue_size)
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.running = True
        self.worker_thread.start()
        
        self.logger.info("Announcement Manager initialized with config: %s", 
                        self.config.__dict__)
        
        # Check for required dependencies and audio files
        self._check_dependencies()
        self._check_audio_files()
        
        # Set initial volume
        self._set_volume(self.config.volume)
    
    def _check_dependencies(self):
        """Check if required system dependencies are installed"""
        try:
            # Check if aplay is available (ALSA)
            subprocess.run(['aplay', '--version'], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
            
            # Check if we can access the audio device
            test_cmd = ["speaker-test", "-l", "1", "-D", self.config.audio_device, 
                       "-t", "sine", "-f", "1000"]
            subprocess.run(test_cmd, 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL,
                         timeout=1)  # Only test for 1 second
                         
        except FileNotFoundError:
            self.logger.error("ALSA tools not found. Please install with: "
                            "sudo apt-get install alsa-utils")
            raise RuntimeError("Required dependency alsa-utils not found")
        except subprocess.TimeoutExpired:
            # This is actually okay - means audio device was accessible
            pass
        except Exception as e:
            self.logger.error("Audio device test failed: %s", str(e))
            raise RuntimeError(f"Audio device {self.config.audio_device} not accessible")
    
    def _check_audio_files(self):
        """Check if required audio files exist"""
        missing_files = []
        for file_name in self.AUDIO_FILES.values():
            file_path = self.audio_dir / file_name
            if not file_path.exists():
                missing_files.append(file_name)
        
        if missing_files:
            self.logger.warning("Missing audio files: %s", missing_files)
            self.logger.warning("Please add the required audio files to %s",
                              self.audio_dir)
    
    def _set_volume(self, volume: int):
        """Set the PCM volume"""
        try:
            cmd = f"amixer sset 'PCM' {volume}%"
            subprocess.run(cmd.split(), 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
        except Exception as e:
            self.logger.error("Failed to set volume: %s", str(e))
    
    def _play_audio_file(self, file_name: str):
        """Play a single audio file"""
        try:
            file_path = self.audio_dir / file_name
            if not file_path.exists():
                self.logger.error(f"Audio file not found: {file_path}")
                return False
            
            cmd = ['aplay', '-D', self.config.audio_device, str(file_path)]
            subprocess.run(cmd, 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            self.logger.error(f"Failed to play audio file {file_name}: {str(e)}")
            return False
    
    def _play_number(self, number: int):
        """Play a number using individual digit files"""
        if number >= 0 and number <= 20:
            # Direct number files for 0-20
            self._play_audio_file(self.AUDIO_FILES[str(number)])
        elif number < 60:  # For times, we don't need numbers above 59
            tens = (number // 10) * 10
            ones = number % 10
            self._play_audio_file(self.AUDIO_FILES[str(tens)])
            if ones > 0:
                self._play_audio_file(self.AUDIO_FILES[str(ones)])
    
    def _play_time(self, time_str: str):
        """Play a time announcement (format: HH:MM)"""
        try:
            hours, minutes = map(int, time_str.split(':'))
            
            self._play_number(hours)
            if hours == 1:
                self._play_audio_file(self.AUDIO_FILES["hours"])
            else:
                self._play_audio_file(self.AUDIO_FILES["hours"])
            
            if minutes > 0:
                self._play_number(minutes)
                self._play_audio_file(self.AUDIO_FILES["minutes"])
            else:
                self._play_audio_file(self.AUDIO_FILES["oclock"])
                
        except Exception as e:
            self.logger.error(f"Failed to play time {time_str}: {str(e)}")
    
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
        """Play an announcement using the appropriate audio files"""
        try:
            # Ensure volume is set correctly
            self._set_volume(self.config.volume)
            
            # Play prefix sound
            self._play_audio_file(self.AUDIO_FILES["prefix"])
            
            # Play announcement based on type
            if announcement["type"] == "delay":
                self._play_audio_file(self.AUDIO_FILES["delay"])
                self._play_time(announcement["scheduled_time"])
                self._play_time(announcement["expected_time"])
                
            elif announcement["type"] == "platform_change":
                self._play_audio_file(self.AUDIO_FILES["platform_change"])
                self._play_time(announcement["scheduled_time"])
                
            elif announcement["type"] == "cancellation":
                self._play_audio_file(self.AUDIO_FILES["cancellation"])
                self._play_time(announcement["scheduled_time"])
                
            elif announcement["type"] == "departure":
                self._play_audio_file(self.AUDIO_FILES["departure"])
                self._play_time(announcement["scheduled_time"])
            
            # Play suffix sound
            self._play_audio_file(self.AUDIO_FILES["suffix"])
            
            self.logger.info("Played announcement: %s", announcement)
            
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
        volume=90,
        audio_device="plughw:0,0",
        announcement_gap=1.0,
        audio_dir="audio",  # Make sure this directory exists with required files
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
        
        #