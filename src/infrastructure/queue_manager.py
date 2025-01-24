from typing import Dict, Any, Optional, TypeVar, Generic, Callable
import queue
import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum, auto

logger = logging.getLogger(__name__)

class QueueType(Enum):
    """Types of queues in the system"""
    DEPARTURE = auto()
    ANNOUNCEMENT = auto()
    STATUS = auto()

T = TypeVar('T')

@dataclass
class QueueItem(Generic[T]):
    """Queue item with priority and timestamp"""
    data: T
    priority: int = 0
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()

    def __lt__(self, other):
        if not isinstance(other, QueueItem):
            return NotImplemented
        # Higher priority items come first
        if self.priority != other.priority:
            return self.priority > other.priority
        # Older items come first for same priority
        return self.timestamp < other.timestamp

class QueueManager:
    """Manager for system queues"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.queues: Dict[QueueType, queue.PriorityQueue] = {
            queue_type: queue.PriorityQueue() for queue_type in QueueType
        }
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._processors: Dict[QueueType, Callable[[Any], None]] = {}
        self._lock = threading.Lock()
        
    def register_processor(self, queue_type: QueueType, processor: Callable[[Any], None]) -> None:
        """Register a processor for a queue type"""
        with self._lock:
            self._processors[queue_type] = processor
            logger.info(f"Registered processor for {queue_type.name}")
        
    def add_item(self, queue_type: QueueType, item: Any, priority: int = 0) -> None:
        """Add an item to a queue"""
        if queue_type not in self.queues:
            raise ValueError(f"Unknown queue type: {queue_type}")
            
        queue_item = QueueItem(item, priority)
        self.queues[queue_type].put(queue_item)
        logger.debug(f"Added item to {queue_type.name} queue with priority {priority}")
        
    def get_item(self, queue_type: QueueType, timeout: Optional[float] = None) -> Optional[Any]:
        """Get an item from a queue"""
        if queue_type not in self.queues:
            raise ValueError(f"Unknown queue type: {queue_type}")
            
        try:
            item = self.queues[queue_type].get(timeout=timeout)
            return item.data
        except queue.Empty:
            return None
            
    def _process_queues(self) -> None:
        """Process all queues"""
        while self._running:
            with self._lock:
                processors = self._processors.copy()
                
            for queue_type, processor in processors.items():
                try:
                    item = self.get_item(queue_type, timeout=0.1)
                    if item is not None:
                        processor(item)
                        self.queues[queue_type].task_done()
                except Exception as e:
                    logger.error(f"Error processing {queue_type.name} queue: {str(e)}", exc_info=True)
                    
    def start(self) -> None:
        """Start queue processing"""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._process_queues, daemon=True)
            self._thread.start()
            logger.info("Queue manager started")
            
    def stop(self) -> None:
        """Stop queue processing"""
        if self._running:
            self._running = False
            if self._thread:
                self._thread.join(timeout=1.0)
            logger.info("Queue manager stopped")
            
    def __enter__(self):
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
