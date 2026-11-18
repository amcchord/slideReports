"""Regression checks for sync load, continuity and account isolation."""
import json
import os
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from lib.background_sync import BackgroundSyncManager
from lib.database import Database
from lib.scheduler import AutoSyncScheduler, next_auto_sync_at
from lib.slide_api import SlideAPIClient, SlideRateLimitError
from lib.sync import SyncEngine


class SyncConsumptionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.environment = patch.dict(os.environ, {'DATA_DIR': self.directory.name})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.account = '0123456789abcdef'
        self.db = Database(str(Path(self.directory.name, self.account + '.db')))
        self.client = Mock()
        self.engine = SyncEngine(self.client, self.db)
        self.retention = datetime.utcnow() - timedelta(days=90)

    def sync(self, *sources, incremental=True):
        return self.engine.sync_all(list(sources), self.retention, incremental=incremental)

    def test_history_uses_overlap_and_reconciles_older_mutations_daily(self):
        original = {'snapshot_id': 'old', 'locations': [{'type': 'local'}]}
        self.client.get_snapshots.return_value = [original]
        self.sync('snapshots')
        self.assertEqual(self.client.get_snapshots.call_args.kwargs['start_date'], self.retention)
        original['locations'] = [{'type': 'cloud'}]
        self.client.get_snapshots.return_value = []

        self.sync('snapshots')
        self.assertGreater(self.client.get_snapshots.call_args.kwargs['start_date'],
                           datetime.utcnow() - timedelta(hours=25))
        self.assertEqual(self.db.get_records('snapshots')[0]['exists_local'], 1)

        state = json.loads(self.db.get_preference('sync_history:snapshots'))
        state['last_full'] = (datetime.utcnow() - timedelta(days=1, hours=1)).isoformat()
        self.db.set_preference('sync_history:snapshots', json.dumps(state))
        self.client.get_snapshots.return_value = [original]
        self.sync('snapshots')
        self.assertEqual(self.client.get_snapshots.call_args.kwargs['start_date'], self.retention)
        self.assertEqual(self.db.get_records('snapshots')[0]['exists_cloud'], 1)

    def test_upgrade_reuses_legacy_history_and_clear_restarts_backfill(self):
        self.db.update_sync_status('backups', 'completed', 5000)
        self.client.get_backups.return_value = []
        self.sync('backups')
        self.assertGreater(self.client.get_backups.call_args.kwargs['start_date'],
                           datetime.utcnow() - timedelta(hours=25))
        self.db.clear_sync_data()
        self.sync('backups')
        self.assertEqual(self.client.get_backups.call_args.kwargs['start_date'], self.retention)

    def test_failed_history_fetch_does_not_advance_checkpoint(self):
        self.client.get_backups.return_value = []
        self.sync('backups')
        before = self.db.get_preference('sync_history:backups')
        self.client.get_backups.side_effect = SlideRateLimitError(time.time() + 300)
        with self.assertRaises(SlideRateLimitError):
            self.sync('backups', 'snapshots')
        self.client.get_snapshots.assert_not_called()
        self.assertEqual(self.db.get_preference('sync_history:backups'), before)

    def test_audit_backfill_resumes_same_window_even_when_timestamps_match(self):
        stamp = datetime.utcnow().isoformat()
        rows = [{'audit_id': str(i), 'audit_time': stamp} for i in range(3)]
        self.engine.BACKGROUND_AUDIT_PAGES = 1
        self.client.get_audit_pages.side_effect = [
            iter([([rows[0]], 50, None), ([rows[1]], 100, None)]),
            iter([([rows[1]], 100, None)]),
            iter([([rows[2]], None, None)]),
        ]
        first = self.sync('audits')
        self.assertEqual(first['sources']['audits']['status'], 'partial')
        lower, upper, _ = self.client.get_audit_pages.call_args.args
        self.sync('audits')
        self.assertEqual(self.client.get_audit_pages.call_args.args, (lower, upper, 50))
        last = self.sync('audits', incremental=False)
        self.assertEqual(self.client.get_audit_pages.call_args.args, (lower, upper, 100))
        self.assertEqual(last['sources']['audits']['status'], 'completed')
        self.assertEqual(len(self.db.get_records('audits')), 3)

    def test_sync_lock_coalesces_workers_and_rejects_cache_clear(self):
        first = BackgroundSyncManager()
        second = BackgroundSyncManager()
        entered, release = threading.Event(), threading.Event()

        def run(*args):
            entered.set()
            release.wait(5)

        with patch.object(first, '_run_sync', side_effect=run):
            self.assertTrue(first.start_sync('test-key', self.account))
            try:
                self.assertTrue(entered.wait(5))
                self.assertFalse(second.start_sync('test-key', self.account, trigger='email'))
                self.assertFalse(second.clear_synced_data(self.account))
            finally:
                release.set()

    def test_auto_scheduler_batches_due_keys_and_defers_rejected_keys(self):
        manager = Mock(AUTO_SYNC_SLOTS=4, DISABLED_KEY_RECHECK=timedelta(days=1))
        manager.get_sync_state.return_value = {'status': 'idle'}
        manager.start_sync.return_value = True
        for i in range(10):
            account = f'{i:016x}'
            db = Database(str(Path(self.directory.name, account + '.db')))
            db.set_preference('auto_sync_enabled', 'true')
            db.store_encrypted_api_key(account, 'ciphertext')
            if i == 0:
                db.set_preference('api_key_status', 'disabled')
                db.set_preference('api_key_retry_at', (datetime.utcnow() + timedelta(hours=20)).isoformat())
        with patch.dict(os.environ, {'ENCRYPTION_KEY': '12' * 16}), \
                patch('lib.scheduler.Encryption') as encryption, \
                patch('lib.scheduler.background_sync', manager):
            encryption.return_value.decrypt.return_value = 'test-key'
            AutoSyncScheduler()._check_and_sync_all()
        self.assertEqual([call.args[1] for call in manager.start_sync.call_args_list],
                         [f'{i:016x}' for i in range(1, 5)])

        retry = time.time() + 600
        state = {'retry_at': retry}
        self.assertEqual(next_auto_sync_at(state, 1, {}), datetime.utcfromtimestamp(retry))

    def test_request_budget_is_shared_across_client_instances(self):
        first, second = SlideAPIClient('first'), SlideAPIClient('second')
        first.RATE_LIMIT_DELAY = second.RATE_LIMIT_DELAY = 0.03
        first.UNVERIFIED_DELAY = second.UNVERIFIED_DELAY = 0.06
        first._rate_limit()
        start = time.monotonic()
        second._rate_limit()
        self.assertGreaterEqual(time.monotonic() - start, 0.05)

    def test_email_reuses_a_recent_account_refresh(self):
        from lib.email_scheduler import EmailScheduler

        manager = Mock(EMAIL_SYNC_FRESHNESS=timedelta(hours=1))
        manager.get_sync_state.return_value = {
            'status': 'completed',
            'last_full_attempt_at': (datetime.utcnow() - timedelta(minutes=20)).isoformat(),
        }
        scheduler = EmailScheduler.__new__(EmailScheduler)
        with patch('lib.background_sync.background_sync', manager):
            scheduler._sync_before_email(self.account, self.db)
        manager.start_sync.assert_not_called()
