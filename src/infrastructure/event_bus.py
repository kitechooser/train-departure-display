from typing import Dict, List, Any, Callable, Optional
import logging
import queue
import threading
import time
from dataclasses import dataclass
from enum import Enum, auto

logger = logging.getLogger(__name__)

@dataclass
class Event:
    """Event data structure"""
    type: str
    data: Dict[str, Any]
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()
        if self.data is None:
            self.data = {}

class EventHandler:
    """Event handler wrapper"""
    def __init__(self, callback: Callable[[Dict[str, Any]], None], filter_type: Optional[str] = None):
        self.callback = callback
        self.filter_type = filter_type

    def can_handle(self, event_type: str) -> bool:
        """Check if handler can process this event type"""
        return self.filter_type is None or event_type == self.filter_type

    def handle(self, data: Dict[str, Any]) -> None:
        """Process the event"""
        try:
            self.callback(data)
        except Exception as e:
            logger.error(f"Error in event handler: {str(e)}", exc_info=True)
            raise  # Re-raise to let event bus handle it

class EventBus:
    """Central event bus for system-wide events"""
    
    def __init__(self, async_mode: bool = True):
        self.handlers: List[EventHandler] = []
        self.event_queue: queue.Queue = queue.Queue()
        self.async_mode = async_mode
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        if async_mode:
            self.start()

    def subscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe to events"""
        handler = EventHandler(callback, event_type)
        self.handlers.append(handler)
        logger.debug(f"Added handler for {event_type if event_type else 'all events'}")

    def unsubscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Unsubscribe from events"""
        self.handlers = [h for h in self.handlers if not (h.callback == callback and h.filter_type == event_type)]
        logger.debug(f"Removed handler for {event_type}")

    def emit(self, event_type: str, data: Dict[str, Any] = None) -> None:
        """Publish an event"""
        event = Event(event_type, data)
        
        if self.async_mode:
            self.event_queue.put(event)
            logger.debug(f"Queued event {event_type}")
        else:
            self._process_event(event)

    def _process_event(self, event: Event) -> None:
        """Process a single event"""
        logger.debug(f"Processing event {event.type}")
        
        # Process error handlers first if this is an error event
        if event.type == 'error':
            for handler in self.handlers:
                if handler.filter_type == 'error':
                    try:
                        handler.handle(event.data)
                    except Exception as e:
                        logger.error(f"Error in error handler: {str(e)}", exc_info=True)
            return
            
        # Process regular handlers
        for handler in self.handlers:
            if handler.can_handle(event.type):
                try:
                    handler.handle(event.data)
                except Exception as e:
                    logger.error(f"Error processing event {event.type}: {str(e)}", exc_info=True)
                    # Create and process error event
                    error_event = Event(
                        'error',
                        {
                            'error': str(e),
                            'event_type': event.type,
                            'data': event.data
                        }
                    )
                    self._process_event(error_event)

    def _process_queue(self) -> None:
        """Process events from the queue"""
        while self._running:
            try:
                event = self.event_queue.get(timeout=0.1)
                self._process_event(event)
                self.event_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in event processing loop: {str(e)}", exc_info=True)

    def start(self) -> None:
        """Start the event processing thread"""
        if self.async_mode and not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._process_queue, daemon=True)
            self._thread.start()
            logger.info("Event bus started in async mode")

    def stop(self) -> None:
        """Stop the event processing thread"""
        if self._running:
            self._running = False
            if self._thread:
                self._thread.join(timeout=1.0)
            logger.info("Event bus stopped")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
