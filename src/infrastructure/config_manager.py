import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manager for handling configuration settings"""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize the config manager
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.load_config()
        
    def load_config(self) -> None:
        """Load configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            logger.info("Configuration loaded successfully")
        except FileNotFoundError:
            logger.error("Configuration file not found: %s", self.config_path)
            raise
        except json.JSONDecodeError as e:
            logger.error("Error parsing configuration: %s", str(e))
            raise
        except Exception as e:
            logger.error("Error loading configuration: %s", str(e))
            raise
            
    def save_config(self) -> None:
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info("Configuration saved successfully")
        except Exception as e:
            logger.error("Error saving configuration: %s", str(e))
            raise
            
    def get_config(self) -> Dict[str, Any]:
        """Get the complete configuration
        
        Returns:
            Complete configuration dictionary
        """
        return self.config
            
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)
        
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self.config[key] = value
        
    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple configuration values
        
        Args:
            updates: Dictionary of updates
        """
        self.config.update(updates)
        
    def delete(self, key: str) -> None:
        """Delete a configuration value
        
        Args:
            key: Configuration key
        """
        if key in self.config:
            del self.config[key]
            
    def clear(self) -> None:
        """Clear all configuration values"""
        self.config.clear()
        
    def has_key(self, key: str) -> bool:
        """Check if configuration has key
        
        Args:
            key: Configuration key
            
        Returns:
            True if key exists, False otherwise
        """
        return key in self.config
        
    def get_path(self) -> str:
        """Get configuration file path
        
        Returns:
            Configuration file path
        """
        return self.config_path
