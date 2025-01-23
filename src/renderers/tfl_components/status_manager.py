import time
import logging
from src.tfl_status_detailed import get_detailed_line_status

logger = logging.getLogger(__name__)

class StatusManager:
    def __init__(self, config, font):
        self.config = config
        self.font = font
        # Status tracking
        self.last_status_query = 0
        self.last_status_announcement = 0
        self.current_line_status = None
        self.status_display_start = 0
        self.last_shown_status = None  # Track last shown status
        
        # Status animation states
        self.showing_status = False
        self.statusElevated = False
        self.statusPixelsUp = 0
        self.statusPixelsLeft = 0  # Start from left edge
        self.statusPauseCount = 0

    def check_and_update_line_status(self, current_departures, announcer=None):
        """Check if it's time to query line status and update if needed"""
        current_time = time.time()
        
        # Check if status updates are enabled
        if not self.config["tfl"]["status"]["enabled"]:
            return
            
        # Check if it's time to query status
        if current_time - self.last_status_query >= self.config["tfl"]["status"]["queryInterval"]:
            # Get the line name from the first departure's line if available
            line_name = None
            if current_departures:
                line_name = current_departures[0].get('line', '').lower()
            
            if line_name:
                new_status = get_detailed_line_status(line_name)
                logger.info(f"Checking status update - Current: {self.current_line_status}, New: {new_status}, Last shown: {self.last_shown_status}, Showing: {self.showing_status}")
                # Check if we have a new status that hasn't been shown yet
                if new_status != self.last_shown_status:
                    logger.info(f"Status check - New: {new_status}, Current: {self.current_line_status}, Last shown: {self.last_shown_status}, Showing: {self.showing_status}")
                    if not self.showing_status:
                        if new_status != self.current_line_status:
                            logger.info("New status detected, updating current status")
                            self.current_line_status = new_status
                        else:
                            logger.info("Status already set as current")
                    else:
                        logger.info("Status display in progress, deferring update")
                else:
                    logger.info(f"Status already shown - New: {new_status}, Last shown: {self.last_shown_status}")
                self.last_status_query = current_time
                
                # Only process announcements if they are enabled in config and we have a status
                if (announcer and self.config["announcements"]["enabled"] and 
                    self.config["announcements"]["announcement_types"]["line_status"] and
                    self.current_line_status):  # Only announce if we have a status
                    # Check if it's time to announce the status
                    if current_time - self.last_status_announcement >= self.config["tfl"]["status"]["announcementInterval"]:
                        announcer.announce_line_status(self.current_line_status)
                        self.last_status_announcement = current_time

    def calculate_scroll_duration(self, text_width):
        """Calculate how long it will take to scroll the text"""
        # Calculate frames needed for each animation phase:
        roll_up_frames = 10  # Roll up animation
        roll_up_pause = 20  # Pause after roll up
        scroll_frames = text_width // 2  # Scroll animation (faster scroll)
        end_pause = 8  # Final pause
        
        # Total frames needed for complete animation
        frames_needed = roll_up_frames + roll_up_pause + scroll_frames + end_pause
        
        # Convert frames to seconds (0.02s per frame)
        duration = frames_needed * 0.02
        
        # Add fixed buffer for long messages
        duration += 1  # Add 1 second buffer
        
        logger.info(f"Calculated scroll duration: {duration}s for text width {text_width} (frames: {frames_needed})")
        return duration

    def should_show_status(self, current_departures, cached_bitmap_text):
        """Determine if we should show status instead of third departure"""
        if not self.config["tfl"]["status"]["enabled"] or not self.current_line_status:
            self.showing_status = False
            return False
            
        # If we're not showing status, check if we should start
        if not self.showing_status and self.current_line_status != self.last_shown_status:  # Only show if status changed
            if len(current_departures) > 2:  # Only show status if we have a third departure to replace
                # Calculate text width and set display duration
                status_text = self.current_line_status.replace("\n", " ")
                text_width, _, _ = cached_bitmap_text(status_text, self.font)
                self.status_display_start = time.time()
                self.status_duration = self.calculate_scroll_duration(text_width)
                logger.info(f"Starting status display, duration: {self.status_duration}s")
                self.showing_status = True
                self.statusElevated = False
                self.statusPixelsUp = 0
                self.statusPixelsLeft = 0  # Start from left edge
                return True
        # If we are showing status, check if we should continue
        else:
            current_time = time.time()
            if current_time - self.status_display_start < self.status_duration:
                return True
            else:
                # Reset status display and animation states
                logger.info(f"Status display cycle complete - Current: {self.current_line_status}, Last shown: {self.last_shown_status}")
                self.showing_status = False
                self.statusPauseCount = 0
                self.statusPixelsLeft = 0  # Reset to left edge
                self.statusElevated = False
                self.statusPixelsUp = 0
                if self.current_line_status:  # Only update last shown if we have a status
                    logger.info(f"Marking status as shown and resetting - Current: {self.current_line_status}")
                    self.last_shown_status = self.current_line_status
                    self.current_line_status = None  # Reset current status to prevent re-showing
                    logger.info(f"Status state after reset - Current: {self.current_line_status}, Last shown: {self.last_shown_status}")
                logger.info("Returning to departure 3")
                return False
                
        return False

    def render_line_status(self, draw=None, width=None, height=None, cached_bitmap_text=None):
        """Render the current line status"""
        if draw is None:
            def drawText(draw, width=None, height=None, x=0, y=0):
                if self.current_line_status:
                    # Replace newlines with spaces
                    status_text = self.current_line_status.replace("\n", " ")
                    text_width, text_height, bitmap = cached_bitmap_text(status_text, self.font)
                    
                    # Always start with roll-up animation
                    if not self.statusElevated:
                        draw.bitmap((x, y + text_height - self.statusPixelsUp), bitmap, fill="yellow")
                        if self.statusPixelsUp == text_height:
                            self.statusPauseCount += 1
                            if self.statusPauseCount > 20:
                                self.statusElevated = True
                                self.statusPixelsUp = 0
                                self.statusPixelsLeft = 0  # Start from left edge
                        else:
                            self.statusPixelsUp = self.statusPixelsUp + 1
                    else:
                        # Horizontal scroll after elevation
                        draw.bitmap((x + self.statusPixelsLeft - 1, y), bitmap, fill="yellow")
                        if -self.statusPixelsLeft > text_width:  # If scrolled past end
                            if self.statusPauseCount < 8:  # Pause briefly at end
                                self.statusPauseCount += 1
                            else:
                                # End status display
                                logger.info(f"Status animation complete - Current: {self.current_line_status}, Last shown: {self.last_shown_status}")
                                self.showing_status = False
                                self.statusPauseCount = 0
                                self.statusPixelsLeft = 0
                                self.statusElevated = False
                                self.statusPixelsUp = 0
                                # Don't update last_shown_status here, it's handled in should_show_status
                        else:
                            self.statusPixelsLeft = self.statusPixelsLeft - 1  # Scroll slower
            return drawText
        else:
            if self.current_line_status:
                # Replace newlines with spaces
                status_text = self.current_line_status.replace("\n", " ")
                text_width, text_height, bitmap = cached_bitmap_text(status_text, self.font)
                
                # Always start with roll-up animation
                if not self.statusElevated:
                    draw.bitmap((0, text_height - self.statusPixelsUp), bitmap, fill="yellow")
                    if self.statusPixelsUp == text_height:
                        self.statusPauseCount += 1
                        if self.statusPauseCount > 20:
                            self.statusElevated = True
                            self.statusPixelsUp = 0
                            self.statusPixelsLeft = 0  # Start from left edge
                    else:
                        self.statusPixelsUp = self.statusPixelsUp + 1
                else:
                    # Horizontal scroll after elevation
                    draw.bitmap((self.statusPixelsLeft - 1, 0), bitmap, fill="yellow")
                    if -self.statusPixelsLeft > text_width:  # If scrolled past end
                        if self.statusPauseCount < 8:  # Pause briefly at end
                            self.statusPauseCount += 1
                        else:
                            # End status display
                            logger.info(f"Status animation complete - Current: {self.current_line_status}, Last shown: {self.last_shown_status}")
                            self.showing_status = False
                            self.statusPauseCount = 0
                            self.statusPixelsLeft = 0
                            self.statusElevated = False
                            self.statusPixelsUp = 0
                            # Don't update last_shown_status here, it's handled in should_show_status
                    else:
                        self.statusPixelsLeft = self.statusPixelsLeft - 1  # Scroll slower
