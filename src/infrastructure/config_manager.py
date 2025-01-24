from typing import Dict, Any, Optional
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class MigrationConfig:
    """Migration configuration settings"""
    phase1_enabled: bool = False
    phase2_enabled: bool = False
    phase3_enabled: bool = False
    phase4_enabled: bool = False
    use_new_api_client: bool = False
    use_new_tfl_client: bool = False
    use_new_rail_client: bool = False
    use_event_system: bool = False
    use_new_display: bool = False

class ConfigManager:
    """Manager for application configuration"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join(os.getcwd(), 'src', 'config.json')
        self._config: Dict[str, Any] = {}
        self._migration: MigrationConfig = MigrationConfig()
        self.load_config()
        
    def load_config(self) -> None:
        """Load configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                self._config = json.load(f)
                
            # Load migration settings
            migration_data = self._config.get('migration', {})
            self._migration = MigrationConfig(
                phase1_enabled=migration_data.get('phase1_enabled', False),
                phase2_enabled=migration_data.get('phase2_enabled', False),
                phase3_enabled=migration_data.get('phase3_enabled', False),
                phase4_enabled=migration_data.get('phase4_enabled', False),
                use_new_api_client=migration_data.get('use_new_api_client', False),
                use_new_tfl_client=migration_data.get('use_new_tfl_client', False),
                use_new_rail_client=migration_data.get('use_new_rail_client', False),
                use_event_system=migration_data.get('use_event_system', False),
                use_new_display=migration_data.get('use_new_display', False)
            )
            
            logger.info("Configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}", exc_info=True)
            raise
            
    def save_config(self) -> None:
        """Save configuration to file"""
        try:
            # Update migration settings
            self._config['migration'] = {
                'phase1_enabled': self._migration.phase1_enabled,
                'phase2_enabled': self._migration.phase2_enabled,
                'phase3_enabled': self._migration.phase3_enabled,
                'phase4_enabled': self._migration.phase4_enabled,
                'use_new_api_client': self._migration.use_new_api_client,
                'use_new_tfl_client': self._migration.use_new_tfl_client,
                'use_new_rail_client': self._migration.use_new_rail_client,
                'use_event_system': self._migration.use_event_system,
                'use_new_display': self._migration.use_new_display
            }
            
            # Create backup
            backup_path = f"{self.config_path}.bak"
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    with open(backup_path, 'w') as b:
                        b.write(f.read())
                        
            # Save new config
            with open(self.config_path, 'w') as f:
                json.dump(self._config, f, indent=2)
                
            logger.info("Configuration saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}", exc_info=True)
            raise
            
    @property
    def config(self) -> Dict[str, Any]:
        """Get the full configuration"""
        return self._config
        
    @property
    def migration(self) -> MigrationConfig:
        """Get migration settings"""
        return self._migration
        
    def update_migration(self, **kwargs) -> None:
        """Update migration settings"""
        new_settings = {
            'phase1_enabled': self._migration.phase1_enabled,
            'phase2_enabled': self._migration.phase2_enabled,
            'phase3_enabled': self._migration.phase3_enabled,
            'phase4_enabled': self._migration.phase4_enabled,
            'use_new_api_client': self._migration.use_new_api_client,
            'use_new_tfl_client': self._migration.use_new_tfl_client,
            'use_new_rail_client': self._migration.use_new_rail_client,
            'use_event_system': self._migration.use_event_system,
            'use_new_display': self._migration.use_new_display
        }
        
        for key, value in kwargs.items():
            if key in new_settings:
                new_settings[key] = value
            else:
                logger.warning(f"Unknown migration setting: {key}")
                
        self._migration = MigrationConfig(**new_settings)
        self.save_config()
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        return self._config.get(key, default)
        
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value"""
        self._config[key] = value
        self.save_config()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save_config()
