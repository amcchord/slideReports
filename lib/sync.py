"""
Data synchronization engine for fetching data from Slide API and storing in SQLite.
Provides progress tracking for UI feedback.
"""
import json
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta, timezone
from .slide_api import SlideAPIClient, InvalidAPIKeyError, SlideRateLimitError
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
        'clients': 'Clients',
        'users': 'Users',
        'networks': 'Networks',
        'virtual_machines': 'Virtual Machines',
        'file_restores': 'File Restores',
        'image_exports': 'Image Exports',
        'accounts': 'Accounts',
        'audits': 'Audit Logs'
    }
    
    # How long before a "syncing" status is considered stale (in minutes)
    STALE_SYNC_THRESHOLD_MINUTES = 10
    HISTORY_OVERLAP = timedelta(days=1)
    HISTORY_RECONCILE_INTERVAL = timedelta(days=1)
    AUDIT_OVERLAP = timedelta(minutes=5)
    BACKGROUND_AUDIT_PAGES = 20
    
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
                progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
                incremental: bool = False) -> Dict[str, Any]:
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
            data_sources = list(self.DATA_SOURCES)
        else:
            data_sources = list(dict.fromkeys(data_sources))
        
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
                result = self._sync_source(source, start_date, progress_callback, incremental)
                results['sources'][source] = result
                results['total_items'] += result['items_synced']
            except (InvalidAPIKeyError, SlideRateLimitError):
                # Authentication rejection and throttling both end this run.
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
                    progress_callback: Optional[Callable], incremental: bool) -> Dict[str, Any]:
        """Sync a single data source"""
        self.current_operation = source
        
        def progress_wrapper(current: int, total: int):
            if progress_callback:
                progress_callback(source, current, total, 'syncing')
        
        history = None
        if source in ('backups', 'snapshots'):
            history = self._history_state(source, incremental, start_date)
        self.database.update_sync_status(source, 'syncing', 0)
        
        try:
            status = 'completed'
            if source == 'audits':
                count, more = self._sync_audits(start_date, progress_callback, incremental)
                if more:
                    status = 'partial'
            elif source in ('backups', 'snapshots'):
                count = self._sync_history(source, start_date, progress_wrapper,
                                           progress_callback, incremental, history)
            else:
                items = self._fetch_source_data(source, progress_wrapper)
                self._store_source_data(source, items, progress_callback)
                count = len(items)

            self.database.update_sync_status(source, status, count)
            return {
                'status': status,
                'items_synced': count,
                'synced_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.database.update_sync_status(source, 'error', 0, str(e))
            raise
    
    def _history_state(self, source, incremental, retention_start):
        stored = self.database.get_preference(f'sync_history:{source}')
        if stored:
            state = json.loads(stored)
            return self._parse_utc(state['last_success']), self._parse_utc(state['last_full'])
        if incremental:
            # Before checkpoints were added, a completed background refresh
            # always read the full reporting window. Reuse that work on upgrade.
            previous = next(iter(self.database.get_sync_status(source)), {})
            if previous.get('status') == 'completed':
                stamp = self._parse_utc(previous.get('last_sync_at'))
                if stamp and retention_start and stamp >= retention_start:
                    # Persist the migration before recording an in-progress
                    # status, so an interruption cannot erase this baseline.
                    self.database.set_preference(f'sync_history:{source}', json.dumps({
                        'last_success': stamp.isoformat(), 'last_full': stamp.isoformat(),
                    }))
                    return stamp, stamp
        return None, None

    def _sync_history(self, source, retention_start, progress_wrapper, progress_callback,
                      incremental, history):
        # Backups and snapshots can change after creation. Re-read a recent overlap
        # every time and reconcile the entire retained window periodically.
        now = datetime.utcnow()
        last_success, last_full = history
        reconcile = (
            not incremental or not last_success or not last_full
            or now - last_full >= self.HISTORY_RECONCILE_INTERVAL
        )
        start = retention_start
        if not reconcile:
            recent = last_success - self.HISTORY_OVERLAP
            start = max(start, recent) if start else recent

        fetch = self.api_client.get_backups if source == 'backups' else self.api_client.get_snapshots
        items = fetch(start_date=start, end_date=now, progress_callback=progress_wrapper)
        self._store_source_data(source, items, progress_callback)
        self.database.set_preference(f'sync_history:{source}', json.dumps({
            'last_success': now.isoformat(),
            'last_full': (now if reconcile else last_full).isoformat(),
        }))
        return len(items)

    def _sync_audits(self, retention_start, progress_callback, incremental):
        # Keep the query bounds fixed until its last page. Save each cursor
        # after its rows are committed so a retry can replay safely.
        preference = 'sync_audit_cursor'
        cursor = json.loads(self.database.get_preference(preference, '{}'))
        offset = cursor.get('next_offset')
        high = self._parse_utc(cursor.get('upper'))
        if offset is None:
            last = high or self._get_latest_audit_time()
            lower = last - self.AUDIT_OVERLAP if last else None
            if retention_start:
                lower = max(retention_start, lower) if lower else retention_start
            high = datetime.utcnow()
            offset = 0
        else:
            lower = self._parse_utc(cursor.get('lower'))

        count = 0
        pages = self.api_client.get_audit_pages(lower, high, offset)
        for page, (items, next_offset, total) in enumerate(pages, start=1):
            self._store_source_data('audits', items, None)
            count += len(items)
            self.database.set_preference(preference, json.dumps({
                'lower': lower.isoformat() if lower else None,
                'upper': high.isoformat(),
                'next_offset': next_offset,
            }))
            if progress_callback:
                progress_callback('audits', count, total or count, 'storing')
            if incremental and page >= self.BACKGROUND_AUDIT_PAGES and next_offset is not None:
                return count, True

        return count, False

    @staticmethod
    def _parse_utc(value):
        if value is None:
            return None
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if stamp.tzinfo is not None:
            stamp = stamp.astimezone(timezone.utc).replace(tzinfo=None)
        return stamp

    def _fetch_source_data(self, source: str, progress_callback: Optional[Callable]) -> List[Dict]:
        """Fetch data from API for a specific source"""
        if source == 'devices':
            return self.api_client.get_devices(progress_callback=progress_callback)

        if source == 'agents':
            return self.api_client.get_agents(progress_callback=progress_callback)

        if source == 'alerts':
            return self.api_client.get_alerts(progress_callback=progress_callback)

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
        
        batch = []
        for i, item in enumerate(items):
            # Store raw JSON for reference
            data = dict(item)
            data['raw_json'] = item
            
            # Parse snapshot location data if this is a snapshot
            if source == 'snapshots':
                data = self._parse_snapshot_location_data(data)
            
            batch.append(data)
            if len(batch) == 500 or i + 1 == len(items):
                self.database.upsert_records(table_name, primary_key, batch)
                batch = []
                if progress_callback:
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
                return self._parse_utc(result[0]['latest_time'])
            
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

