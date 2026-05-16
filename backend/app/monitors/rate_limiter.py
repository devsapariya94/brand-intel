"""Token bucket rate limiter for API calls"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from collections import deque
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter for API calls.
    Thread-safe for async operations.
    """
    
    def __init__(self, max_requests: int, time_window: int):
        """
        Args:
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """
        Wait until a request can be made within rate limits.
        Blocks if rate limit is exceeded.
        """
        while True:
            async with self._lock:
                now = datetime.now(timezone.utc)
                
                cutoff = now - timedelta(seconds=self.time_window)
                while self.requests and self.requests[0] < cutoff:
                    self.requests.popleft()
                
                if len(self.requests) < self.max_requests:
                    self.requests.append(now)
                    return
                
                oldest_request = self.requests[0]
                wait_until = oldest_request + timedelta(seconds=self.time_window)
                wait_seconds = (wait_until - now).total_seconds()
            
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
    
    def get_remaining(self) -> int:
        """Get number of remaining requests in current window"""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.time_window)
        
        current_requests = sum(1 for req in self.requests if req >= cutoff)
        return max(0, self.max_requests - current_requests)
    
    def get_reset_time(self) -> Optional[datetime]:
        """Get time when rate limit will reset"""
        if not self.requests:
            return None
        
        oldest_request = self.requests[0]
        return oldest_request + timedelta(seconds=self.time_window)
