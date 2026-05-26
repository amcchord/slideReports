"""
Data synchronization engine for fetching data from Slide API and storing in SQLite.
Provides progress tracking for UI feedback.
"""
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from .slide_api import SlideAPIClient, InvalidAPIKeyError
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
    
    # How long before a "syncing" status is considered stale (in minutes)
    STALE_SYNC_THRESHOLD_MINUTES = 10
    
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
    
    def recover_stale_syncs(self) -> List[str]:
        """
        Detect and recover from stale/interrupted sync operations.
        
        A sync is considered stale if it has been in 'syncing' status for longer
        than STALE_SYNC_THRESHOLD_MINUTES.
        
        Returns:
            List of resource types that were recovered
        """
        recovered = []
        threshold = datetime.utcnow() - timedelta(minutes=self.STALE_SYNC_THRESHOLD_MINUTES)
        
        try:
            # Get all sync statuses that are stuck in 'syncing'
            status_list = self.database.get_sync_status()
            
            for status in status_list:
                if status.get('status') == 'syncing':
                    resource_type = status.get('resource_type')
                    last_sync_at = status.get('last_sync_at')
                    
                    if last_sync_at:
                        try:
                            # Parse the timestamp
                            sync_time = datetime.fromisoformat(last_sync_at.replace('Z', '+00:00'))
                            # Remove timezone info for comparison if present
                            if sync_time.tzinfo is not None:
                                sync_time = sync_time.replace(tzinfo=None)
                            
                            # Check if it's stale
                            if sync_time < threshold:
                                logger.warning(
                                    f"Recovering stale sync for {resource_type}: "
                                    f"started at {last_sync_at}, threshold was {threshold.isoformat()}"
                                )
                                self.database.update_sync_status(
                                    resource_type, 
                                    'interrupted', 
                                    status.get('items_synced', 0),
                                    'Sync was interrupted (server restart or timeout)'
                                )
                                recovered.append(resource_type)
                        except (ValueError, TypeError) as e:
                            # If we can't parse the timestamp, consider it stale
                            logger.warning(f"Could not parse sync time for {resource_type}: {e}")
                            self.database.update_sync_status(
                                resource_type,
                                'interrupted',
                                0,
                                'Sync was interrupted (invalid timestamp)'
                            )
                            recovered.append(resource_type)
                    else:
                        # No timestamp but status is syncing - definitely stale
                        logger.warning(f"Recovering sync with no timestamp for {resource_type}")
                        self.database.update_sync_status(
                            resource_type,
                            'interrupted',
                            0,
                            'Sync was interrupted (no timestamp)'
                        )
                        recovered.append(resource_type)
            
            if recovered:
                logger.info(f"Recovered {len(recovered)} stale sync(s): {', '.join(recovered)}")
                
        except Exception as e:
            logger.error(f"Error during stale sync recovery: {e}", exc_info=True)
        
        return recovered
    
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
        # Recover any stale syncs before starting
        recovered = self.recover_stale_syncs()
        
        if data_sources is None:
            data_sources = list(self.DATA_SOURCES.keys())
        
        results = {
            'started_at': datetime.utcnow().isoformat(),
            'sources': {},
            'total_items': 0,
            'errors': [],
            'recovered_syncs': recovered
        }
        
        for source in data_sources:
            if source not in self.DATA_SOURCES:
                results['errors'].append(f"Unknown data source: {source}")
                continue
            
            try:
                result = self._sync_source(source, start_date, progress_callback)
                results['sources'][source] = result
                results['total_items'] += result['items_synced']
            except InvalidAPIKeyError:
                # API key is disabled/revoked. No point continuing to hit
                # other endpoints that will all 401 -- bubble up so the
                # caller can mark the key disabled and abort.
                raise
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
            # Audit logs are immutable, so only fetch new ones after the latest we have
            latest_audit_time = self._get_latest_audit_time()
            if latest_audit_time:
                # Use the latest audit time we have, adding 1 second to avoid re-fetching the same record
                audit_start_date = latest_audit_time + timedelta(seconds=1)
                logger.info(f"Skipping existing audit logs, fetching only after {audit_start_date.isoformat()}")
            else:
                # No existing audits, use the provided start_date
                audit_start_date = start_date
                
            return self.api_client.get_audits(start_date=audit_start_date,
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
    
    def _get_latest_audit_time(self) -> Optional[datetime]:
        """
        Get the timestamp of the most recent audit log in the database.
        Returns None if no audit logs exist yet.
        """
        try:
            result = self.database.execute_query("""
                SELECT MAX(audit_time) as latest_time
                FROM audits
            """)
            
            if result and result[0].get('latest_time'):
                time_str = result[0]['latest_time']
                # Parse the ISO format timestamp
                time_str = time_str.replace('Z', '+00:00')
                return datetime.fromisoformat(time_str)
            
            return None
        except Exception as e:
            logger.warning(f"Could not get latest audit time: {e}")
            return None
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status for all sources"""
        # Recover any stale syncs before returning status
        self.recover_stale_syncs()
        
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

