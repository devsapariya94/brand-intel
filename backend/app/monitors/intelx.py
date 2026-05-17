"""Intelligence X (IntelX) monitor implementation"""
import aiohttp
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from .base import BaseMonitor, MonitorConfig, RawHit
from .rate_limiter import RateLimiter
from .retry import with_retry, RetryConfig

logger = logging.getLogger(__name__)

INTELX_BASE = "https://free.intelx.io"


class IntelXMonitor(BaseMonitor):
    """
    Monitors Intelligence X for brand mentions across:
    1. Paste sites and data leaks
    2. Dark web forums and markets
    3. Document repositories
    4. Social media and public records
    
    Uses the free IntelX Search API.
    Requires a free API key from https://intelx.io/account?tab=developer
    """
    
    def __init__(self, config: MonitorConfig, api_key: str):
        super().__init__(config)
        self.api_key = api_key
        self.base_url = INTELX_BASE
        self.rate_limiter = RateLimiter(max_requests=10, time_window=60)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    @property
    def _headers(self):
        return {
            "x-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    async def search(self, brand: Dict[str, Any]) -> List[RawHit]:
        """Search IntelX for brand mentions"""
        hits = []
        
        brand_name = brand.get("name", "")
        brand_domain = brand.get("domain", "")
        keywords = brand.get("keywords", [])
        email_patterns = brand.get("email_patterns", [])
        
        search_terms = list(set(
            [brand_name, brand_domain] + keywords + email_patterns
        ))
        search_terms = [t for t in search_terms if t and len(t) >= 3]
        
        for term in search_terms[:5]:
            try:
                term_hits = await self._search_term(term, brand)
                hits.extend(term_hits)
            except Exception as e:
                logger.error(f"Error searching IntelX for '{term}': {e}")
        
        return hits
    
    async def _search_term(self, term: str, brand: Dict[str, Any]) -> List[RawHit]:
        """Search IntelX for a single term"""
        hits = []
        
        search_id = await self._submit_search(term)
        if not search_id:
            return hits
        
        records = await self._get_results(search_id, limit=20)
        
        for record in records:
            hits.append(self._create_hit_from_record(record, brand, term))
        
        return hits
    
    @with_retry(RetryConfig(max_retries=2, base_delay=3.0))
    async def _submit_search(self, term: str) -> Optional[str]:
        """Submit a search query to IntelX"""
        await self.rate_limiter.acquire()
        self.increment_api_calls()
        
        body = {
            "term": term,
            "buckets": [],
            "lookuplevel": 0,
            "timeout": 30,
            "maxresults": 20,
            "datefrom": "",
            "dateto": "",
            "sort": 0,
            "media": 0,
        }
        
        session = await self._get_session()
        async with session.post(
            f"{self.base_url}/intelligent/search",
            headers=self._headers,
            json=body,
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        ) as response:
            if response.status != 200:
                logger.warning(f"IntelX search failed for '{term}': {response.status}")
                return None
            data = await response.json()
            return data.get("id")
    
    @with_retry(RetryConfig(max_retries=3, base_delay=2.0))
    async def _get_results(self, search_id: str, limit: int = 20) -> List[Dict]:
        """Poll for search results"""
        await self.rate_limiter.acquire()
        self.increment_api_calls()
        
        session = await self._get_session()
        
        for attempt in range(10):
            async with session.get(
                f"{self.base_url}/intelligent/search/result",
                headers=self._headers,
                params={"id": search_id, "limit": limit},
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            ) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                status = data.get("status", 0)
                
                if status == 0 or status == 2:
                    records = data.get("records", [])
                    return records
                elif status == 1:
                    await asyncio.sleep(2)
                    continue
                else:
                    return []
        
        return []
    
    def _create_hit_from_record(self, record: Dict, brand: Dict, search_term: str) -> RawHit:
        """Convert IntelX record to RawHit"""
        name = record.get("name", "")
        date = record.get("date", "")
        bucket = record.get("bucket", "")
        systemid = record.get("systemid", "")
        
        tags = []
        for tag in record.get("tags", []):
            if isinstance(tag, dict):
                tags.append(tag.get("value", ""))
            else:
                tags.append(str(tag))
        
        content = f"Result: {name}\nDate: {date}\nSource: {bucket}\nTags: {', '.join(tags[:5])}"
        
        source_url = ""
        if systemid:
            source_url = f"https://intelx.io/search?term={search_term}"
        
        return RawHit(
            source="intelx",
            source_url=source_url,
            raw_content=content,
            metadata={
                "name": name,
                "date": date,
                "bucket": bucket,
                "systemid": systemid,
                "tags": tags,
                "search_term": search_term,
                "detection_type": "intelx_search",
            },
            detected_at=datetime.now(timezone.utc)
        )
    
    async def is_available(self) -> bool:
        """Check if IntelX API is accessible"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/intelligent/search",
                headers=self._headers,
                params={"term": "test", "maxresults": 1},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                return response.status in (200, 400)
        except Exception:
            return False
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        return {
            "remaining": self.rate_limiter.get_remaining(),
            "reset_time": self.rate_limiter.get_reset_time(),
            "max_requests": self.rate_limiter.max_requests,
            "time_window": self.rate_limiter.time_window
        }
