import pytest
import time
from src.infrastructure.queue_manager import QueueManager, QueueType, QueueItem

@pytest.fixture
def config():
    return {
        "queue_settings": {
            "process_interval": 0.1
        }
    }

def test_queue_item_priority():
    """Test queue item priority ordering"""
    item1 = QueueItem("low", priority=1)
    item2 = QueueItem("high", priority=2)
    item3 = QueueItem("medium", priority=1, timestamp=time.time()+1)
    
    # Higher priority comes first
    assert item2 < item1
    # Same priority, earlier timestamp comes first
    assert item1 < item3

def test_queue_manager_basic(config):
    """Test basic queue manager functionality"""
    processed_items = []
    
    def processor(item):
        processed_items.append(item)
    
    with QueueManager(config) as manager:
        manager.register_processor(QueueType.DEPARTURE, processor)
        manager.add_item(QueueType.DEPARTURE, "test_item")
        
        # Allow time for processing
        time.sleep(0.2)
        
    assert processed_items == ["test_item"]

def test_queue_priority_processing(config):
    """Test priority-based processing"""
    processed_items = []
    
    def processor(item):
        processed_items.append(item)
    
    with QueueManager(config) as manager:
        manager.register_processor(QueueType.ANNOUNCEMENT, processor)
        
        # Add items with different priorities
        manager.add_item(QueueType.ANNOUNCEMENT, "low", priority=1)
        manager.add_item(QueueType.ANNOUNCEMENT, "high", priority=2)
        manager.add_item(QueueType.ANNOUNCEMENT, "medium", priority=1)
        
        # Allow time for processing
        time.sleep(0.3)
    
    # High priority should be processed first
    assert processed_items[0] == "high"
    # Other items should follow
    assert set(processed_items[1:]) == {"low", "medium"}

def test_multiple_queue_types(config):
    """Test handling multiple queue types"""
    departure_items = []
    announcement_items = []
    
    def departure_processor(item):
        departure_items.append(item)
        
    def announcement_processor(item):
        announcement_items.append(item)
    
    with QueueManager(config) as manager:
        manager.register_processor(QueueType.DEPARTURE, departure_processor)
        manager.register_processor(QueueType.ANNOUNCEMENT, announcement_processor)
        
        manager.add_item(QueueType.DEPARTURE, "departure1")
        manager.add_item(QueueType.ANNOUNCEMENT, "announcement1")
        
        # Allow time for processing
        time.sleep(0.2)
    
    assert departure_items == ["departure1"]
    assert announcement_items == ["announcement1"]

def test_error_handling(config):
    """Test error handling in queue processing"""
    processed_items = []
    
    def failing_processor(item):
        if item == "fail":
            raise ValueError("Test error")
        processed_items.append(item)
    
    with QueueManager(config) as manager:
        manager.register_processor(QueueType.STATUS, failing_processor)
        
        manager.add_item(QueueType.STATUS, "success")
        manager.add_item(QueueType.STATUS, "fail")
        manager.add_item(QueueType.STATUS, "after_fail")
        
        # Allow time for processing
        time.sleep(0.3)
    
    # Items after error should still be processed
    assert "success" in processed_items
    assert "after_fail" in processed_items

def test_queue_manager_shutdown(config):
    """Test clean shutdown of queue manager"""
    processed_items = []
    
    def slow_processor(item):
        time.sleep(0.1)
        processed_items.append(item)
    
    manager = QueueManager(config)
    manager.register_processor(QueueType.DEPARTURE, slow_processor)
    manager.start()
    
    # Add items
    manager.add_item(QueueType.DEPARTURE, "item1")
    manager.add_item(QueueType.DEPARTURE, "item2")
    
    # Stop immediately
    manager.stop()
    
    # Verify items were processed before shutdown
    assert len(processed_items) > 0

def test_invalid_queue_type(config):
    """Test handling of invalid queue types"""
    manager = QueueManager(config)
    
    with pytest.raises(ValueError):
        manager.add_item("invalid_type", "test")
        
    with pytest.raises(ValueError):
        manager.get_item("invalid_type")

def test_concurrent_processing(config):
    """Test concurrent processing of different queue types"""
    departure_items = []
    announcement_items = []
    status_items = []
    
    def departure_processor(item):
        time.sleep(0.1)  # Simulate slow processing
        departure_items.append(item)
        
    def announcement_processor(item):
        announcement_items.append(item)
        
    def status_processor(item):
        status_items.append(item)
    
    with QueueManager(config) as manager:
        manager.register_processor(QueueType.DEPARTURE, departure_processor)
        manager.register_processor(QueueType.ANNOUNCEMENT, announcement_processor)
        manager.register_processor(QueueType.STATUS, status_processor)
        
        # Add items to different queues
        manager.add_item(QueueType.DEPARTURE, "departure1")
        manager.add_item(QueueType.ANNOUNCEMENT, "announcement1")
        manager.add_item(QueueType.STATUS, "status1")
        
        # Allow time for processing
        time.sleep(0.3)
    
    # All queues should have processed their items
    assert len(departure_items) == 1
    assert len(announcement_items) == 1
    assert len(status_items) == 1
