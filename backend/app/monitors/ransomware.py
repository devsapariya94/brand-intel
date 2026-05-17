"""Ransomware.live monitor implementation"""
import aiohttp
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from .base import BaseMonitor, MonitorConfig, RawHit
from .rate_limiter import RateLimiter
from .retry import with_retry, RetryConfig

logger = logging.getLogger(__name__)

GROUPS_URL = "https://data.ransomware.live/groups.json"


class RansomwareMonitor(BaseMonitor):
    """
    Monitors ransomware.live for brand mentions in:
    1. Ransomware group victim lists
    2. New group announcements mentioning the brand
    3. Brand domain appearing as a victim
    
    Uses the free data.ransomware.live API - no API key required.
    Data is updated daily with new victims across all tracked groups.
    """
    
    def __init__(self, config: MonitorConfig):
        super().__init__(config)
        self.rate_limiter = RateLimiter(max_requests=1, time_window=60)
        self._session: Optional[aiohttp.ClientSession] = None
        self._cached_groups: Optional[List[Dict]] = None
        self._cache_time: Optional[datetime] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def search(self, brand: Dict[str, Any]) -> List[RawHit]:
        """Check ransomware.live for brand mentions"""
        hits = []
        
        brand_name = brand.get("name", "").lower()
        brand_domain = brand.get("domain", "").lower()
        keywords = [k.lower() for k in brand.get("keywords", [])]
        
        groups = await self._fetch_groups()
        if not groups:
            return hits
        
        for group in groups:
            group_name = group.get("name", "")
            description = (group.get("description") or "").lower()
            victim_count = group.get("_victim_count", 0)
            
            if victim_count <= 0:
                continue
            
            matched = False
            match_reasons = []
            
            if brand_name and brand_name in description:
                matched = True
                match_reasons.append(f"Brand name in group description")
            
            for kw in keywords:
                if len(kw) >= 3 and kw in description:
                    matched = True
                    match_reasons.append(f"Keyword '{kw}' in group description")
            
            locations = group.get("locations", [])
            for loc in locations:
                fqdn = (loc.get("fqdn") or "").lower()
                if brand_domain and brand_domain in fqdn:
                    matched = True
                    match_reasons.append(f"Domain found in leak site: {fqdn}")
            
            if matched:
                hits.append(self._create_hit_from_group(group, brand, match_reasons))
        
        return hits
    
    @with_retry(RetryConfig(max_retries=2, base_delay=5.0))
    async def _fetch_groups(self) -> List[Dict]:
        """Fetch ransomware groups data with caching"""
        now = datetime.now(timezone.utc)
        
        if self._cached_groups and self._cache_time:
            age = (now - self._cache_time).total_seconds()
            if age < 3600:
                return self._cached_groups
        
        await self.rate_limiter.acquire()
        self.increment_api_calls()
        
        session = await self._get_session()
        async with session.get(
            GROUPS_URL,
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        ) as response:
            response.raise_for_status()
            data = await response.json()
            self._cached_groups = data
            self._cache_time = now
            return data
    
    def _create_hit_from_group(self, group: Dict, brand: Dict, reasons: List[str]) -> RawHit:
        """Convert ransomware group data to RawHit"""
        group_name = group.get("name", "")
        description = group.get("description", "")
        victim_count = group.get("_victim_count", 0)
        group_type = group.get("type", {})
        is_raas = group_type.get("raas", False) if group_type else False
        meta = group.get("meta", "")
        
        locations = group.get("locations", [])
        leak_urls = []
        for loc in locations:
            fqdn = loc.get("fqdn", "")
            if fqdn:
                leak_urls.append(f"http://{fqdn}" if not fqdn.startswith("http") else fqdn)
        
        content_parts = [f"Group: {group_name}"]
        if description:
            content_parts.append(f"Description: {description}")
        content_parts.append(f"Victim Count: {victim_count}")
        if is_raas:
            content_parts.append("Type: RaaS (Ransomware-as-a-Service)")
        if meta:
            content_parts.append(f"Notes: {meta}")
        content_parts.append(f"Match Reasons: {'; '.join(reasons)}")
        if leak_urls:
            content_parts.append(f"Leak Sites: {', '.join(leak_urls[:5])}")
        
        return RawHit(
            source="ransomware",
            source_url=leak_urls[0] if leak_urls else f"https://ransomware.live/groups/{group_name}",
            raw_content="\n".join(content_parts),
            metadata={
                "group_name": group_name,
                "victim_count": victim_count,
                "is_raas": is_raas,
                "meta": meta,
                "match_reasons": reasons,
                "leak_sites": leak_urls,
                "detection_type": "group_match",
            },
            detected_at=datetime.now(timezone.utc)
        )
    
    async def is_available(self) -> bool:
        """Check if ransomware.live data is accessible"""
        try:
            session = await self._get_session()
            async with session.get(
                GROUPS_URL,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                return response.status == 200
        except Exception:
            return False
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        return {
            "remaining": self.rate_limiter.get_remaining(),
            "reset_time": self.rate_limiter.get_reset_time(),
            "max_requests": self.rate_limiter.max_requests,
            "time_window": self.rate_limiter.time_window
        }
