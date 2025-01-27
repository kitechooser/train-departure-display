from typing import Dict, Any, Optional, List
from src.infrastructure.event_bus import EventBus
from src.infrastructure.queue_manager import QueueManager
from src.infrastructure.config_manager import ConfigManager
from src.domain.processors.tfl_processor import TflProcessor
from src.api.tfl_client import TflClient

class StatusService:
    """Service for managing TfL line statuses"""
    
    def __init__(self, event_bus: EventBus, queue_manager: QueueManager):
        """Initialize the status service
        
        Args:
            event_bus: Event bus for handling events
            queue_manager: Queue manager for handling status queues
        """
        self.event_bus = event_bus
        self.queue_manager = queue_manager
        
        # Get TfL credentials from config
        config = queue_manager.config.get_config()
        tfl_config = config.get('tfl', {})
        app_id = tfl_config.get('app_id', '')
        app_key = tfl_config.get('app_key', '')
        
        # Initialize TfL client and processor
        self.tfl_client = TflClient(app_id, app_key)
        self.processor = TflProcessor(self.tfl_client, queue_manager.config)
        self.statuses: Dict[str, Any] = {}
        
        # Subscribe to events
        self.event_bus.subscribe('status_update', self.handle_event)
        self.event_bus.subscribe('status_request', self.handle_event)
        
    def handle_event(self, event: Dict[str, Any]) -> None:
        """Handle incoming events
        
        Args:
            event: Event data dictionary containing type and payload
        """
        if event['type'] == 'status_update':
            line = event['data'].get('line')
            status = event['data'].get('status')
            if line is not None and status is not None:
                self.update_status(line, status)
        elif event['type'] == 'status_request':
            line = event['data'].get('line')
            if line is not None:
                self.get_status(line)
                
    def update_status(self, line: str, status: Any) -> None:
        """Update a line's status
        
        Args:
            line: Line identifier
            status: Status data
        """
        processed_status = self.processor.process_status(status)
        self.statuses[line] = processed_status
        self.queue_manager.append('statuses', {
            'line': line,
            'status': processed_status
        })
        self.event_bus.emit('status_updated', {
            'line': line,
            'status': processed_status
        })
        
    def get_status(self, line: str) -> None:
        """Get a line's status and emit it
        
        Args:
            line: Line identifier
        """
        status = self.statuses.get(line)
        if status is not None:
            self.event_bus.emit('status_response', {
                'line': line,
                'status': status
            })
        else:
            self.event_bus.emit('status_not_found', {
                'line': line
            })
            
    def get_all_statuses(self) -> Dict[str, Any]:
        """Get all line statuses
        
        Returns:
            Dictionary of line statuses
        """
        return self.statuses.copy()
        
    def clear_status(self, line: str) -> None:
        """Clear a line's status
        
        Args:
            line: Line identifier
        """
        if line in self.statuses:
            del self.statuses[line]
            self.event_bus.emit('status_cleared', {
                'line': line
            })
            
    def clear_all_statuses(self) -> None:
        """Clear all line statuses"""
        self.statuses.clear()
        self.event_bus.emit('all_statuses_cleared')
        
    def cleanup(self) -> None:
        """Clean up resources and event subscriptions"""
        self.event_bus.unsubscribe('status_update', self.handle_event)
        self.event_bus.unsubscribe('status_request', self.handle_event)
        self.clear_all_statuses()
