import pytest
import time
from src.infrastructure.event_bus import EventBus, Event

def test_event_bus_sync_mode():
    """Test event bus in synchronous mode"""
    events_received = []
    
    def handler(data):
        events_received.append(data)
        
    bus = EventBus(async_mode=False)
    bus.subscribe('departure_updated', handler)
    
    bus.emit('departure_updated', {"test": "data"})
    
    assert len(events_received) == 1
    assert events_received[0] == {"test": "data"}

def test_event_bus_async_mode():
    """Test event bus in asynchronous mode"""
    events_received = []
    
    def handler(data):
        events_received.append(data)
        
    with EventBus(async_mode=True) as bus:
        bus.subscribe('status_changed', handler)
        bus.emit('status_changed', {"status": "test"})
        
        # Give time for async processing
        time.sleep(0.1)
        
        assert len(events_received) == 1
        assert events_received[0] == {"status": "test"}

def test_event_filtering():
    """Test event type filtering"""
    departure_events = []
    status_events = []
    all_events = []
    
    def departure_handler(data):
        departure_events.append(data)
        
    def status_handler(data):
        status_events.append(data)
        
    def all_handler(data):
        all_events.append(data)
        
    bus = EventBus(async_mode=False)
    bus.subscribe('departure_updated', departure_handler)
    bus.subscribe('status_changed', status_handler)
    bus.subscribe(None, all_handler)  # None means subscribe to all events
    
    bus.emit('departure_updated', {"test": "departure"})
    bus.emit('status_changed', {"test": "status"})
    
    assert len(departure_events) == 1
    assert len(status_events) == 1
    assert len(all_events) == 2

def test_error_handling():
    """Test error handling in event processing"""
    error_events = []
    
    def error_handler(data):
        error_events.append(data)
        
    def failing_handler(data):
        raise ValueError("Test error")
        
    bus = EventBus(async_mode=False)
    # Register handlers in correct order - error handler first
    bus.subscribe('error', error_handler)
    bus.subscribe('departure_updated', failing_handler)
    
    bus.emit('departure_updated', {"test": "data"})
    
    # Verify error event was published
    assert len(error_events) == 1
    assert "Test error" in str(error_events[0]["error"])
    assert error_events[0]["event_type"] == 'departure_updated'
    assert error_events[0]["data"] == {"test": "data"}

def test_event_ordering():
    """Test event processing order"""
    events_processed = []
    
    def handler(data):
        events_processed.append(data["order"])
        
    bus = EventBus(async_mode=False)
    bus.subscribe('test_event', handler)
    
    bus.emit('test_event', {"order": 1})
    bus.emit('test_event', {"order": 2})
    bus.emit('test_event', {"order": 3})
    
    assert events_processed == [1, 2, 3]

def test_multiple_handlers():
    """Test multiple handlers for same event"""
    handler1_called = False
    handler2_called = False
    
    def handler1(data):
        nonlocal handler1_called
        handler1_called = True
        
    def handler2(data):
        nonlocal handler2_called
        handler2_called = True
        
    bus = EventBus(async_mode=False)
    bus.subscribe('test_event', handler1)
    bus.subscribe('test_event', handler2)
    
    bus.emit('test_event', {"test": "data"})
    
    assert handler1_called
    assert handler2_called

def test_context_manager():
    """Test event bus context manager"""
    events_received = []
    
    def handler(data):
        events_received.append(data)
        
    with EventBus(async_mode=True) as bus:
        bus.subscribe('test_event', handler)
        bus.emit('test_event', {"test": "data"})
        time.sleep(0.1)  # Allow async processing
        
    # Verify event was processed
    assert len(events_received) == 1
    
    # Verify bus is stopped
    assert not bus._running
    assert not bus._thread or not bus._thread.is_alive()
