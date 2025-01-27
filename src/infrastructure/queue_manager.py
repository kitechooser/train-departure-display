import logging
import time
from typing import Dict, Any, Optional, List
from collections import deque
from src.infrastructure.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class QueueManager:
    """Manager for handling message queues"""
    
    def __init__(self, config: ConfigManager):
        """Initialize the queue manager
        
        Args:
            config: Configuration manager
        """
        self.config = config
        self.queues: Dict[str, deque] = {}
        self.timeouts: Dict[str, Dict[str, float]] = {}
        self._init_queues()
        
    def _init_queues(self) -> None:
        """Initialize queues from configuration"""
        queue_config = self.config.get('queues', {})
        for queue_name, settings in queue_config.items():
            self.queues[queue_name] = deque(maxlen=settings.get('max_size', 100))
            self.timeouts[queue_name] = {
                'timeout': settings.get('timeout', 30.0),
                'last_update': time.time()
            }
            
    def append(self, queue_name: str, item: Any) -> None:
        """Append an item to a queue
        
        Args:
            queue_name: Name of queue
            item: Item to append
        """
        if queue_name not in self.queues:
            logger.warning("Queue %s does not exist", queue_name)
            return
            
        self.queues[queue_name].append(item)
        self.timeouts[queue_name]['last_update'] = time.time()
        logger.debug("Appended item to queue %s", queue_name)
        
    def prepend(self, queue_name: str, item: Any) -> None:
        """Prepend an item to a queue
        
        Args:
            queue_name: Name of queue
            item: Item to prepend
        """
        if queue_name not in self.queues:
            logger.warning("Queue %s does not exist", queue_name)
            return
            
        self.queues[queue_name].appendleft(item)
        self.timeouts[queue_name]['last_update'] = time.time()
        logger.debug("Prepended item to queue %s", queue_name)
        
    def peek(self, queue_name: str) -> Optional[Any]:
        """Peek at the next item in a queue
        
        Args:
            queue_name: Name of queue
            
        Returns:
            Next item or None if queue empty
        """
        if queue_name not in self.queues:
            logger.warning("Queue %s does not exist", queue_name)
            return None
            
        if not self.queues[queue_name]:
            return None
            
        return self.queues[queue_name][0]
        
    def pop(self, queue_name: str) -> Optional[Any]:
        """Pop the next item from a queue
        
        Args:
            queue_name: Name of queue
            
        Returns:
            Next item or None if queue empty
        """
        if queue_name not in self.queues:
            logger.warning("Queue %s does not exist", queue_name)
            return None
            
        if not self.queues[queue_name]:
            return None
            
        item = self.queues[queue_name].popleft()
        logger.debug("Popped item from queue %s", queue_name)
        return item
        
    def clear(self, queue_name: str) -> None:
        """Clear a queue
        
        Args:
            queue_name: Name of queue
        """
        if queue_name not in self.queues:
            logger.warning("Queue %s does not exist", queue_name)
            return
            
        self.queues[queue_name].clear()
        logger.debug("Cleared queue %s", queue_name)
        
    def clear_all(self) -> None:
        """Clear all queues"""
        for queue_name in self.queues:
            self.queues[queue_name].clear()
        logger.debug("Cleared all queues")
        
    def get_length(self, queue_name: str) -> int:
        """Get length of a queue
        
        Args:
            queue_name: Name of queue
            
        Returns:
            Queue length
        """
        if queue_name not in self.queues:
            logger.warning("Queue %s does not exist", queue_name)
            return 0
            
        return len(self.queues[queue_name])
        
    def get_all_lengths(self) -> Dict[str, int]:
        """Get lengths of all queues
        
        Returns:
            Dictionary of queue lengths
        """
        return {name: len(queue) for name, queue in self.queues.items()}
        
    def has_queue(self, queue_name: str) -> bool:
        """Check if queue exists
        
        Args:
            queue_name: Name of queue
            
        Returns:
            True if queue exists, False otherwise
        """
        return queue_name in self.queues
        
    def get_queue_names(self) -> List[str]:
        """Get list of queue names
        
        Returns:
            List of queue names
        """
        return list(self.queues.keys())
