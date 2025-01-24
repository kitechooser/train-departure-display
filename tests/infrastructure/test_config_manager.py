import pytest
import os
import json
import tempfile
from src.infrastructure.config_manager import ConfigManager, MigrationConfig

@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing"""
    config = {
        "migration": {
            "phase1_enabled": True,
            "phase2_enabled": False,
            "use_new_tfl_client": True
        },
        "tfl": {
            "appId": "test_id",
            "appKey": "test_key"
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_path = f.name
        
    yield temp_path
    os.unlink(temp_path)

def test_load_config(temp_config_file):
    """Test loading configuration from file"""
    manager = ConfigManager(temp_config_file)
    
    assert manager.migration.phase1_enabled is True
    assert manager.migration.phase2_enabled is False
    assert manager.migration.use_new_tfl_client is True
    assert manager.get("tfl")["appId"] == "test_id"

def test_save_config(temp_config_file):
    """Test saving configuration changes"""
    manager = ConfigManager(temp_config_file)
    
    # Update some settings
    manager.update_migration(phase2_enabled=True)
    manager.set("tfl", {"appId": "new_id", "appKey": "new_key"})
    
    # Create new manager to load from file
    new_manager = ConfigManager(temp_config_file)
    
    assert new_manager.migration.phase2_enabled is True
    assert new_manager.get("tfl")["appId"] == "new_id"

def test_migration_config_defaults():
    """Test migration config default values"""
    config = MigrationConfig()
    
    assert config.phase1_enabled is False
    assert config.phase2_enabled is False
    assert config.phase3_enabled is False
    assert config.phase4_enabled is False
    assert config.use_new_api_client is False
    assert config.use_new_tfl_client is False
    assert config.use_new_rail_client is False
    assert config.use_event_system is False
    assert config.use_new_display is False

def test_update_migration_settings(temp_config_file):
    """Test updating migration settings"""
    manager = ConfigManager(temp_config_file)
    
    manager.update_migration(
        phase1_enabled=True,
        phase2_enabled=True,
        use_event_system=True
    )
    
    assert manager.migration.phase1_enabled is True
    assert manager.migration.phase2_enabled is True
    assert manager.migration.use_event_system is True

def test_invalid_migration_setting(temp_config_file):
    """Test handling invalid migration setting"""
    manager = ConfigManager(temp_config_file)
    
    # Should not raise exception but log warning
    manager.update_migration(invalid_setting=True)
    
    # Valid settings should still be updated
    manager.update_migration(phase1_enabled=True, invalid_setting=True)
    assert manager.migration.phase1_enabled is True

def test_config_backup(temp_config_file):
    """Test config backup creation"""
    manager = ConfigManager(temp_config_file)
    
    # Make some changes to trigger backup
    manager.update_migration(phase2_enabled=True)
    
    # Check backup file exists
    backup_path = f"{temp_config_file}.bak"
    assert os.path.exists(backup_path)
    
    # Check backup contains original content
    with open(backup_path, 'r') as f:
        backup_data = json.load(f)
        assert backup_data["migration"]["phase2_enabled"] is False

def test_context_manager(temp_config_file):
    """Test config manager context manager"""
    with ConfigManager(temp_config_file) as manager:
        manager.update_migration(phase2_enabled=True)
        
    # Check changes were saved
    new_manager = ConfigManager(temp_config_file)
    assert new_manager.migration.phase2_enabled is True

def test_get_default_value(temp_config_file):
    """Test getting non-existent config with default"""
    manager = ConfigManager(temp_config_file)
    
    value = manager.get("non_existent", "default")
    assert value == "default"

def test_missing_config_file():
    """Test handling of missing config file"""
    with pytest.raises(FileNotFoundError):
        ConfigManager("non_existent_file.json")

def test_invalid_json_config():
    """Test handling of invalid JSON config"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("invalid json")
        temp_path = f.name
        
    with pytest.raises(json.JSONDecodeError):
        ConfigManager(temp_path)
        
    os.unlink(temp_path)

def test_migration_config_immutable(temp_config_file):
    """Test migration config immutability"""
    manager = ConfigManager(temp_config_file)
    migration1 = manager.migration
    
    # Update settings through manager
    manager.update_migration(phase2_enabled=True)
    migration2 = manager.migration
    
    # Should be different objects
    assert migration1 is not migration2
    # Original object should be unchanged
    assert migration1.phase2_enabled is False
    # New object should have updated value
    assert migration2.phase2_enabled is True
    
    # Direct modification should not be possible
    with pytest.raises(AttributeError):
        migration2.phase2_enabled = False
