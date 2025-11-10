"""
Rate limiting for template operations to prevent abuse.
"""
import time
import logging
from collections import defaultdict
from threading import Lock
from typing import Tuple

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter for template operations"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 3600):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed in time window
            time_window: Time window in seconds (default: 1 hour)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = defaultdict(list)  # api_key_hash -> [timestamps]
        self.lock = Lock()
    
    def is_allowed(self, api_key_hash: str, operation: str = "template_operation") -> Tuple[bool, str]:
        """
        Check if a request is allowed for the given API key.
        
        Args:
            api_key_hash: Hash of the API key
            operation: Type of operation (for logging)
            
        Returns:
            Tuple of (is_allowed, message)
        """
        with self.lock:
            now = time.time()
            key = f"{api_key_hash}:{operation}"
            
            # Clean up old requests outside the time window
            self.requests[key] = [
                timestamp for timestamp in self.requests[key]
                if now - timestamp < self.time_window
            ]
            
            # Check if limit exceeded
            if len(self.requests[key]) >= self.max_requests:
                time_until_reset = self.time_window - (now - self.requests[key][0])
                minutes_until_reset = int(time_until_reset / 60)
                
                logger.warning(
                    f"Rate limit exceeded for {api_key_hash[:8]}: "
                    f"{operation} ({len(self.requests[key])}/{self.max_requests} in {self.time_window}s)"
                )
                
                return False, f"Rate limit exceeded. You can perform {self.max_requests} {operation}s per hour. Try again in {minutes_until_reset} minutes."
            
            # Record this request
            self.requests[key].append(now)
            
            return True, ""
    
    def get_remaining(self, api_key_hash: str, operation: str = "template_operation") -> int:
        """
        Get the number of remaining requests for an API key.
        
        Args:
            api_key_hash: Hash of the API key
            operation: Type of operation
            
        Returns:
            Number of remaining requests
        """
        with self.lock:
            now = time.time()
            key = f"{api_key_hash}:{operation}"
            
            # Clean up old requests
            self.requests[key] = [
                timestamp for timestamp in self.requests[key]
                if now - timestamp < self.time_window
            ]
            
            return max(0, self.max_requests - len(self.requests[key]))


# Global rate limiter instance
_global_limiter = None


def get_rate_limiter():
    """Get the global rate limiter instance"""
    global _global_limiter
    if _global_limiter is None:
        # 10 template operations per hour
        _global_limiter = RateLimiter(max_requests=10, time_window=3600)
    return _global_limiter


def check_rate_limit(api_key_hash: str, operation: str = "template_operation") -> Tuple[bool, str]:
    """
    Check if a request should be rate limited.
    
    Args:
        api_key_hash: Hash of the API key
        operation: Type of operation
        
    Returns:
        Tuple of (is_allowed, error_message)
    """
    limiter = get_rate_limiter()
    return limiter.is_allowed(api_key_hash, operation)

