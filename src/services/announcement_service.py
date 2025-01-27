from typing import Dict, Any, Optional
from src.infrastructure.event_bus import EventBus
from src.infrastructure.queue_manager import QueueManager
from src.announcements.announcements_module import AnnouncementManager

class AnnouncementService:
    """Service for handling text-to-speech announcements"""
    
    def __init__(self, event_bus: EventBus, queue_manager: QueueManager):
        """Initialize the announcement service
        
        Args:
            event_bus: Event bus for handling events
            queue_manager: Queue manager for handling announcement queue
        """
        self.event_bus = event_bus
        self.queue_manager = queue_manager
        self.announcements = AnnouncementManager()
        self._is_speaking = False
        
        # Subscribe to events
        self.event_bus.subscribe('announcement_request', self.handle_event)
        self.event_bus.subscribe('announcement_cancel', self.handle_event)
        
    def handle_event(self, event: Dict[str, Any]) -> None:
        """Handle incoming events
        
        Args:
            event: Event data dictionary containing type and payload
        """
        if event['type'] == 'announcement_request':
            text = event['data'].get('text')
            priority = event['data'].get('priority', False)
            if text:
                self.queue_announcement(text, priority)
        elif event['type'] == 'announcement_cancel':
            self.cancel_announcements()
            
    def queue_announcement(self, text: str, priority: bool = False) -> None:
        """Queue an announcement to be spoken
        
        Args:
            text: Text to be spoken
            priority: If True, add to front of queue
        """
        announcement = {
            'text': text,
            'priority': priority
        }
        if priority:
            self.queue_manager.prepend('announcements', announcement)
        else:
            self.queue_manager.append('announcements', announcement)
            
    def process_queue(self) -> None:
        """Process the next announcement in the queue"""
        if self._is_speaking:
            return
            
        announcement = self.queue_manager.peek('announcements')
        if announcement:
            self._is_speaking = True
            try:
                # Create train data format expected by announce_next_train
                train_data = {
                    'is_tfl': False,  # Treat as National Rail announcement
                    'destination_name': announcement['text'],
                    'aimed_departure_time': 'Due',  # Required field
                    'expected_departure_time': 'Due',  # Required field
                    'platform': '',  # Optional field
                    'line': 'Announcement'  # Optional field
                }
                self.announcements.announce_next_train(train_data)
                self.queue_manager.pop('announcements')
                self.event_bus.emit('announcement_complete', {
                    'text': announcement['text']
                })
            except Exception as e:
                self.event_bus.emit('announcement_error', {
                    'text': announcement['text'],
                    'error': str(e)
                })
            finally:
                self._is_speaking = False
                
    def cancel_announcements(self) -> None:
        """Cancel all pending announcements"""
        self.queue_manager.clear('announcements')
        self.announcements.cleanup()
        self._is_speaking = False
        self.event_bus.emit('announcements_cleared')
        
    def cleanup(self) -> None:
        """Clean up resources and event subscriptions"""
        self.event_bus.unsubscribe('announcement_request', self.handle_event)
        self.event_bus.unsubscribe('announcement_cancel', self.handle_event)
        self.cancel_announcements()
