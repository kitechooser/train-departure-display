import pytest
import time
from unittest.mock import Mock, patch
from src.renderers.tfl_components.status_manager import StatusManager

@pytest.fixture
def config():
    return {
        "tfl": {
            "status": {
                "enabled": True,
                "queryInterval": 180,
                "announcementInterval": 360,
                "reshowInterval": 60,
                "alternatingRowInterval": 7
            }
        }
    }

@pytest.fixture
def font():
    mock_font = Mock()
    mock_font.getlength = lambda text: len(text) * 8  # Simulate text width
    return mock_font

@pytest.fixture
def cached_bitmap_text():
    def mock_bitmap_text(text, font):
        width = len(text) * 8
        height = 10
        bitmap = Mock()  # Mock bitmap object
        return width, height, bitmap
    return mock_bitmap_text

def test_init(config, font):
    """Test status manager initialization"""
    manager = StatusManager(config, font)
    assert manager.config == config
    assert manager.font == font
    assert manager.current_line_status is None
    assert manager.last_shown_status is None
    assert manager.last_shown_time == 0
    assert not manager.showing_status

def test_check_and_update_line_status(config, font):
    """Test status checking and updating"""
    manager = StatusManager(config, font)
    
    # Mock current departures
    departures = [{'line': 'Piccadilly'}]
    
    # Mock get_detailed_line_status
    with patch('src.renderers.tfl_components.status_manager.get_detailed_line_status') as mock_get_status:
        mock_get_status.return_value = "Test Status"
        
        # First check should update status
        manager.check_and_update_line_status(departures)
        assert manager.current_line_status == "Test Status"
        assert manager.last_shown_status is None
        
        # Second check within interval should not query again
        manager.check_and_update_line_status(departures)
        mock_get_status.assert_called_once()  # Should only be called once

def test_should_show_status_initial(config, font, cached_bitmap_text):
    """Test initial status display"""
    manager = StatusManager(config, font)
    manager.current_line_status = "Test Status"
    
    # Should show status when there are 3+ departures
    departures = [{'id': 1}, {'id': 2}, {'id': 3}]
    assert manager.should_show_status(departures, cached_bitmap_text)
    assert manager.showing_status
    
    # Should not show status with < 3 departures
    departures = [{'id': 1}, {'id': 2}]
    assert not manager.should_show_status(departures, cached_bitmap_text)

def test_status_reshow_interval(config, font, cached_bitmap_text):
    """Test status reshow functionality"""
    manager = StatusManager(config, font)
    manager.current_line_status = "Test Status"
    departures = [{'id': 1}, {'id': 2}, {'id': 3}]
    
    # Show status initially
    assert manager.should_show_status(departures, cached_bitmap_text)
    
    # Complete the display cycle
    manager.status_display_start = time.time() - 100  # Force display cycle to complete
    assert not manager.should_show_status(departures, cached_bitmap_text)
    
    # Status should be marked as shown
    assert manager.last_shown_status == "Test Status"
    assert manager.last_shown_time > 0
    
    # Advance time past reshow interval
    original_time = manager.last_shown_time
    manager.last_shown_time = time.time() - config["tfl"]["status"]["reshowInterval"] - 1
    
    # Should trigger reshow
    assert manager.should_show_status(departures, cached_bitmap_text)
    assert manager.last_shown_time == 0  # Should reset last shown time
    assert manager.last_shown_status is None  # Should reset last shown status

def test_status_change_forces_reshow(config, font, cached_bitmap_text):
    """Test status change triggers immediate reshow"""
    manager = StatusManager(config, font)
    manager.current_line_status = "Initial Status"
    departures = [{'id': 1}, {'id': 2}, {'id': 3}]
    
    # Show initial status
    assert manager.should_show_status(departures, cached_bitmap_text)
    manager.status_display_start = time.time() - 100  # Force display cycle to complete
    assert not manager.should_show_status(departures, cached_bitmap_text)
    
    # Change status
    with patch('src.renderers.tfl_components.status_manager.get_detailed_line_status') as mock_get_status:
        mock_get_status.return_value = "New Status"
        manager.check_and_update_line_status([{'line': 'Piccadilly'}])
        
    # Should trigger immediate reshow
    assert manager.should_show_status(departures, cached_bitmap_text)
    assert manager.last_shown_status is None
    assert manager.last_shown_time == 0

def test_render_line_status(config, font, cached_bitmap_text):
    """Test status rendering"""
    manager = StatusManager(config, font)
    manager.current_line_status = "Test Status"
    
    # Test render function creation
    render_func = manager.render_line_status(None, None, None, cached_bitmap_text)
    assert callable(render_func)
    
    # Test direct rendering
    mock_draw = Mock()
    manager.render_line_status(mock_draw, 100, 10, cached_bitmap_text)
    assert mock_draw.bitmap.called

def test_disabled_status(config, font, cached_bitmap_text):
    """Test behavior when status is disabled"""
    config["tfl"]["status"]["enabled"] = False
    manager = StatusManager(config, font)
    manager.current_line_status = "Test Status"
    
    departures = [{'id': 1}, {'id': 2}, {'id': 3}]
    assert not manager.should_show_status(departures, cached_bitmap_text)
    assert not manager.showing_status
