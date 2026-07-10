"""Regression tests for API-key rejection and scheduled-report recovery."""
import sys
import tempfile
import types
import unittest
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
from lib.database import list_account_database_hashes
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


if __name__ == '__main__':
    unittest.main()
