"""Regression tests for API-key rejection and scheduled-report recovery."""
import os
import sys
import tempfile
import types
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

# EmailScheduler imports PDFService at module load time. The scheduler behavior
# under test does not render PDFs, so isolate it from optional local native
# WeasyPrint libraries.
pdf_service_stub = types.ModuleType('lib.pdf_service')
pdf_service_stub.PDFService = MagicMock
sys.modules['lib.pdf_service'] = pdf_service_stub

from lib.email_scheduler import EmailScheduler
from lib.database import Database, list_account_database_hashes
from lib.email_schedules import EmailScheduleManager
from lib.encryption import Encryption
from lib.slide_api import InvalidAPIKeyError, SlideAPIClient


def make_response(status_code, url, body=b'{}'):
    response = requests.Response()
    response.status_code = status_code
    response.url = url
    response._content = body
    response.request = requests.Request('GET', url).prepare()
    return response


class SlideAPIKeyStatusTests(unittest.TestCase):
    def make_client(self, responses):
        client = SlideAPIClient('tk_test')
        client.RATE_LIMIT_DELAY = 0
        client.session = MagicMock()
        client.session.request.side_effect = responses
        return client

    def test_endpoint_401_does_not_disable_key_when_device_is_accepted(self):
        audit_url = f'{SlideAPIClient.BASE_URL}/audit'
        device_url = f'{SlideAPIClient.BASE_URL}/device'
        client = self.make_client([
            make_response(401, audit_url),
            make_response(200, device_url),
        ])

        with self.assertRaises(requests.HTTPError):
            client._make_request('GET', 'audit')

        self.assertEqual(client.session.request.call_count, 2)

    def test_endpoint_401_disables_key_when_device_is_also_rejected(self):
        audit_url = f'{SlideAPIClient.BASE_URL}/audit'
        device_url = f'{SlideAPIClient.BASE_URL}/device'
        client = self.make_client([
            make_response(401, audit_url),
            make_response(401, device_url),
        ])

        with self.assertRaises(InvalidAPIKeyError):
            client._make_request('GET', 'audit')

    def test_device_401_is_direct_evidence_of_invalid_key(self):
        device_url = f'{SlideAPIClient.BASE_URL}/device'
        client = self.make_client([make_response(401, device_url)])

        with self.assertRaises(InvalidAPIKeyError):
            client._make_request('GET', 'device')

        self.assertEqual(client.session.request.call_count, 1)

    def test_inconclusive_confirmation_does_not_disable_key(self):
        audit_url = f'{SlideAPIClient.BASE_URL}/audit'
        client = self.make_client([
            make_response(401, audit_url),
            requests.ConnectionError('temporary connection failure'),
        ])

        with self.assertRaises(requests.HTTPError):
            client._make_request('GET', 'audit')


class ScheduledReportRecoveryTests(unittest.TestCase):
    @patch('lib.email_scheduler.EmailScheduleManager')
    @patch('lib.email_scheduler.Database')
    @patch('lib.email_scheduler.os.path.exists', return_value=True)
    @patch('lib.email_scheduler.get_database_path', return_value='/tmp/account.db')
    def test_due_schedule_runs_even_with_previously_disabled_key(
        self,
        _get_database_path,
        _path_exists,
        database_class,
        schedule_manager_class,
    ):
        database = database_class.return_value
        database.get_preference.return_value = 'America/New_York'

        schedule = {'schedule_id': 7}
        schedule_manager = schedule_manager_class.return_value
        schedule_manager.get_schedules_due.return_value = [schedule]

        scheduler = EmailScheduler.__new__(EmailScheduler)
        scheduler._execute_schedule = MagicMock()
        scheduler._check_and_send_for_key('abc12345')

        scheduler._execute_schedule.assert_called_once_with(
            'abc12345', schedule, 'America/New_York'
        )
        database.get_preference.assert_called_once_with(
            'timezone', 'America/New_York'
        )


class AccountDatabaseDiscoveryTests(unittest.TestCase):
    def test_only_canonical_account_databases_are_returned(self):
        with tempfile.TemporaryDirectory() as data_dir:
            filenames = [
                '0123456789abcdef.db',
                'fedcba9876543210.db',
                '0123456789abcdef_templates.db',
                '0123456789abcdef0123456789abcdef.db',
                'not-an-api-key.db',
            ]
            for filename in filenames:
                Path(data_dir, filename).touch()

            self.assertEqual(
                list_account_database_hashes(data_dir),
                ['0123456789abcdef', 'fedcba9876543210'],
            )

    def test_snapshot_pruning_deletes_only_records_older_than_cutoff(self):
        with tempfile.TemporaryDirectory() as data_dir:
            database = Database(str(Path(data_dir, '0123456789abcdef.db')))
            old_date = (datetime.utcnow() - timedelta(days=91)).isoformat()
            recent_date = (datetime.utcnow() - timedelta(days=1)).isoformat()

            with database.get_connection() as connection:
                connection.executemany(
                    'INSERT INTO snapshots (snapshot_id, backup_started_at) VALUES (?, ?)',
                    [
                        ('old-snapshot', old_date),
                        ('recent-snapshot', recent_date),
                    ],
                )

            self.assertEqual(database.prune_old_snapshots(days=90), 1)
            remaining = database.get_records('snapshots')
            self.assertEqual(
                [row['snapshot_id'] for row in remaining],
                ['recent-snapshot'],
            )


class DisabledKeyAlertRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.environment = patch.dict(os.environ, {'DATA_DIR': self.temp.name})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        # Import after isolating the global manager's data directory.
        from lib.background_sync import BackgroundSyncManager
        self.manager = BackgroundSyncManager()
        self.key_hash = '0123456789abcdef'
        self.db = Database(str(Path(self.temp.name, self.key_hash + '.db')))
        self.db.set_preference('api_key_status', 'disabled')
        self.db.set_preference('api_key_disabled_at', 'original-rejection')
        self.db.set_preference('api_key_disabled_alert_sent_at', 'original-alert')
        self.esm = EmailScheduleManager(self.db.db_path)
        self.schedule_id = self.esm.create_schedule(
            'Daily report', 'recipient@example.com', 1, 'last_day',
            schedule_frequency='daily', schedule_time='09:00',
        )
        self.scheduler = EmailScheduler.__new__(EmailScheduler)
        self.scheduler.email_service = MagicMock()
        self.scheduler.email_service.send_report_email.return_value = (True, 'ok')

    def run_sync(self, response_for_endpoint, sources=None):
        client = SlideAPIClient('tk_test')
        client.RATE_LIMIT_DELAY = 0
        client.session = MagicMock()
        def respond(method, url, **kwargs):
            status = response_for_endpoint(url.rsplit('/', 1)[-1])
            return make_response(status, url, b'{"data": []}')
        client.session.request.side_effect = respond
        with patch('lib.background_sync.SlideAPIClient', return_value=client), \
                patch('lib.slide_api.time.sleep'), \
                self.assertLogs('lib', level='INFO'):
            self.manager._run_sync('tk_test', self.key_hash, sources)

    def test_rate_limited_sync_does_not_rearm_alert(self):
        # Reproduce production: /device is rate limited, other sources reject
        # the key, and their baseline confirmations are also rate limited.
        self.run_sync(lambda endpoint: 429 if endpoint == 'device' else 401)
        state = self.manager.get_sync_state(self.key_hash)
        self.assertEqual(len(state['results']['errors']), 13)
        self.assertEqual(state['results']['total_items'], 0)
        self.assertEqual(self.db.get_preference('api_key_status'), 'disabled')
        self.assertEqual(self.db.get_preference('api_key_disabled_at'), 'original-rejection')
        self.assertEqual(self.db.get_preference('api_key_disabled_alert_sent_at'), 'original-alert')

        # A later definitive 401 must still suppress the report without
        # delivering another disabled-key notification.
        self.run_sync(lambda endpoint: 401)
        self.scheduler._execute_schedule(
            self.key_hash, self.esm.get_schedule(self.schedule_id), 'America/New_York'
        )
        self.scheduler.email_service.send_report_email.assert_not_called()
        self.assertEqual(self.db.get_preference('api_key_disabled_alert_sent_at'), 'original-alert')

    def test_confirmed_recovery_allows_one_alert_for_a_new_episode(self):
        # An empty but successful device response is still positive evidence.
        self.run_sync(lambda endpoint: 200)
        self.assertEqual(self.db.get_preference('api_key_status'), 'valid')
        self.assertIsNone(self.db.get_preference('api_key_disabled_at'))
        self.assertIsNone(self.db.get_preference('api_key_disabled_alert_sent_at'))
        self.run_sync(lambda endpoint: 401)
        for _ in range(2):
            self.scheduler._maybe_send_disabled_key_alert(self.db, self.esm, self.key_hash)
        self.scheduler.email_service.send_report_email.assert_called_once()

    def test_endpoint_permission_error_does_not_block_confirmed_recovery(self):
        self.run_sync(lambda endpoint: 200 if endpoint == 'device' else 403,
                      ['devices', 'agents'])
        self.assertEqual(self.db.get_preference('api_key_status'), 'valid')
        self.assertIsNone(self.db.get_preference('api_key_disabled_alert_sent_at'))

    def test_unverified_sync_does_not_clear_disabled_markers(self):
        for sources, status in [(['devices'], 503), (['agents'], 200), ([], 200)]:
            with self.subTest(sources=sources, status=status):
                self.db.set_preference('api_key_status', 'disabled')
                self.db.set_preference('api_key_disabled_alert_sent_at', 'original-alert')
                self.run_sync(lambda endpoint: status, sources)
                self.assertEqual(self.db.get_preference('api_key_status'), 'disabled')
                self.assertEqual(self.db.get_preference('api_key_disabled_alert_sent_at'), 'original-alert')

    def assert_schedule_skipped(self):
        with patch.object(self.scheduler, '_handle_disabled_key_skip') as skipped, \
                patch('lib.email_scheduler.ReportGenerator') as generator:
            self.scheduler._execute_schedule(
                self.key_hash, self.esm.get_schedule(self.schedule_id), 'America/New_York'
            )
        skipped.assert_called_once()
        generator.assert_not_called()
        self.scheduler.email_service.send_report_email.assert_not_called()

    def test_missing_stored_key_cannot_bypass_disabled_status(self):
        self.assert_schedule_skipped()

    def test_failed_presync_cannot_bypass_disabled_status(self):
        with patch.object(self.scheduler, '_sync_before_email',
                          side_effect=RuntimeError('temporary sync failure')):
            self.assert_schedule_skipped()

    def test_waiting_for_another_sync_cannot_bypass_disabled_status(self):
        encryption_key = '12' * 16
        self.db.store_encrypted_api_key(self.key_hash, Encryption(encryption_key).encrypt('tk_test'))
        self.manager.get_sync_state = MagicMock(side_effect=[
            {'status': 'syncing'}, {'status': 'error', 'error': 'Slide API key disabled'},
        ])
        with patch.dict(os.environ, {'ENCRYPTION_KEY': encryption_key}), \
                patch('lib.background_sync.background_sync', self.manager), \
                patch('time.sleep'):
            self.assert_schedule_skipped()


if __name__ == '__main__':
    unittest.main()
