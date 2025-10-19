"""
Data synchronization engine for fetching data from Slide API and storing in SQLite.
Provides progress tracking for UI feedback.
"""
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from .slide_api import SlideAPIClient
from .database import Database

logger = logging.getLogger(__name__)


class SyncEngine:
    """Handles synchronization of data from Slide API to local database"""
    
    # Data sources that can be synced
    DATA_SOURCES = {
        'devices': 'Devices',
        'agents': 'Agents',
        'backups': 'Backups',
        'snapshots': 'Snapshots',
        'alerts': 'Alerts',
        'audits': 'Audit Logs',
        'clients': 'Clients',
        'users': 'Users',
        'networks': 'Networks',
        'virtual_machines': 'Virtual Machines',
        'file_restores': 'File Restores',
        'image_exports': 'Image Exports',
        'accounts': 'Accounts'
    }
    
    def __init__(self, api_client: SlideAPIClient, database: Database):
        """
        Initialize sync engine.
        
        Args:
            api_client: Slide API client instance
            database: Database instance
        """
        self.api_client = api_client
        self.database = database
        self.current_operation = None
        self.progress_data = {}
    
    def sync_all(self, data_sources: Optional[List[str]] = None,
                start_date: Optional[datetime] = None,
                progress_callback: Optional[Callable[[str, int, int, str], None]] = None) -> Dict[str, Any]:
        """
        Sync all or selected data sources.
        
        Args:
            data_sources: List of data source keys to sync (None = all)
            start_date: Optional start date for time-based filtering
            progress_callback: Callback function(resource, current, total, status)
            
        Returns:
            Dictionary with sync results
        """
        if data_sources is None:
            data_sources = list(self.DATA_SOURCES.keys())
        
        results = {
            'started_at': datetime.utcnow().isoformat(),
            'sources': {},
            'total_items': 0,
            'errors': []
        }
        
        for source in data_sources:
            if source not in self.DATA_SOURCES:
                results['errors'].append(f"Unknown data source: {source}")
                continue
            
            try:
                result = self._sync_source(source, start_date, progress_callback)
                results['sources'][source] = result
                results['total_items'] += result['items_synced']
            except Exception as e:
                error_msg = f"Error syncing {source}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                results['errors'].append(error_msg)
                results['sources'][source] = {
                    'status': 'error',
                    'error': str(e),
                    'items_synced': 0
                }
        
        results['completed_at'] = datetime.utcnow().isoformat()
        return results
    
    def _sync_source(self, source: str, start_date: Optional[datetime],
                    progress_callback: Optional[Callable]) -> Dict[str, Any]:
        """Sync a single data source"""
        self.current_operation = source
        
        def progress_wrapper(current: int, total: int):
            if progress_callback:
                progress_callback(source, current, total, 'syncing')
        
        # Update sync status to in-progress
        self.database.update_sync_status(source, 'syncing', 0)
        
        try:
            # Fetch data from API
            items = self._fetch_source_data(source, start_date, progress_wrapper)
            
            # Store in database
            self._store_source_data(source, items, progress_callback)
            
            # Update sync status to completed
            self.database.update_sync_status(source, 'completed', len(items))
            
            return {
                'status': 'completed',
                'items_synced': len(items),
                'synced_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.database.update_sync_status(source, 'error', 0, str(e))
            raise
    
    def _fetch_source_data(self, source: str, start_date: Optional[datetime],
                          progress_callback: Optional[Callable]) -> List[Dict]:
        """Fetch data from API for a specific source"""
        if source == 'devices':
            return self.api_client.get_devices(progress_callback=progress_callback)
        
        if source == 'agents':
            return self.api_client.get_agents(progress_callback=progress_callback)
        
        if source == 'backups':
            return self.api_client.get_backups(start_date=start_date, 
                                              progress_callback=progress_callback)
        
        if source == 'snapshots':
            return self.api_client.get_snapshots(include_deleted=True, 
                                                start_date=start_date,
                                                progress_callback=progress_callback)
        
        if source == 'alerts':
            return self.api_client.get_alerts(progress_callback=progress_callback)
        
        if source == 'audits':
            return self.api_client.get_audits(start_date=start_date,
                                             progress_callback=progress_callback)
        
        if source == 'clients':
            return self.api_client.get_clients(progress_callback=progress_callback)
        
        if source == 'users':
            return self.api_client.get_users(progress_callback=progress_callback)
        
        if source == 'networks':
            return self.api_client.get_networks(progress_callback=progress_callback)
        
        if source == 'virtual_machines':
            return self.api_client.get_virtual_machines(progress_callback=progress_callback)
        
        if source == 'file_restores':
            return self.api_client.get_file_restores(progress_callback=progress_callback)
        
        if source == 'image_exports':
            return self.api_client.get_image_exports(progress_callback=progress_callback)
        
        if source == 'accounts':
            return self.api_client.get_accounts(progress_callback=progress_callback)
        
        return []
    
    def _store_source_data(self, source: str, items: List[Dict],
                          progress_callback: Optional[Callable]):
        """Store fetched data in database"""
        if not items:
            return
        
        # Map source names to table names and primary keys
        table_map = {
            'devices': ('devices', 'device_id'),
            'agents': ('agents', 'agent_id'),
            'backups': ('backups', 'backup_id'),
            'snapshots': ('snapshots', 'snapshot_id'),
            'alerts': ('alerts', 'alert_id'),
            'audits': ('audits', 'audit_id'),
            'clients': ('clients', 'client_id'),
            'users': ('users', 'user_id'),
            'networks': ('networks', 'network_id'),
            'virtual_machines': ('virtual_machines', 'virt_id'),
            'file_restores': ('file_restores', 'file_restore_id'),
            'image_exports': ('image_exports', 'image_export_id'),
            'accounts': ('accounts', 'account_id')
        }
        
        table_name, primary_key = table_map[source]
        
        for i, item in enumerate(items):
            # Store raw JSON for reference
            data = dict(item)
            data['raw_json'] = item
            
            # Parse snapshot location data if this is a snapshot
            if source == 'snapshots':
                data = self._parse_snapshot_location_data(data)
            
            self.database.upsert_record(table_name, primary_key, data)
            
            # Update progress
            if progress_callback and (i + 1) % 10 == 0:
                progress_callback(source, i + 1, len(items), 'storing')
    
    def _parse_snapshot_location_data(self, snapshot_data: Dict) -> Dict:
        """
        Parse snapshot location fields from API response.
        
        Args:
            snapshot_data: Snapshot data from API
            
        Returns:
            Updated snapshot data with parsed location fields
        """
        # Parse locations array - each location is an object with 'type' field
        locations = snapshot_data.get('locations', [])
        snapshot_data['exists_local'] = 0
        snapshot_data['exists_cloud'] = 0
        
        if isinstance(locations, list):
            for location in locations:
                if isinstance(location, dict):
                    location_type = location.get('type', '')
                    if location_type == 'local':
                        snapshot_data['exists_local'] = 1
                    elif location_type == 'cloud':
                        snapshot_data['exists_cloud'] = 1
        
        # Parse deletions array for deletion types
        deletions = snapshot_data.get('deletions', [])
        snapshot_data['exists_deleted'] = 1 if deletions else 0
        snapshot_data['exists_deleted_retention'] = 0
        snapshot_data['exists_deleted_manual'] = 0
        snapshot_data['exists_deleted_other'] = 0
        
        if isinstance(deletions, list):
            for deletion in deletions:
                if isinstance(deletion, dict):
                    deletion_type = deletion.get('type', '')
                    if deletion_type == 'retention':
                        snapshot_data['exists_deleted_retention'] = 1
                    elif deletion_type == 'manual':
                        snapshot_data['exists_deleted_manual'] = 1
                    else:
                        snapshot_data['exists_deleted_other'] = 1
        
        return snapshot_data
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status for all sources"""
        status_list = self.database.get_sync_status()
        counts = self.database.get_data_source_counts()
        
        status_dict = {}
        for status in status_list:
            source = status['resource_type']
            status_dict[source] = {
                'name': self.DATA_SOURCES.get(source, source),
                'last_sync': status.get('last_sync_at'),
                'status': status.get('status', 'never'),
                'items_synced': status.get('items_synced', 0),
                'total_items': counts.get(source, 0),
                'error_message': status.get('error_message')
            }
        
        # Add sources that haven't been synced yet
        for source in self.DATA_SOURCES:
            if source not in status_dict:
                status_dict[source] = {
                    'name': self.DATA_SOURCES[source],
                    'last_sync': None,
                    'status': 'never',
                    'items_synced': 0,
                    'total_items': 0,
                    'error_message': None
                }
        
        return status_dict

