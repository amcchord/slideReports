"""Schedule a bounded number of automatic syncs as accounts become due."""
import logging
import os
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .background_sync import background_sync
from .database import Database, get_database_path, list_account_database_hashes
from .encryption import Encryption
from .slide_api import SlideRateLimitError
from .sync import SyncEngine

logger = logging.getLogger(__name__)

AUTO_SYNC_FREQUENCIES = (1, 2, 4, 6, 12, 24)


def auto_sync_frequency(value):
    try:
        hours = int(value)
    except (ValueError, TypeError):
        return 1
    return hours if hours in AUTO_SYNC_FREQUENCIES else 1


def next_auto_sync_at(state, frequency_hours, preferences):
    last_attempt = SyncEngine._parse_utc(
        state.get('last_full_attempt_at') or state.get('completed_at')
        or state.get('error_at') or state.get('started_at')
    )
    due_at = (last_attempt + timedelta(hours=frequency_hours)
              if last_attempt else datetime.min)
    if preferences.get('api_key_status') == 'disabled':
        retry = SyncEngine._parse_utc(preferences.get('api_key_retry_at'))
        if not retry and last_attempt:
            retry = last_attempt + background_sync.DISABLED_KEY_RECHECK
        if retry:
            due_at = max(due_at, retry)
    if state.get('retry_at'):
        due_at = max(due_at, datetime.utcfromtimestamp(state['retry_at']))
    return due_at


class AutoSyncScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.data_dir = os.environ.get('DATA_DIR', '/var/www/reports.slide.recipes/data')
        self.started = False

    def start(self):
        if self.started:
            return
        self.scheduler.add_job(
            self._check_and_sync_all,
            trigger=IntervalTrigger(minutes=1),
            id='auto_sync_check',
            name='Start due account syncs',
            replace_existing=True,
        )
        self.scheduler.start()
        self.started = True
        logger.info('Auto-sync scheduler started')

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.started = False
            logger.info('Auto-sync scheduler stopped')

    def _check_and_sync_all(self):
        now = datetime.utcnow()
        due = []
        for api_key_hash in list_account_database_hashes(self.data_dir):
            try:
                path = get_database_path(api_key_hash)
                db = Database(path, initialize=False)
                preferences = db.get_auto_sync_preferences()
                if preferences.get('auto_sync_enabled', 'false').lower() != 'true':
                    continue
                state = background_sync.get_sync_state(api_key_hash)
                if state['status'] == 'syncing':
                    continue
                hours = auto_sync_frequency(preferences.get('auto_sync_frequency_hours'))
                due_at = next_auto_sync_at(state, hours, preferences)
                if due_at <= now:
                    due.append((due_at, api_key_hash, db))
            except Exception:
                logger.exception('Unable to check auto-sync for %s', api_key_hash[:8])

        # Start older work first. Small batches avoid an hourly wave of
        # credential checks, even if many accounts become due together.
        encryption_key = os.environ.get('ENCRYPTION_KEY')
        if not due or not encryption_key:
            return
        encryption = Encryption(encryption_key)
        started = 0
        for _, api_key_hash, db in sorted(due):
            try:
                encrypted = db.get_encrypted_api_key(api_key_hash)
                if not encrypted:
                    continue
                if background_sync.start_sync(encryption.decrypt(encrypted), api_key_hash, trigger='auto'):
                    started += 1
                    if started >= background_sync.AUTO_SYNC_SLOTS:
                        break
                else:
                    # The global slots are busy, or an account started
                    # between the scheduler scan and the lock attempt.
                    break
            except SlideRateLimitError:
                continue
            except Exception:
                logger.exception('Unable to start auto-sync for %s', api_key_hash[:8])


auto_sync_scheduler = AutoSyncScheduler()
