import pytest
import json
import os
from unittest.mock import mock_open, patch, call, Mock
from src.infrastructure.config_manager import ConfigManager

@pytest.fixture
def config_data():
    return {
        'test_key': 'test_value',
        'nested': {
            'key': 'value'
        }
    }

@pytest.fixture
def config_manager(config_data):
    with patch('builtins.open', mock_open(read_data=json.dumps(config_data))):
        return ConfigManager('test_config.json')

def test_init_and_load(config_data):
    """Test initialization and loading of config"""
    with patch('builtins.open', mock_open(read_data=json.dumps(config_data))):
        manager = ConfigManager('test_config.json')
        assert manager.config == config_data
        assert manager.get_path() == 'test_config.json'

def test_get_config(config_manager, config_data):
    """Test getting complete configuration"""
    assert config_manager.get_config() == config_data

def test_get_value(config_manager):
    """Test getting a configuration value"""
    assert config_manager.get('test_key') == 'test_value'
    assert config_manager.get('nested')['key'] == 'value'
    assert config_manager.get('non_existent', 'default') == 'default'

def test_set_value(config_manager):
    """Test setting a configuration value"""
    config_manager.set('new_key', 'new_value')
    assert config_manager.get('new_key') == 'new_value'

def test_update_values(config_manager):
    """Test updating multiple configuration values"""
    updates = {
        'key1': 'value1',
        'key2': 'value2'
    }
    config_manager.update(updates)
    assert config_manager.get('key1') == 'value1'
    assert config_manager.get('key2') == 'value2'

def test_delete_value(config_manager):
    """Test deleting a configuration value"""
    config_manager.delete('test_key')
    assert config_manager.get('test_key') is None

def test_clear_config(config_manager):
    """Test clearing all configuration values"""
    config_manager.clear()
    assert len(config_manager.get_config()) == 0

def test_has_key(config_manager):
    """Test checking if configuration has key"""
    assert config_manager.has_key('test_key') is True
    assert config_manager.has_key('non_existent') is False

def test_save_config(config_manager, config_data):
    """Test saving configuration to file"""
    m = mock_open()
    with patch('builtins.open', m):
        config_manager.save_config()
    
    # Get all write calls and join them into a single string
    write_calls = [args[0] for name, args, kwargs in m().mock_calls if name == 'write']
    written_data = ''.join(write_calls)
    
    # Parse the written data and compare
    saved_data = json.loads(written_data)
    assert saved_data == config_data

def test_load_config_file_not_found():
    """Test loading non-existent configuration file"""
    with pytest.raises(FileNotFoundError):
        with patch('builtins.open', mock_open()) as mock_file:
            mock_file.side_effect = FileNotFoundError()
            ConfigManager('non_existent.json')

def test_load_config_invalid_json():
    """Test loading invalid JSON configuration"""
    with pytest.raises(json.JSONDecodeError):
        with patch('builtins.open', mock_open(read_data='invalid json')):
            ConfigManager('test_config.json')

def test_save_config_error(config_manager):
    """Test error while saving configuration"""
    with pytest.raises(Exception):
        with patch('builtins.open', mock_open()) as mock_file:
            mock_file.side_effect = Exception('Save error')
            config_manager.save_config()
