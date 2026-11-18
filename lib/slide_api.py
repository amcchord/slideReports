"""
Slide API client for fetching data from the Slide API.
Handles pagination, rate limiting, and all endpoint operations.
"""
import fcntl
import hashlib
import logging
import math
import os
import threading
import time
from collections import Counter

import requests
from email.utils import parsedate_to_datetime
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timezone


logger = logging.getLogger(__name__)


class SlideRateLimitError(requests.HTTPError):
    """Pause the account when Slide returns 429."""

    def __init__(self, retry_at: float):
        self.retry_at = retry_at
        super().__init__('Slide API rate limited this account; sync deferred')


class InvalidAPIKeyError(Exception):
    """Raised when Slide's baseline endpoint rejects the key with 401/403.

    Distinct from a generic requests.HTTPError so callers (background sync,
    email scheduler) can mark the per-account API key as disabled and stop
    sending emails until the user re-enables the key in the Slide UI.
    """

    def __init__(self, status_code: int, message: str = ""):
        self.status_code = status_code
        super().__init__(message or f"Slide API key rejected (HTTP {status_code})")


class SlideAPIClient:
    """Client for interacting with the Slide API"""
    
    BASE_URL = "https://api.slide.tech/v1"
    ITEMS_PER_PAGE = 50
    RATE_LIMIT_DELAY = 0.2  # Five requests/sec across Reports workers.
    UNVERIFIED_DELAY = 1.1  # Protect Slide's shared failed-auth budget.
    MIN_COOLDOWN = 300
    _cooldowns = {}
    _cooldown_lock = threading.Lock()
    
    def __init__(self, api_key: str):
        """
        Initialize the API client.
        
        Args:
            api_key: Slide API token (starts with tk_)
        """
        self._key_hash = hashlib.sha256(api_key.encode()).digest()
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
        self._authorized = False
        self.device_verified = False
        self._checked_device = False
        self.request_counts = Counter()
    
    def _rate_limit(self):
        """Share a request budget across threads and WSGI worker generations."""
        data_dir = os.environ.get('DATA_DIR', '/var/www/reports.slide.recipes/data')
        with open(os.path.join(data_dir, '.slide-request-pace'), 'a+') as pace:
            while True:
                with self._cooldown_lock:
                    retry_at = self._cooldowns.get(self._key_hash, 0)
                    if retry_at > time.time():
                        raise SlideRateLimitError(retry_at)
                fcntl.flock(pace, fcntl.LOCK_EX)
                pace.seek(0)
                try:
                    last, last_unverified = map(float, pace.read().split())
                except ValueError:
                    last = last_unverified = 0
                now = time.monotonic()
                # A machine reboot can reset the monotonic clock.
                last = last if last <= now else 0
                last_unverified = last_unverified if last_unverified <= now else 0
                delay = last + self.RATE_LIMIT_DELAY - now
                if not self._authorized:
                    delay = max(delay, last_unverified + self.UNVERIFIED_DELAY - now)
                if delay <= 0:
                    pace.seek(0)
                    pace.truncate()
                    pace.write(f'{now} {last_unverified if self._authorized else now}')
                    pace.flush()
                    return
                fcntl.flock(pace, fcntl.LOCK_UN)
                time.sleep(delay)

    def _send(self, method, endpoint, **kwargs):
        self._rate_limit()
        self.request_counts['requests'] += 1
        self.request_counts[endpoint] += 1
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            response = self.session.request(
                method, url, timeout=(5, 30), allow_redirects=False, **kwargs
            )
        except requests.RequestException:
            self.request_counts['transport_errors'] += 1
            raise

        status = response.status_code
        if status == 429:
            self.request_counts['http_429'] += 1
            now = time.time()
            retry_at = now + self._retry_delay(response, self.MIN_COOLDOWN)
            with self._cooldown_lock:
                expired = [key for key, until in self._cooldowns.items() if until <= now]
                for key in expired:
                    del self._cooldowns[key]
                retry_at = max(retry_at, self._cooldowns.get(self._key_hash, 0))
                self._cooldowns[self._key_hash] = retry_at
            raise SlideRateLimitError(retry_at)
        if status in (401, 403):
            self.request_counts[f'http_{status}'] += 1
        if 200 <= status < 300:
            self._authorized = True
            if endpoint == 'device':
                self.device_verified = True
        return response

    @staticmethod
    def _retry_delay(response, minimum):
        value = response.headers.get('Retry-After')
        if not value:
            return minimum
        try:
            delay = float(value)
        except ValueError:
            try:
                delay = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
            except (ValueError, TypeError, OverflowError):
                return minimum
        return max(minimum, delay) if math.isfinite(delay) else minimum

    def _key_is_rejected(self) -> Optional[bool]:
        """At most one extra device probe for endpoint-specific denials per run."""
        if self.device_verified or self._checked_device:
            return None
        self._checked_device = True
        try:
            response = self._send('GET', 'device', params={'limit': 1})
        except SlideRateLimitError:
            raise
        except requests.RequestException:
            return None
        return response.status_code in (401, 403)

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None,
                     json_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make an API request with rate limiting.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON body for POST/PATCH
            
        Returns:
            Response data as dictionary
            
        Raises:
            requests.HTTPError: If request fails
            InvalidAPIKeyError: If the baseline endpoint rejects the API key
        """
        endpoint = endpoint.lstrip('/')
        # Retry only reads. Retrying a timed-out mutation could duplicate an operation.
        attempts = 3 if method.upper() == 'GET' else 1
        for attempt in range(attempts):
            try:
                response = self._send(method, endpoint, params=params, json=json_data)
            except (requests.Timeout, requests.ConnectionError):
                if attempt + 1 == attempts:
                    raise
                time.sleep(0.25 * 2 ** attempt)
                continue
            if response.status_code not in (502, 503, 504) or attempt + 1 == attempts:
                break
            delay = self._retry_delay(response, 0.25 * 2 ** attempt)
            if delay > 10:
                response.raise_for_status()
            time.sleep(delay)
        if 300 <= response.status_code < 400:
            raise requests.HTTPError('Unexpected redirect from Slide API', response=response)
        
        if response.status_code in (401, 403):
            endpoint_path = endpoint.split('?', 1)[0]

            # A rejection from the baseline endpoint is direct evidence that
            # the key itself is invalid. For every other endpoint, confirm
            # against /device before disabling the entire account. If the
            # confirmation succeeds or is inconclusive, raise the original
            # HTTP error so sync_all records only this source as failed.
            key_is_rejected = True
            if endpoint_path != 'device':
                key_is_rejected = self._key_is_rejected()

            if key_is_rejected is True:
                raise InvalidAPIKeyError(
                    response.status_code,
                    f"Slide API rejected the key ({response.status_code})",
                )

            response.raise_for_status()
        
        response.raise_for_status()
        
        if response.status_code == 204:
            return {}
        
        return response.json()
    
    def _paginate_all(self, endpoint: str, params: Optional[Dict] = None,
                     progress_callback: Optional[Callable[[int, int], None]] = None,
                     start_date: Optional[datetime] = None,
                     date_field: str = 'created_at') -> List[Dict[str, Any]]:
        """
        Fetch all items from a paginated endpoint.
        The server applies the requested date range. Check item dates as well
        when a cutoff was supplied.
        
        Args:
            endpoint: API endpoint path
            params: Base query parameters
            progress_callback: Optional callback(current, total) for progress tracking
            start_date: Optional start date to stop pagination
            date_field: Field name to check against start_date
            
        Returns:
            List of all items
        """
        all_items = []
        if start_date and start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        for items, _, total in self._collection_pages(endpoint, params):
            for item in items:
                if start_date and item.get(date_field):
                    try:
                        stamp = datetime.fromisoformat(item[date_field].replace('Z', '+00:00'))
                        if stamp.tzinfo is None:
                            stamp = stamp.replace(tzinfo=timezone.utc)
                        if stamp < start_date:
                            continue
                    except (ValueError, AttributeError):
                        pass
                all_items.append(item)
            if progress_callback:
                progress_callback(len(all_items), total or len(all_items))
        return all_items

    def _collection_pages(self, endpoint, params=None, offset=0):
        params = dict(params or {}, limit=self.ITEMS_PER_PAGE, offset=offset)
        while True:
            data = self._make_request('GET', endpoint, params=dict(params))
            if not isinstance(data, dict) or not isinstance(data.get('data'), list):
                raise ValueError('Slide API returned an invalid collection')

            pagination = data.get('pagination', {})
            if not isinstance(pagination, dict):
                raise ValueError('Slide API returned invalid pagination')
            next_offset = pagination.get('next_offset')
            if next_offset is not None:
                if type(next_offset) is not int or next_offset <= params['offset']:
                    raise ValueError('Slide API returned invalid pagination')
                if next_offset > 1000000:
                    raise ValueError('Slide collection exceeds the safety limit; narrow the date range')
            yield data['data'], next_offset, pagination.get('total')
            if next_offset is None:
                return
            params['offset'] = next_offset

    @staticmethod
    def _api_timestamp(value: datetime) -> str:
        # Background sync uses naive UTC datetimes; the API requires RFC3339.
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    
    def get_devices(self, client_id: Optional[str] = None,
                   progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """Fetch all devices"""
        params = {}
        if client_id:
            params['client_id'] = client_id
        return self._paginate_all('device', params, progress_callback)
    
    def get_agents(self, device_id: Optional[str] = None, client_id: Optional[str] = None,
                  progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """Fetch all agents"""
        params = {}
        if device_id:
            params['device_id'] = device_id
        if client_id:
            params['client_id'] = client_id
        return self._paginate_all('agent', params, progress_callback)
    
    def get_backups(self, agent_id: Optional[str] = None, device_id: Optional[str] = None,
                   start_date: Optional[datetime] = None,
                   progress_callback: Optional[Callable] = None,
                   end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Fetch all backups"""
        params = {}
        if agent_id:
            params['agent_id'] = agent_id
        if device_id:
            params['device_id'] = device_id
        params.update({'sort_by': 'start_time', 'sort_asc': 'false'})
        if start_date:
            params['backup_started_after'] = self._api_timestamp(start_date)
        if end_date:
            params['backup_started_before'] = self._api_timestamp(end_date)
        return self._paginate_all('backup', params, progress_callback, start_date, 'started_at')
    
    def get_snapshots(self, agent_id: Optional[str] = None,
                     include_deleted: bool = True,
                     start_date: Optional[datetime] = None,
                     progress_callback: Optional[Callable] = None,
                     end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Fetch all snapshots including deleted ones.
        
        Args:
            agent_id: Filter by agent ID
            include_deleted: Whether to include deleted snapshots (legacy parameter, always fetches all)
            start_date: Filter snapshots after this date
            progress_callback: Progress tracking callback
            
        Returns:
            List of all snapshots
        """
        # Use location_any to fetch snapshots wherever they exist (local, cloud, or deleted)
        params = {'snapshot_location': 'location_any', 'sort_by': 'backup_start_time', 'sort_asc': 'false'}
        if start_date:
            params['backup_started_after'] = self._api_timestamp(start_date)
        if agent_id:
            params['agent_id'] = agent_id
        
        if end_date:
            params['backup_started_before'] = self._api_timestamp(end_date)
        all_snapshots = self._paginate_all('snapshot', params, progress_callback, 
                                          start_date, 'backup_started_at')
        
        return all_snapshots
    
    def get_alerts(self, device_id: Optional[str] = None, agent_id: Optional[str] = None,
                  resolved: Optional[bool] = None,
                  progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """Fetch all alerts"""
        params = {}
        if device_id:
            params['device_id'] = device_id
        if agent_id:
            params['agent_id'] = agent_id
        if resolved is not None:
            params['resolved'] = str(resolved).lower()
        return self._paginate_all('alert', params, progress_callback)
    
    def get_audits(self, action_name: Optional[str] = None,
                  resource_type_name: Optional[str] = None,
                  start_date: Optional[datetime] = None,
                  progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """Fetch a stable audit window without chasing records created during the walk."""
        params = self._audit_params(start_date, datetime.now(timezone.utc))
        if action_name:
            params['audit_action_name'] = action_name
        if resource_type_name:
            params['audit_resource_type_name'] = resource_type_name
        return self._paginate_all('audit', params, progress_callback, start_date, 'audit_time')

    def get_audit_pages(self, start_date, end_date, offset):
        return self._collection_pages('audit', self._audit_params(start_date, end_date), offset)

    def _audit_params(self, start_date, end_date):
        params = {
            'sort_by': 'audit_time',
            'sort_asc': 'false',
            'audit_time_before': self._api_timestamp(end_date),
        }
        if start_date:
            params['audit_time_after'] = self._api_timestamp(start_date)
        return params

    def get_clients(self, progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """Fetch all clients"""
        return self._paginate_all('client', None, progress_callback)
    
    def get_users(self, progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """Fetch all users"""
        return self._paginate_all('user', None, progress_callback)
    
    def get_networks(self, progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """Fetch all networks"""
        return self._paginate_all('network', None, progress_callback)
    
    def get_virtual_machines(self, progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """Fetch all virtual machines"""
        return self._paginate_all('restore/virt', None, progress_callback)
    
    def get_file_restores(self, progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """Fetch all file restores"""
        return self._paginate_all('restore/file', None, progress_callback)
    
    def get_image_exports(self, progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """Fetch all image exports"""
        return self._paginate_all('restore/image', None, progress_callback)
    
    def get_accounts(self, progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """Fetch all accounts"""
        return self._paginate_all('account', None, progress_callback)
    
    def test_connection(self) -> bool:
        """
        Test if the API key is valid.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._make_request('GET', 'device', params={'limit': 1})
            return True
        except SlideRateLimitError:
            raise
        except (requests.HTTPError, InvalidAPIKeyError):
            return False
        finally:
            if self.request_counts:
                logger.info('slide_api_validation requests=%d http_429=%d http_401=%d http_403=%d',
                            self.request_counts['requests'], self.request_counts['http_429'],
                            self.request_counts['http_401'], self.request_counts['http_403'])
