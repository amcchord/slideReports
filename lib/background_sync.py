"""
Background sync manager for handling long-running sync operations.
Uses a simple file-based state tracking.
"""
import json
import os
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from .slide_api import SlideAPIClient
from .sync import SyncEngine
from .database import Database, get_database_path


class BackgroundSyncManager:
    """Manage background sync operations"""
    
    def __init__(self):
        self.base_dir = os.environ.get('DATA_DIR', '/var/www/reports.slide.recipes/data')
        os.makedirs(self.base_dir, exist_ok=True)
    
    def get_state_file(self, api_key_hash: str) -> str:
        """Get the state file path for a user"""
        return os.path.join(self.base_dir, f"{api_key_hash}_sync_state.json")
    
    def get_sync_state(self, api_key_hash: str) -> Dict[str, Any]:
        """Get current sync state"""
        state_file = self.get_state_file(api_key_hash)
        
        if not os.path.exists(state_file):
            return {
                'status': 'idle',
                'started_at': None,
                'current_source': None,
                'progress': {}
            }
        
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            
            # Check for stalled sync (syncing for more than 30 minutes with no updates)
            if state.get('status') == 'syncing':
                last_update = state.get('last_update') or state.get('started_at')
                if last_update:
                    try:
                        last_update_dt = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                        time_since_update = datetime.utcnow() - last_update_dt.replace(tzinfo=None)
                        
                        # If no update in 30 minutes, mark as stalled
                        if time_since_update.total_seconds() > 1800:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.warning(f"Sync stalled for {api_key_hash[:8]}, marking as error")
                            
                            state['status'] = 'error'
                            state['error'] = f'Sync stalled after {int(time_since_update.total_seconds() / 60)} minutes'
                            state['error_at'] = datetime.utcnow().isoformat() + 'Z'
                            
                            # Save the updated state
                            self.update_sync_state(api_key_hash, state)
                    except Exception as e:
                        pass
            
            return state
        except Exception:
            return {
                'status': 'idle',
                'started_at': None,
                'current_source': None,
                'progress': {}
            }
    
    def update_sync_state(self, api_key_hash: str, state: Dict[str, Any]):
        """Update sync state"""
        state_file = self.get_state_file(api_key_hash)
        
        try:
            with open(state_file, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            print(f"Failed to update sync state: {e}")
    
    def clear_sync_state(self, api_key_hash: str):
        """Clear sync state to reset to idle"""
        state_file = self.get_state_file(api_key_hash)
        
        try:
            if os.path.exists(state_file):
                os.remove(state_file)
        except Exception as e:
            print(f"Failed to clear sync state: {e}")
    
    def start_sync(self, api_key: str, api_key_hash: str, data_sources: Optional[list] = None):
        """Start a background sync operation"""
        # Check if already syncing
        state = self.get_sync_state(api_key_hash)
        if state.get('status') == 'syncing':
            return False
        
        # Update state to syncing
        self.update_sync_state(api_key_hash, {
            'status': 'syncing',
            'started_at': datetime.utcnow().isoformat() + 'Z',
            'current_source': None,
            'progress': {},
            'cutoff_days': 90
        })
        
        # Start sync in background thread
        thread = threading.Thread(
            target=self._run_sync,
            args=(api_key, api_key_hash, data_sources),
            daemon=True
        )
        thread.start()
        
        return True
    
    def _run_sync(self, api_key: str, api_key_hash: str, data_sources: Optional[list]):
        """Run the actual sync in background"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            db = Database(get_database_path(api_key_hash))
            client = SlideAPIClient(api_key)
            sync_engine = SyncEngine(client, db)
            
            # Calculate cutoff date (90 days ago)
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            
            def progress_callback(source: str, current: int, total: int, status: str):
                """Update progress state"""
                try:
                    state = self.get_sync_state(api_key_hash)
                    state['current_source'] = source
                    state['progress'][source] = {
                        'current': current,
                        'total': total,
                        'status': status
                    }
                    state['last_update'] = datetime.utcnow().isoformat() + 'Z'
                    self.update_sync_state(api_key_hash, state)
                except Exception as e:
                    logger.error(f"Error updating sync progress: {e}")
            
            logger.info(f"Starting sync for {api_key_hash[:8]}")
            
            # Pass cutoff date to sync_all
            results = sync_engine.sync_all(
                data_sources, 
                start_date=cutoff_date,
                progress_callback=progress_callback
            )
            
            logger.info(f"Sync completed successfully for {api_key_hash[:8]}")
            
            # Prune old snapshot records (older than 90 days)
            pruned_count = 0
            try:
                logger.info(f"Pruning snapshot records older than 90 days for {api_key_hash[:8]}")
                pruned_count = db.prune_old_snapshots(days=90)
                if pruned_count > 0:
                    logger.info(f"Pruned {pruned_count} old snapshot records for {api_key_hash[:8]}")
                else:
                    logger.info(f"No old snapshot records to prune for {api_key_hash[:8]}")
            except Exception as e:
                logger.error(f"Error pruning old snapshots for {api_key_hash[:8]}: {e}")
            
            # Update state to completed
            self.update_sync_state(api_key_hash, {
                'status': 'completed',
                'started_at': None,
                'current_source': None,
                'progress': {},
                'completed_at': datetime.utcnow().isoformat() + 'Z',
                'cutoff_date': cutoff_date.isoformat(),
                'results': results,
                'pruned_snapshots': pruned_count
            })
        except Exception as e:
            logger.error(f"Sync failed for {api_key_hash[:8]}: {e}", exc_info=True)
            
            # Update state to error
            try:
                self.update_sync_state(api_key_hash, {
                    'status': 'error',
                    'started_at': None,
                    'current_source': None,
                    'progress': {},
                    'error': str(e),
                    'error_at': datetime.utcnow().isoformat() + 'Z'
                })
            except Exception as state_error:
                logger.error(f"Failed to update error state: {state_error}")


# Global instance
background_sync = BackgroundSyncManager()

