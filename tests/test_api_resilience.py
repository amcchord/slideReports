import unittest
from unittest.mock import Mock, patch
import requests
from datetime import datetime, timezone
from lib.slide_api import SlideAPIClient, SlideRateLimitError

class ClientTests(unittest.TestCase):
    def client(self):
        c=SlideAPIClient('test-key')
        c._rate_limit=Mock()
        return c
    def response(self,status=200,body=None,headers=None):
        r=Mock(status_code=status,headers=headers or {})
        r.json.return_value=body or {'data':[]}
        if status>=400:r.raise_for_status.side_effect=requests.HTTPError('failure')
        return r
    @patch('lib.slide_api.time.time', return_value=1000)
    @patch.object(SlideAPIClient, '_cooldowns', {})
    @patch('lib.slide_api.time.sleep')
    def test_429_sets_cooldown_without_retrying(self, sleep, now):
        client = self.client()
        client.session.request = Mock(return_value=self.response(429, headers={'Retry-After': '600'}))
        with self.assertRaises(SlideRateLimitError) as rejected:
            client._make_request('GET', 'device')
        self.assertEqual(rejected.exception.retry_at, 1600)
        client.session.request.assert_called_once()
        sleep.assert_not_called()
        self.assertEqual(client.session.request.call_args.kwargs['timeout'], (5, 30))

        second = SlideAPIClient('test-key')
        second.session.request = Mock()
        with self.assertRaises(SlideRateLimitError):
            second._make_request('GET', 'agent')
        second.session.request.assert_not_called()

    @patch('lib.slide_api.time.sleep')
    def test_mutation_not_retried(self,sleep):
        c=self.client();c.session.request=Mock(return_value=self.response(503))
        with self.assertRaises(requests.HTTPError):c._make_request('POST','backup')
        self.assertEqual(c.session.request.call_count,1)
        sleep.assert_not_called()
    def test_full_final_page_without_next_offset_does_not_probe(self):
        client = self.client()
        params = {'client_id': 'c1'}
        client._make_request = Mock(return_value={
            'data': [{'id': i} for i in range(50)],
            'pagination': {},
        })
        self.assertEqual(len(client._paginate_all('agent', params)), 50)
        client._make_request.assert_called_once()
        self.assertEqual(params, {'client_id': 'c1'})

    def test_pagination_follows_explicit_next_offset(self):
        client = self.client()
        client._make_request = Mock(side_effect=[
            {'data': [{'id': 1}], 'pagination': {'next_offset': 20}},
            {'data': [{'id': 2}], 'pagination': {}},
        ])
        self.assertEqual(client._paginate_all('agent'), [{'id': 1}, {'id': 2}])
        self.assertEqual(client._make_request.call_args.kwargs['params']['offset'], 20)

    def test_malformed_collection_fails(self):
        c=self.client();c._make_request=Mock(return_value={'message':'missing data'})
        with self.assertRaises(ValueError):c._paginate_all('agent')
    def test_date_filters_are_rfc3339_and_audits_have_a_stable_upper_bound(self):
        c=self.client();c._paginate_all=Mock(return_value=[])
        start=datetime(2026,9,1)
        c.get_backups(start_date=start)
        self.assertEqual(c._paginate_all.call_args.args[1]['backup_started_after'],'2026-09-01T00:00:00+00:00')
        c.get_snapshots(start_date=start)
        self.assertEqual(c._paginate_all.call_args.args[1]['backup_started_after'],'2026-09-01T00:00:00+00:00')
        c.get_audits(start_date=start)
        params=c._paginate_all.call_args.args[1]
        self.assertEqual(params['audit_time_after'],'2026-09-01T00:00:00+00:00')
        self.assertIsNotNone(datetime.fromisoformat(params['audit_time_before']).tzinfo)
        self.assertEqual(params['sort_asc'],'false')
    def test_repeating_offset_fails(self):
        c=self.client();c._make_request=Mock(return_value={'data':[{'id':1}],'pagination':{'next_offset':0}})
        with self.assertRaises(ValueError):c._paginate_all('agent')
if __name__=='__main__':unittest.main()
