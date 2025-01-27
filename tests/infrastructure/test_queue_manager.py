import pytest
from unittest.mock import Mock, patch
from src.infrastructure.queue_manager import QueueManager
from src.infrastructure.config_manager import ConfigManager

@pytest.fixture
def config_data():
    return {
        'queues': {
            'test_queue': {
                'max_size': 5,
                'timeout': 10.0
            },
            'another_queue': {
                'max_size': 3,
                'timeout': 5.0
            }
        }
    }

@pytest.fixture
def config_manager(config_data):
    mock_config = Mock(spec=ConfigManager)
    mock_config.get.return_value = config_data['queues']
    return mock_config

@pytest.fixture
def queue_manager(config_manager):
    return QueueManager(config_manager)

def test_init_queues(queue_manager):
    """Test queue initialization"""
    assert queue_manager.has_queue('test_queue')
    assert queue_manager.has_queue('another_queue')
    assert queue_manager.get_length('test_queue') == 0
    assert queue_manager.get_length('another_queue') == 0

def test_append_item(queue_manager):
    """Test appending items to queue"""
    queue_manager.append('test_queue', 'item1')
    queue_manager.append('test_queue', 'item2')
    assert queue_manager.get_length('test_queue') == 2
    assert queue_manager.peek('test_queue') == 'item1'

def test_prepend_item(queue_manager):
    """Test prepending items to queue"""
    queue_manager.append('test_queue', 'item1')
    queue_manager.prepend('test_queue', 'item2')
    assert queue_manager.get_length('test_queue') == 2
    assert queue_manager.peek('test_queue') == 'item2'

def test_pop_item(queue_manager):
    """Test popping items from queue"""
    queue_manager.append('test_queue', 'item1')
    queue_manager.append('test_queue', 'item2')
    assert queue_manager.pop('test_queue') == 'item1'
    assert queue_manager.get_length('test_queue') == 1
    assert queue_manager.peek('test_queue') == 'item2'

def test_clear_queue(queue_manager):
    """Test clearing a queue"""
    queue_manager.append('test_queue', 'item1')
    queue_manager.append('test_queue', 'item2')
    queue_manager.clear('test_queue')
    assert queue_manager.get_length('test_queue') == 0

def test_clear_all_queues(queue_manager):
    """Test clearing all queues"""
    queue_manager.append('test_queue', 'item1')
    queue_manager.append('another_queue', 'item2')
    queue_manager.clear_all()
    assert queue_manager.get_length('test_queue') == 0
    assert queue_manager.get_length('another_queue') == 0

def test_get_all_lengths(queue_manager):
    """Test getting all queue lengths"""
    queue_manager.append('test_queue', 'item1')
    queue_manager.append('another_queue', 'item2')
    queue_manager.append('another_queue', 'item3')
    lengths = queue_manager.get_all_lengths()
    assert lengths['test_queue'] == 1
    assert lengths['another_queue'] == 2

def test_queue_max_size(queue_manager):
    """Test queue max size limit"""
    for i in range(10):  # More than max_size
        queue_manager.append('test_queue', f'item{i}')
    assert queue_manager.get_length('test_queue') == 5  # max_size from config

def test_nonexistent_queue(queue_manager):
    """Test operations on non-existent queue"""
    assert queue_manager.get_length('nonexistent') == 0
    assert queue_manager.peek('nonexistent') is None
    assert queue_manager.pop('nonexistent') is None
    # These should not raise errors
    queue_manager.append('nonexistent', 'item')
    queue_manager.prepend('nonexistent', 'item')
    queue_manager.clear('nonexistent')

def test_get_queue_names(queue_manager):
    """Test getting list of queue names"""
    names = queue_manager.get_queue_names()
    assert sorted(names) == sorted(['test_queue', 'another_queue'])

def test_has_queue(queue_manager):
    """Test checking queue existence"""
    assert queue_manager.has_queue('test_queue')
    assert queue_manager.has_queue('another_queue')
    assert not queue_manager.has_queue('nonexistent')
