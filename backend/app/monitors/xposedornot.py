"""XposedOrNot monitor implementation"""
import aiohttp
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from .base import BaseMonitor, MonitorConfig, RawHit
from .rate_limiter import RateLimiter
from .retry import with_retry, RetryConfig

logger = logging.getLogger(__name__)

API_BASE = "https://api.xposedornot.com/v1"


class XposedOrNotMonitor(BaseMonitor):
    """
    Monitors XposedOrNot breach database for:
    1. Brand domain appearing in known data breaches
    2. Brand email patterns in breach records
    3. New breaches affecting the brand's domain
    
    Uses the free XposedOrNot API - no API key required for basic checks.
    """
    
    def __init__(self, config: MonitorConfig):
        super().__init__(config)
        self.rate_limiter = RateLimiter(max_requests=30, time_window=60)
        self._session: Optional[aiohttp.ClientSession] = None
        self._seen_breaches: set = set()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def search(self, brand: Dict[str, Any]) -> List[RawHit]:
        """Check XposedOrNot for brand-related breaches"""
        hits = []
        
        domain = brand.get("domain", "").lower()
        email_patterns = brand.get("email_patterns", [])
        
        if domain:
            try:
                domain_hits = await self._check_domain(domain, brand)
                hits.extend(domain_hits)
            except Exception as e:
                logger.error(f"Error checking domain {domain}: {e}")
        
        for email_pattern in email_patterns[:5]:
            try:
                email_hits = await self._check_email_pattern(email_pattern, brand)
                hits.extend(email_hits)
            except Exception as e:
                logger.error(f"Error checking email pattern {email_pattern}: {e}")
        
        return hits
    
    @with_retry(RetryConfig(max_retries=2, base_delay=2.0))
    async def _check_domain(self, domain: str, brand: Dict[str, Any]) -> List[RawHit]:
        """Check breaches for a specific domain"""
        hits = []
        
        await self.rate_limiter.acquire()
        self.increment_api_calls()
        
        session = await self._get_session()
        async with session.get(
            f"{API_BASE}/breaches",
            params={"domain": domain},
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        ) as response:
            response.raise_for_status()
            breaches = await response.json()
        
        if not isinstance(breaches, list):
            return hits
        
        for breach in breaches:
            breach_id = breach.get("breachID", "")
            if not breach_id or breach_id in self._seen_breaches:
                continue
            
            self._seen_breaches.add(breach_id)
            hits.append(self._create_hit_from_breach(breach, brand))
        
        return hits
    
    @with_retry(RetryConfig(max_retries=2, base_delay=2.0))
    async def _check_email_pattern(self, email_pattern: str, brand: Dict[str, Any]) -> List[RawHit]:
        """Check if an email pattern appears in breaches"""
        hits = []
        
        if "@" not in email_pattern:
            return hits
        
        await self.rate_limiter.acquire()
        self.increment_api_calls()
        
        session = await self._get_session()
        async with session.get(
            f"{API_BASE}/check-email/{email_pattern}",
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        ) as response:
            response.raise_for_status()
            data = await response.json()
        
        if not data.get("found"):
            return hits
        
        breach_names = data.get("breaches", [])
        for breach_name in breach_names:
            if breach_name in self._seen_breaches:
                continue
            
            self._seen_breaches.add(breach_name)
            hits.append(self._create_hit_from_email_check(breach_name, email_pattern, brand))
        
        return hits
    
    def _create_hit_from_breach(self, breach: Dict, brand: Dict) -> RawHit:
        """Convert XposedOrNot breach record to RawHit"""
        breach_id = breach.get("breachID", "Unknown")
        breached_date = breach.get("breachedDate", "")
        exposed_data = breach.get("exposedData", "")
        exposed_records = breach.get("exposedRecords", 0)
        industry = breach.get("industry", "")
        verified = breach.get("verified", False)
        
        try:
            if breached_date:
                posted_at = datetime.fromisoformat(breached_date.replace("Z", "+00:00"))
            else:
                posted_at = datetime.now(timezone.utc)
        except Exception:
            posted_at = datetime.now(timezone.utc)
        
        content = (
            f"Breach: {breach_id}\n"
            f"Date: {breached_date}\n"
            f"Industry: {industry}\n"
            f"Exposed Data: {exposed_data}\n"
            f"Records: {exposed_records:,}\n"
            f"Verified: {verified}"
        )
        
        return RawHit(
            source="xposedornot",
            source_url=f"https://xposedornot.com",
            raw_content=content,
            metadata={
                "breach_id": breach_id,
                "breached_date": breached_date,
                "exposed_data": exposed_data,
                "exposed_records": exposed_records,
                "industry": industry,
                "verified": verified,
                "detection_type": "domain_match",
            },
            detected_at=datetime.now(timezone.utc)
        )
    
    def _create_hit_from_email_check(self, breach_name: str, email: str, brand: Dict) -> RawHit:
        """Convert email breach check result to RawHit"""
        content = (
            f"Email Pattern: {email}\n"
            f"Found in Breach: {breach_name}\n"
            f"This email pattern was found in a known data breach."
        )
        
        return RawHit(
            source="xposedornot",
            source_url=f"https://xposedornot.com",
            raw_content=content,
            metadata={
                "breach_id": breach_name,
                "email_pattern": email,
                "detection_type": "email_match",
            },
            detected_at=datetime.now(timezone.utc)
        )
    
    async def is_available(self) -> bool:
        """Check if XposedOrNot API is accessible"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{API_BASE}/breaches",
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
