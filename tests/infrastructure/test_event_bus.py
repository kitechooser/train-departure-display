import pytest
import time
from src.infrastructure.event_bus import EventBus, EventType, Event

def test_event_bus_sync_mode():
    """Test event bus in synchronous mode"""
    events_received = []
    
    def handler(event: Event):
        events_received.append(event)
        
    bus = EventBus(async_mode=False)
    bus.subscribe(handler)
    
    bus.publish(EventType.DEPARTURE_UPDATED, {"test": "data"})
    
    assert len(events_received) == 1
    assert events_received[0].type == EventType.DEPARTURE_UPDATED
    assert events_received[0].data == {"test": "data"}

def test_event_bus_async_mode():
    """Test event bus in asynchronous mode"""
    events_received = []
    
    def handler(event: Event):
        events_received.append(event)
        
    with EventBus(async_mode=True) as bus:
        bus.subscribe(handler)
        bus.publish(EventType.STATUS_CHANGED, {"status": "test"})
        
        # Give time for async processing
        time.sleep(0.1)
        
        assert len(events_received) == 1
        assert events_received[0].type == EventType.STATUS_CHANGED
        assert events_received[0].data == {"status": "test"}

def test_event_filtering():
    """Test event type filtering"""
    departure_events = []
    status_events = []
    all_events = []
    
    def departure_handler(event: Event):
        departure_events.append(event)
        
    def status_handler(event: Event):
        status_events.append(event)
        
    def all_handler(event: Event):
        all_events.append(event)
        
    bus = EventBus(async_mode=False)
    bus.subscribe(departure_handler, EventType.DEPARTURE_UPDATED)
    bus.subscribe(status_handler, EventType.STATUS_CHANGED)
    bus.subscribe(all_handler)
    
    bus.publish(EventType.DEPARTURE_UPDATED, {"test": "departure"})
    bus.publish(EventType.STATUS_CHANGED, {"test": "status"})
    
    assert len(departure_events) == 1
    assert len(status_events) == 1
    assert len(all_events) == 2

def test_error_handling():
    """Test error handling in event processing"""
    error_events = []
    
    def error_handler(event: Event):
        error_events.append(event)
        
    def failing_handler(event: Event):
        raise ValueError("Test error")
        
    bus = EventBus(async_mode=False)
    # Register handlers in correct order - error handler first
    bus.subscribe(error_handler, EventType.ERROR_OCCURRED)
    bus.subscribe(failing_handler)
    
    bus.publish(EventType.DEPARTURE_UPDATED, {"test": "data"})
    
    # Verify error event was published
    assert len(error_events) == 1
    assert error_events[0].type == EventType.ERROR_OCCURRED
    assert "Test error" in str(error_events[0].data["error"])
    assert error_events[0].data["event_type"] == EventType.DEPARTURE_UPDATED
    assert error_events[0].data["data"] == {"test": "data"}

def test_event_ordering():
    """Test event processing order"""
    events_processed = []
    
    def handler(event: Event):
        events_processed.append(event.data["order"])
        
    bus = EventBus(async_mode=False)
    bus.subscribe(handler)
    
    bus.publish(EventType.DEPARTURE_UPDATED, {"order": 1})
    bus.publish(EventType.DEPARTURE_UPDATED, {"order": 2})
    bus.publish(EventType.DEPARTURE_UPDATED, {"order": 3})
    
    assert events_processed == [1, 2, 3]

def test_multiple_handlers():
    """Test multiple handlers for same event"""
    handler1_called = False
    handler2_called = False
    
    def handler1(event: Event):
        nonlocal handler1_called
        handler1_called = True
        
    def handler2(event: Event):
        nonlocal handler2_called
        handler2_called = True
        
    bus = EventBus(async_mode=False)
    bus.subscribe(handler1, EventType.DEPARTURE_UPDATED)
    bus.subscribe(handler2, EventType.DEPARTURE_UPDATED)
    
    bus.publish(EventType.DEPARTURE_UPDATED, {"test": "data"})
    
    assert handler1_called
    assert handler2_called

def test_context_manager():
    """Test event bus context manager"""
    events_received = []
    
    def handler(event: Event):
        events_received.append(event)
        
    with EventBus(async_mode=True) as bus:
        bus.subscribe(handler)
        bus.publish(EventType.DEPARTURE_UPDATED, {"test": "data"})
        time.sleep(0.1)  # Allow async processing
        
    # Verify event was processed
    assert len(events_received) == 1
    
    # Verify bus is stopped
    assert not bus._running
    assert not bus._thread or not bus._thread.is_alive()
