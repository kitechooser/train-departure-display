from typing import Dict, Any, Optional, List
import threading
import time
from src.infrastructure.event_bus import EventBus
from src.infrastructure.queue_manager import QueueManager
from src.infrastructure.config_manager import ConfigManager
from src.services.announcement_service import AnnouncementService
from src.services.display_service import DisplayService
from src.services.status_service import StatusService
from src.presentation.displays.tfl_display import TflDisplay
from src.presentation.displays.rail_display import RailDisplay
from src.api.tfl_client import TflClient
from src.api.rail_client import RailClient

class MainService:
    """Main service that coordinates between all other services"""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize the main service
        
        Args:
            config_path: Path to configuration file
        """
        # Initialize infrastructure
        self.config = ConfigManager(config_path)
        self.event_bus = EventBus()
        self.queue_manager = QueueManager(self.config)
        
        # Get migration config
        self.migration_config = self.config.get('migration', {})
        self.use_new_events = self.migration_config.get('use_event_system', False)
        
        # Initialize services
        self.announcement_service = AnnouncementService(self.event_bus, self.queue_manager)
        self.display_service = DisplayService(self.event_bus, self.queue_manager)
        self.status_service = StatusService(self.event_bus, self.queue_manager)
        
        # Initialize API clients
        tfl_config = self.config.get('tfl', {})
        self.tfl_client = TflClient(
            app_id=tfl_config.get('app_id'),
            app_key=tfl_config.get('app_key')
        )
        self.tfl_update_interval = tfl_config.get('update_interval', 60)
        
        rail_config = self.config.get('rail', {})
        self.rail_client = RailClient(
            api_key=rail_config.get('api_key')
        )
        self.rail_update_interval = rail_config.get('update_interval', 60)
        
        # Initialize update threads
        self._stop_threads = False
        self._tfl_thread = None
        self._rail_thread = None
        
        # Initialize displays
        self._init_displays()
        
        # Subscribe to events based on migration config
        if self.use_new_events:
            self.event_bus.subscribe('display_update', self.handle_event)  # New architecture
        else:
            self.event_bus.subscribe('service_update', self.handle_event)  # Old architecture
        self.event_bus.subscribe('service_error', self.handle_event)
        
    def _process_rail_updates(self) -> None:
        """Process one iteration of rail updates"""
        try:
            # Get screen configs
            screen1_config = self.config.get('screen1', {})
            screen2_config = self.config.get('screen2', {})
            
            # Get stations based on screen configurations
            rail_stations = []
            if screen1_config.get('type') == 'rail':
                rail_stations.append(screen1_config.get('station'))
            if screen2_config.get('type') == 'rail':
                rail_stations.append(screen2_config.get('station'))

            # Process screen1 if it's rail
            if screen1_config.get('type') == 'rail':
                station_code = screen1_config.get('station')
                departures = self.rail_client.get_departures(
                    station=station_code,
                    rows="10",
                    time_offset="0",
                    show_times=True
                )
                if departures:
                    event_type = 'display_update' if self.use_new_events else 'service_update'
                    event_data = {
                        'type': event_type,
                        'data': {
                            'display_id' if self.use_new_events else 'service_type': 'rail',
                            'content': {'departures': departures}
                        }
                    }
                    self.event_bus.emit(event_type, event_data)

            # Process screen2 if it's rail
            if screen2_config.get('type') == 'rail':
                station_code = screen2_config.get('station')
                departures = self.rail_client.get_departures(
                    station=station_code,
                    rows="10",
                    time_offset="0",
                    show_times=True
                )
                if departures:
                    event_type = 'display_update' if self.use_new_events else 'service_update'
                    event_data = {
                        'type': event_type,
                        'data': {
                            'display_id' if self.use_new_events else 'service_type': 'rail_secondary',
                            'content': {'departures': departures}
                        }
                    }
                    self.event_bus.emit(event_type, event_data)
                
        except Exception as e:
            self.event_bus.emit('service_error', {
                'type': 'error',
                'data': {
                    'service': 'rail',
                    'error': str(e)
                }
            })
        
    def handle_event(self, event: Dict[str, Any]) -> None:
        """Handle incoming events
        
        Args:
            event: Event data dictionary containing type and payload
        """
        if event['type'] == 'service_update':
            service_type = event['data'].get('service_type')
            content = event['data'].get('content')
            if service_type == 'tfl':
                # Update TfL display and status
                self.display_service.update_display('tfl', content)
                if 'status' in content:
                    self.status_service.update_status('tfl', content['status'])
                    # Announce significant status changes
                    if content['status'].get('severity', 0) > 1:
                        self.event_bus.emit('announcement_request', {
                            'text': content['status'].get('description', ''),
                            'priority': True
                        })
            elif service_type == 'rail':
                # Update rail display
                self.display_service.update_display('rail', content)
                # Announce significant changes
                if content.get('announcement'):
                    self.event_bus.emit('announcement_request', {
                        'text': content['announcement'],
                        'priority': False
                    })
        elif event['type'] == 'display_update':
            display_id = event['data'].get('display_id')
            content = event['data'].get('content')
            if display_id and content:
                # Update display
                self.display_service.update_display(display_id, content)
                
                # Handle TfL status updates
                if display_id == 'tfl' and 'status' in content:
                    self.status_service.update_status('tfl', content['status'])
                    # Announce significant status changes
                    if content['status'].get('severity', 0) > 1:
                        self.event_bus.emit('announcement_request', {
                            'text': content['status'].get('description', ''),
                            'priority': True
                        })
                
                # Handle Rail announcements
                elif display_id == 'rail' and content.get('announcement'):
                    self.event_bus.emit('announcement_request', {
                        'text': content['announcement'],
                        'priority': False
                    })
                    
        elif event['type'] == 'service_error':
            # Log error and potentially notify displays
            error = event['data'].get('error')
            service = event['data'].get('service')
            if error and service:
                self.display_service.update_display(service, {'error': error})

    def _init_displays(self) -> None:
        """Initialize and register displays"""
        # Get display config
        display_config = self.config.get('display', {})
        width = display_config.get('width', 256)
        height = display_config.get('height', 64)
        
        # Create displays based on config
        from src.display_manager import create_display
        
        # Create primary display based on screen1 config
        screen1_config = self.config.get('screen1', {})
        screen1_type = screen1_config.get('type')
        
        if screen1_type == 'rail':
            primary_display = RailDisplay(event_bus=self.event_bus, width=width, height=height, display_id='rail')
            primary_display.draw_error("Waiting for data...")
        else:  # tfl
            primary_display = TflDisplay(event_bus=self.event_bus, width=width, height=height, display_id='tfl')
            primary_display.draw_error("Waiting for data...")
        
        # Create display device for primary
        primary_device = create_display(display_config, width, height, is_secondary=False)
        primary_display.device = primary_device
        self.display_service.register_display(primary_display)
        primary_display.render()  # Force initial render
        
        # Create secondary display if enabled
        if display_config.get('dualDisplays', False):
            screen2_config = self.config.get('screen2', {})
            screen2_type = screen2_config.get('type')
            
            if screen2_type == 'rail':
                secondary_display = RailDisplay(event_bus=self.event_bus, width=width, height=height, display_id='rail_secondary')
                secondary_display.draw_error("Waiting for data...")
            else:  # tfl
                secondary_display = TflDisplay(event_bus=self.event_bus, width=width, height=height, display_id='tfl_secondary')
                secondary_display.draw_error("Waiting for data...")
            
            # Create display device for secondary
            secondary_device = create_display(display_config, width, height, is_secondary=True)
            secondary_display.device = secondary_device
            self.display_service.register_display(secondary_display)
            secondary_display.render()  # Force initial render
        

    def _rail_update_loop(self) -> None:
        """Rail update loop running in separate thread"""
        while not self._stop_threads:
            self._process_rail_updates()
            time.sleep(self.rail_update_interval)

    def _process_tfl_updates(self) -> None:
        """Process one iteration of TfL updates"""
        try:
            # Get screen configs
            screen1_config = self.config.get('screen1', {})
            screen2_config = self.config.get('screen2', {})
            
            # Get stations based on screen configurations
            stations = []
            if screen1_config.get('type') == 'tfl':
                stations.append({
                    'name': screen1_config.get('station'),
                    'platform': screen1_config.get('platform')
                })
            if screen2_config.get('type') == 'tfl':
                stations.append({
                    'name': screen2_config.get('station'),
                    'platform': screen2_config.get('platform')
                })
            
            # Get station data from TfL API
            stations = self.tfl_client.get_stations(stations)
            if stations:
                event_type = 'display_update' if self.use_new_events else 'service_update'
                event_data = {
                    'type': event_type,
                    'data': {
                        'display_id' if self.use_new_events else 'service_type': 'tfl',
                        'content': {'stations': stations}
                    }
                }
                self.event_bus.emit(event_type, event_data)
                
        except Exception as e:
            self.event_bus.emit('service_error', {
                'type': 'error',
                'data': {
                    'service': 'tfl',
                    'error': str(e)
                }
            })

    def _tfl_update_loop(self) -> None:
        """TfL update loop running in separate thread"""
        while not self._stop_threads:
            self._process_tfl_updates()
            time.sleep(self.tfl_update_interval)
    
    def start(self) -> None:
        """Start all services"""
        # Initial updates
        screen1_config = self.config.get('screen1', {})
        screen2_config = self.config.get('screen2', {})
        
        # Update primary display
        if screen1_config.get('type') == 'rail':
            self.display_service.update_display('rail', {'error': 'Waiting for data...'})
        else:
            self.display_service.update_display('tfl', {'error': 'Waiting for data...'})
            
        # Update secondary display if enabled
        if self.config.get('display', {}).get('dualDisplays', False):
            if screen2_config.get('type') == 'rail':
                self.display_service.update_display('rail_secondary', {'error': 'Waiting for data...'})
            else:
                self.display_service.update_display('tfl_secondary', {'error': 'Waiting for data...'})
        
        # Start update threads
        self._stop_threads = False
        
        self._tfl_thread = threading.Thread(target=self._tfl_update_loop)
        self._tfl_thread.daemon = True
        self._tfl_thread.start()
        
        self._rail_thread = threading.Thread(target=self._rail_update_loop)
        self._rail_thread.daemon = True
        self._rail_thread.start()
        
        # Start periodic announcement processing
        def process_announcements(event: Dict[str, Any]) -> None:
            self.announcement_service.process_queue()
        
        # Process announcements every 5 seconds
        self._process_announcements = process_announcements  # Store reference for cleanup
        self.event_bus.subscribe('timer_tick', self._process_announcements)
        
    def stop(self) -> None:
        """Stop all services and clean up"""
        # Stop update threads
        self._stop_threads = True
        if self._tfl_thread:
            self._tfl_thread.join(timeout=5.0)
        if self._rail_thread:
            self._rail_thread.join(timeout=5.0)
        
        # Cleanup services
        self.announcement_service.cleanup()
        self.display_service.cleanup()
        self.status_service.cleanup()
        
        # Cleanup event subscriptions
        if self.use_new_events:
            self.event_bus.unsubscribe('display_update', self.handle_event)
        else:
            self.event_bus.unsubscribe('service_update', self.handle_event)
        self.event_bus.unsubscribe('service_error', self.handle_event)
        if hasattr(self, '_process_announcements'):
            self.event_bus.unsubscribe('timer_tick', self._process_announcements)
