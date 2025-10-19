"""
Background scheduler for automatic data synchronization.
"""
import os
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from .background_sync import background_sync
from .database import Database, get_database_path
from .encryption import Encryption

logger = logging.getLogger(__name__)


class AutoSyncScheduler:
    """Manages automatic syncing for all API keys"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.data_dir = os.environ.get('DATA_DIR', '/var/www/reports.slide.recipes/data')
        self.started = False
    
    def start(self):
        """Start the scheduler"""
        if self.started:
            return
        
        # Schedule hourly sync check
        self.scheduler.add_job(
            func=self._check_and_sync_all,
            trigger=IntervalTrigger(hours=1),
            id='auto_sync_check',
            name='Check and sync all API keys',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.started = True
        logger.info("Auto-sync scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.started = False
            logger.info("Auto-sync scheduler stopped")
    
    def _check_and_sync_all(self):
        """Check all API keys and sync those with auto-sync enabled"""
        try:
            # Get all database files
            if not os.path.exists(self.data_dir):
                return
            
            db_files = [f for f in os.listdir(self.data_dir) if f.endswith('.db') and not f.endswith('_templates.db')]
            
            for db_file in db_files:
                api_key_hash = db_file.replace('.db', '')
                self._check_and_sync_key(api_key_hash)
        
        except Exception as e:
            logger.error(f"Error in auto-sync check: {e}")
    
    def _check_and_sync_key(self, api_key_hash: str):
        """Check if a specific API key should be synced"""
        try:
            db_path = get_database_path(api_key_hash)
            if not os.path.exists(db_path):
                return
            
            db = Database(db_path)
            
            # Check if auto-sync is enabled
            auto_sync_enabled = db.get_preference('auto_sync_enabled', 'true').lower() == 'true'
            
            if not auto_sync_enabled:
                logger.debug(f"Auto-sync disabled for {api_key_hash[:8]}")
                return
            
            # Check if sync is already in progress
            sync_state = background_sync.get_sync_state(api_key_hash)
            if sync_state.get('status') == 'syncing':
                logger.debug(f"Sync already in progress for {api_key_hash[:8]}")
                return
            
            # Check last sync time
            frequency_hours = int(db.get_preference('auto_sync_frequency_hours', '1'))
            last_sync = sync_state.get('completed_at')
            
            if last_sync:
                # Parse timestamp with UTC indicator (Z suffix)
                last_sync_dt = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
                # Convert to naive datetime for comparison with utcnow()
                last_sync_dt = last_sync_dt.replace(tzinfo=None)
                hours_since_sync = (datetime.utcnow() - last_sync_dt).total_seconds() / 3600
                
                if hours_since_sync < frequency_hours:
                    logger.debug(f"Sync not needed yet for {api_key_hash[:8]}")
                    return
            
            # Get the encrypted API key from the database
            encrypted_api_key = db.get_encrypted_api_key(api_key_hash)
            
            if not encrypted_api_key:
                logger.warning(f"No stored API key for {api_key_hash[:8]}, cannot auto-sync")
                return
            
            # Decrypt the API key
            from .encryption import Encryption
            encryption_key = os.environ.get('ENCRYPTION_KEY')
            if not encryption_key:
                logger.error("ENCRYPTION_KEY not set, cannot decrypt API key")
                return
            
            encryption = Encryption(encryption_key)
            try:
                api_key = encryption.decrypt(encrypted_api_key)
            except Exception as e:
                logger.error(f"Failed to decrypt API key for {api_key_hash[:8]}: {e}")
                return
            
            # Trigger the sync
            success = background_sync.start_sync(api_key, api_key_hash)
            if success:
                logger.info(f"Auto-sync triggered for {api_key_hash[:8]}")
            else:
                logger.warning(f"Auto-sync failed to start for {api_key_hash[:8]} (already in progress)")
            
        except Exception as e:
            logger.error(f"Error checking sync for {api_key_hash[:8]}: {e}")
    
    def trigger_sync_for_key(self, api_key: str, api_key_hash: str):
        """Manually trigger sync for a specific API key"""
        try:
            # Start sync in background
            success = background_sync.start_sync(api_key, api_key_hash)
            if success:
                logger.info(f"Manual sync triggered for {api_key_hash[:8]}")
            return success
        except Exception as e:
            logger.error(f"Error triggering sync: {e}")
            return False


# Global scheduler instance
auto_sync_scheduler = AutoSyncScheduler()


