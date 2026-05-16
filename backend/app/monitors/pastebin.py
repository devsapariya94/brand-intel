"""Pastebin monitor implementation"""
import aiohttp
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from .base import BaseMonitor, MonitorConfig, RawHit
from .rate_limiter import RateLimiter
from .retry import with_retry, RetryConfig

logger = logging.getLogger(__name__)


class PastebinMonitor(BaseMonitor):
    """
    Monitors Pastebin for brand mentions using their scraping API.
    
    API Details:
    - Requires PRO account ($40/year)
    - Rate limit: 1 request per second
    - Returns last 100 pastes
    - Each paste has: key, date, title, size, expire, syntax
    """
    
    def __init__(self, config: MonitorConfig, api_key: str):
        super().__init__(config)
        self.api_key = api_key
        self.base_url = "https://scrape.pastebin.com"
        self.rate_limiter = RateLimiter(max_requests=60, time_window=60)
        self._last_seen_key: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _contains_brand_mention(self, text: str, brand: Dict[str, Any]) -> bool:
        """Quick check if text contains brand keywords"""
        if not text:
            return False
        
        text_lower = text.lower()
        
        for keyword in brand.get('keywords', []):
            if keyword.lower() in text_lower:
                return True
        
        for pattern in brand.get('email_patterns', []):
            if pattern.lower() in text_lower:
                return True
        
        domain = brand.get('domain', '')
        if domain and domain.lower() in text_lower:
            return True
        
        return False
    
    async def search(self, brand: Dict[str, Any]) -> List[RawHit]:
        """Search Pastebin for brand mentions"""
        hits = []
        
        recent_pastes = await self._fetch_recent_pastes()
        
        relevant_pastes = self._filter_pastes(recent_pastes)
        
        for paste in relevant_pastes:
            if not self._contains_brand_mention(paste.get('title', ''), brand):
                continue
            
            try:
                content = await self._fetch_paste_content(paste['key'])
                
                if not self._contains_brand_mention(content, brand):
                    continue
                
                hits.append(RawHit(
                    source="pastebin",
                    source_url=f"https://pastebin.com/{paste['key']}",
                    raw_content=content,
                    metadata={
                        "paste_id": paste['key'],
                        "posted_at": datetime.fromtimestamp(paste['date'], tz=timezone.utc),
                        "title": paste.get('title'),
                        "size": paste['size'],
                        "syntax": paste.get('syntax')
                    },
                    detected_at=datetime.now(timezone.utc)
                ))
            except Exception as e:
                logger.error(f"Error fetching paste {paste['key']}: {e}")
                continue
        
        return hits
    
    @with_retry(RetryConfig(max_retries=3, base_delay=2.0))
    async def _fetch_recent_pastes(self) -> List[Dict]:
        """Fetch metadata for recent pastes"""
        await self.rate_limiter.acquire()
        self.increment_api_calls()
        
        session = await self._get_session()
        async with session.get(
            f"{self.base_url}/api_scraping.php",
            params={"limit": 100},
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        ) as response:
            response.raise_for_status()
            return await response.json()
    
    @with_retry(RetryConfig(max_retries=3, base_delay=2.0))
    async def _fetch_paste_content(self, paste_key: str) -> str:
        """Fetch full content of a specific paste"""
        await self.rate_limiter.acquire()
        self.increment_api_calls()
        
        session = await self._get_session()
        async with session.get(
            f"https://pastebin.com/raw/{paste_key}",
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        ) as response:
            response.raise_for_status()
            return await response.text()
    
    def _filter_pastes(self, pastes: List[Dict]) -> List[Dict]:
        """Filter pastes by size and syntax type"""
        filtered = []
        
        for paste in pastes:
            if self._last_seen_key and paste['key'] == self._last_seen_key:
                break
            
            if paste['size'] > 1_000_000:
                continue
            
            if paste.get('syntax') in ['image', 'video']:
                continue
            
            filtered.append(paste)
        
        if pastes:
            self._last_seen_key = pastes[0]['key']
        
        return filtered
    
    async def is_available(self) -> bool:
        """Check if Pastebin API is accessible"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/api_scraping.php",
                params={"limit": 1},
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
        except Exception:
            return False
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Return current rate limit status"""
        return {
            "remaining": self.rate_limiter.get_remaining(),
            "reset_time": self.rate_limiter.get_reset_time(),
            "max_requests": self.rate_limiter.max_requests,
            "time_window": self.rate_limiter.time_window
        }
