"""Coordinate background synchronization and track account progress."""
import fcntl
import json
import logging
import os
import tempfile
import threading
import time
from contextlib import ExitStack
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from .database import Database, get_database_path
from .slide_api import InvalidAPIKeyError, SlideAPIClient, SlideRateLimitError
from .sync import SyncEngine

logger = logging.getLogger(__name__)


class BackgroundSyncManager:
    AUTO_SYNC_SLOTS = 4
    DISABLED_KEY_RECHECK = timedelta(days=1)
    EMAIL_SYNC_FRESHNESS = timedelta(hours=1)
    MIN_MANUAL_INTERVAL = timedelta(minutes=1)

    def __init__(self):
        self.base_dir = os.environ.get('DATA_DIR', '/var/www/reports.slide.recipes/data')
        os.makedirs(self.base_dir, exist_ok=True)

    def get_state_file(self, api_key_hash: str) -> str:
        return os.path.join(self.base_dir, f"{api_key_hash}_sync_state.json")

    def get_sync_state(self, api_key_hash: str) -> Dict[str, Any]:
        try:
            with open(self.get_state_file(api_key_hash)) as file:
                state = json.load(file)
        except (OSError, ValueError):
            return {'status': 'idle', 'started_at': None, 'current_source': None, 'progress': {}}

        if state.get('status') == 'syncing':
            try:
                updated = SyncEngine._parse_utc(state.get('last_update') or state.get('started_at'))
            except (ValueError, TypeError):
                updated = None
            if not updated or datetime.utcnow() - updated > timedelta(minutes=30):
                state.update(status='error', error='Sync stalled without a progress update')
        return state

    def update_sync_state(self, api_key_hash: str, state: Dict[str, Any]):
        with tempfile.NamedTemporaryFile(mode='w', dir=self.base_dir, delete=False) as file:
            temp_path = file.name
            try:
                json.dump(state, file)
                file.close()
                os.replace(temp_path, self.get_state_file(api_key_hash))
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

    def _try_lock(self, filename, stack):
        # Keep the lock file in place so every process locks the same inode.
        lock = open(os.path.join(self.base_dir, filename), 'a')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock.close()
            return False
        except OSError:
            lock.close()
            raise
        stack.enter_context(lock)
        return True

    def clear_synced_data(self, api_key_hash):
        with ExitStack() as locks:
            if not self._try_lock(f'.sync-{api_key_hash}', locks):
                return False
            Database(get_database_path(api_key_hash)).clear_sync_data()
            try:
                os.remove(self.get_state_file(api_key_hash))
            except FileNotFoundError:
                pass
            return True

    def start_sync(self, api_key: str, api_key_hash: str, data_sources: Optional[list] = None,
                   *, trigger: str = 'manual'):
        with ExitStack() as locks:
            if not self._try_lock(f'.sync-{api_key_hash}', locks):
                return False
            previous = self.get_sync_state(api_key_hash)
            retry_at = previous.get('retry_at', 0)
            if retry_at > time.time():
                raise SlideRateLimitError(retry_at)

            now = datetime.utcnow()
            if trigger == 'auto' and not any(
                self._try_lock(f'.auto-sync-slot-{slot}', locks) for slot in range(self.AUTO_SYNC_SLOTS)
            ):
                return False
            last_attempt = SyncEngine._parse_utc(previous.get('last_attempt_at'))
            if trigger == 'manual' and last_attempt and now - last_attempt < self.MIN_MANUAL_INTERVAL:
                return False

            state = {
                'status': 'syncing',
                'started_at': now.isoformat() + 'Z',
                'last_attempt_at': now.isoformat() + 'Z',
                'current_source': None,
                'progress': {},
                'cutoff_days': 90,
            }
            for key in ('completed_at', 'last_full_attempt_at', 'last_full_completed_at'):
                if key in previous:
                    state[key] = previous[key]
            if data_sources is None:
                state['last_full_attempt_at'] = state['started_at']
            self.update_sync_state(api_key_hash, state)

            worker_locks = locks.pop_all()
            try:
                thread = threading.Thread(
                    target=self._run_locked_sync,
                    args=(worker_locks, api_key, api_key_hash, data_sources, trigger),
                    daemon=True,
                )
                thread.start()
            except Exception:
                worker_locks.close()
                self.update_sync_state(api_key_hash, previous)
                raise
            return True

    def _run_locked_sync(self, locks, api_key, api_key_hash, data_sources, trigger):
        with locks:
            self._run_sync(api_key, api_key_hash, data_sources, trigger)

    def _run_sync(self, api_key: str, api_key_hash: str, data_sources: Optional[list],
                  trigger: str = 'manual'):
        state = self.get_sync_state(api_key_hash)
        start = time.monotonic()
        client = SlideAPIClient(api_key)
        db = None
        outcome = 'error'
        try:
            db = Database(get_database_path(api_key_hash))
            cutoff_date = datetime.utcnow() - timedelta(days=90)

            def progress_callback(source: str, current: int, total: int, status: str):
                # The owner of the account lock is the only writer for this run.
                state['current_source'] = source
                state['progress'][source] = {'current': current, 'total': total, 'status': status}
                state['last_update'] = datetime.utcnow().isoformat() + 'Z'
                self.update_sync_state(api_key_hash, state)

            results = SyncEngine(client, db).sync_all(
                data_sources,
                start_date=cutoff_date,
                progress_callback=progress_callback,
                incremental=trigger != 'manual',
            )
            if results['sources'].get('devices', {}).get('status') == 'completed':
                self._mark_key_valid(db)

            pruned_count = 0
            if results['sources'].get('snapshots', {}).get('status') == 'completed':
                try:
                    pruned_count = db.prune_old_snapshots(days=90)
                except Exception:
                    logger.exception('Snapshot pruning failed for %s', api_key_hash[:8])

            outcome = 'partial' if results['errors'] or any(
                source['status'] == 'partial' for source in results['sources'].values()
            ) else 'completed'
            state.update(status='completed', completed_at=datetime.utcnow().isoformat() + 'Z',
                         cutoff_date=cutoff_date.isoformat(), results=results,
                         pruned_snapshots=pruned_count, outcome=outcome)
            if data_sources is None and outcome == 'completed':
                state['last_full_completed_at'] = state['completed_at']

        except SlideRateLimitError as exc:
            outcome = 'rate_limited'
            state.update(status='error', error=str(exc), retry_at=exc.retry_at)
            if db is not None and client.device_verified:
                self._mark_key_valid(db)
        except InvalidAPIKeyError as exc:
            outcome = 'key_disabled'
            state.update(status='error', error='Slide API key disabled')
            if db is not None:
                now = datetime.utcnow()
                db.set_preference('api_key_status', 'disabled')
                db.claim_preference_once('api_key_disabled_at', now.isoformat())
                db.set_preference('api_key_retry_at', (now + self.DISABLED_KEY_RECHECK).isoformat())
            logger.info('Slide API key disabled for %s (HTTP %d)', api_key_hash[:8], exc.status_code)
        except Exception:
            logger.exception('Sync failed for %s', api_key_hash[:8])
            state.update(status='error', error='Sync failed')
        finally:
            state.update(started_at=None, current_source=None, progress={})
            if state['status'] == 'error':
                state['error_at'] = datetime.utcnow().isoformat() + 'Z'
            logger.info(
                'slide_sync trigger=%s outcome=%s requests=%d http_429=%d http_401=%d '
                'http_403=%d transport_errors=%d duration_s=%.1f endpoints=%s',
                trigger, outcome, client.request_counts['requests'], client.request_counts['http_429'],
                client.request_counts['http_401'], client.request_counts['http_403'],
                client.request_counts['transport_errors'], time.monotonic() - start,
                ','.join(f'{key}:{n}' for key, n in sorted(client.request_counts.items())
                         if key not in ('requests', 'transport_errors') and not key.startswith('http_')),
            )
            self.update_sync_state(api_key_hash, state)

    @staticmethod
    def _mark_key_valid(db):
        db.set_preference('api_key_status', 'valid')
        for key in ('api_key_disabled_at', 'api_key_disabled_alert_sent_at', 'api_key_retry_at'):
            db.delete_preference(key)


background_sync = BackgroundSyncManager()
