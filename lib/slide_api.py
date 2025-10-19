"""
Slide API client for fetching data from the Slide API.
Handles pagination, rate limiting, and all endpoint operations.
"""
import requests
import time
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta


class SlideAPIClient:
    """Client for interacting with the Slide API"""
    
    BASE_URL = "https://api.slide.tech/v1"
    ITEMS_PER_PAGE = 50
    RATE_LIMIT_DELAY = 0.1  # 100ms between requests to stay under 10/sec
    
    def __init__(self, api_key: str):
        """
        Initialize the API client.
        
        Args:
            api_key: Slide API token (starts with tk_)
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = time.time()
    
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
        """
        self._rate_limit()
        
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        response = self.session.request(method, url, params=params, json=json_data)
        
        if response.status_code == 429:
            # Rate limited - wait and retry
            time.sleep(1)
            return self._make_request(method, endpoint, params, json_data)
        
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
        Walks backward through pages until start_date is reached (if provided).
        
        Args:
            endpoint: API endpoint path
            params: Base query parameters
            progress_callback: Optional callback(current, total) for progress tracking
            start_date: Optional start date to stop pagination
            date_field: Field name to check against start_date
            
        Returns:
            List of all items
        """
        params = params or {}
        params['limit'] = self.ITEMS_PER_PAGE
        params['offset'] = 0
        
        all_items = []
        
        while True:
            data = self._make_request('GET', endpoint, params=params)
            
            items = data.get('data', [])
            if not items:
                break
            
            # Check if we've reached our start date
            if start_date:
                filtered_items = []
                reached_start = False
                
                for item in items:
                    # Parse the date field (all dates from API are UTC ISO format)
                    if date_field in item:
                        try:
                            date_str = item[date_field].replace('Z', '+00:00')
                            item_date = datetime.fromisoformat(date_str)
                            
                            # Make sure both dates are timezone-aware for comparison
                            if item_date.tzinfo is None:
                                from datetime import timezone as tz
                                item_date = item_date.replace(tzinfo=tz.utc)
                            
                            compare_start = start_date
                            if compare_start.tzinfo is None:
                                from datetime import timezone as tz
                                compare_start = compare_start.replace(tzinfo=tz.utc)
                            
                            if item_date >= compare_start:
                                filtered_items.append(item)
                            else:
                                reached_start = True
                                break
                        except Exception as e:
                            # If we can't parse the date, include the item
                            filtered_items.append(item)
                    else:
                        filtered_items.append(item)
                
                all_items.extend(filtered_items)
                
                if reached_start:
                    break
            else:
                all_items.extend(items)
            
            # Update progress
            if progress_callback:
                pagination = data.get('pagination', {})
                total = pagination.get('total', len(all_items))
                progress_callback(len(all_items), total)
            
            # Check if there are more pages
            pagination = data.get('pagination', {})
            next_offset = pagination.get('next_offset')
            
            if next_offset is None:
                break
            
            params['offset'] = next_offset
        
        return all_items
    
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
                   progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """Fetch all backups"""
        params = {}
        if agent_id:
            params['agent_id'] = agent_id
        if device_id:
            params['device_id'] = device_id
        return self._paginate_all('backup', params, progress_callback, start_date, 'started_at')
    
    def get_snapshots(self, agent_id: Optional[str] = None,
                     include_deleted: bool = True,
                     start_date: Optional[datetime] = None,
                     progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
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
        params = {'snapshot_location': 'location_any'}
        if agent_id:
            params['agent_id'] = agent_id
        
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
        """Fetch all audit logs"""
        params = {}
        if action_name:
            params['audit_action_name'] = action_name
        if resource_type_name:
            params['audit_resource_type_name'] = resource_type_name
        return self._paginate_all('audit', params, progress_callback, start_date, 'audit_time')
    
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
        except requests.HTTPError:
            return False

