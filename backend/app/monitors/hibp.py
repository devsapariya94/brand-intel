"""HaveIBeenPwned (HIBP) monitor implementation"""
import aiohttp
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from .base import BaseMonitor, MonitorConfig, RawHit
from .rate_limiter import RateLimiter
from .retry import with_retry, RetryConfig

logger = logging.getLogger(__name__)


class HIBPMonitor(BaseMonitor):
    """
    Monitors HaveIBeenPwned for:
    1. New breaches affecting the brand's domain
    2. Specific email addresses from the brand
    
    API requires:
    - API key ($3.50/month)
    - User-Agent header
    - Rate limit: 1 request per 1.5 seconds (40 requests per minute)
    """
    
    def __init__(self, config: MonitorConfig, api_key: str, db_client=None):
        super().__init__(config)
        self.api_key = api_key
        self.base_url = "https://haveibeenpwned.com/api/v3"
        self.rate_limiter = RateLimiter(max_requests=40, time_window=60)
        self._seen_breaches: set = set()
        self._session: Optional[aiohttp.ClientSession] = None
        self._db = db_client.brand_intel if db_client else None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _load_seen_breaches(self, brand_id: str):
        if self._db:
            try:
                doc = await self._db.seen_breaches.find_one({"brand_id": brand_id})
                if doc:
                    self._seen_breaches = set(doc.get("breach_names", []))
            except Exception as e:
                logger.error(f"Failed to load seen breaches: {e}")
    
    async def _save_seen_breaches(self, brand_id: str):
        if self._db and self._seen_breaches:
            try:
                await self._db.seen_breaches.update_one(
                    {"brand_id": brand_id},
                    {"$set": {"breach_names": list(self._seen_breaches)}},
                    upsert=True
                )
            except Exception as e:
                logger.error(f"Failed to save seen breaches: {e}")
    
    async def search(self, brand: Dict[str, Any]) -> List[RawHit]:
        """Search HIBP for brand-related breaches"""
        hits = []
        
        brand_id = str(brand.get('_id', ''))
        await self._load_seen_breaches(brand_id)
        
        all_breaches = await self._fetch_all_breaches()
        
        brand_domain = brand.get('domain', '').lower()
        domain_breaches = [
            b for b in all_breaches 
            if b.get('Domain', '').lower() == brand_domain
        ]
        
        for breach in domain_breaches:
            breach_name = breach.get('Name', '')
            if breach_name not in self._seen_breaches:
                hits.append(self._create_hit_from_breach(breach, brand))
                self._seen_breaches.add(breach_name)
        
        await self._save_seen_breaches(brand_id)
        
        return hits
    
    @with_retry(RetryConfig(max_retries=3, base_delay=2.0))
    async def _fetch_all_breaches(self) -> List[Dict]:
        """Fetch all breaches from HIBP"""
        await self.rate_limiter.acquire()
        self.increment_api_calls()
        
        session = await self._get_session()
        async with session.get(
            f"{self.base_url}/breaches",
            headers={
                "hibp-api-key": self.api_key,
                "User-Agent": "BrandIntel/1.0"
            },
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        ) as response:
            response.raise_for_status()
            return await response.json()
    
    @with_retry(RetryConfig(max_retries=3, base_delay=2.0))
    async def _check_email_breach(self, email: str) -> List[Dict]:
        """Check if a specific email has been breached"""
        await self.rate_limiter.acquire()
        self.increment_api_calls()
        
        session = await self._get_session()
        async with session.get(
            f"{self.base_url}/breachedaccount/{email}",
            headers={
                "hibp-api-key": self.api_key,
                "User-Agent": "BrandIntel/1.0"
            },
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        ) as response:
            if response.status == 404:
                return []
            response.raise_for_status()
            return await response.json()
    
    def _create_hit_from_breach(self, breach: Dict, brand: Dict) -> RawHit:
        """Convert HIBP breach to RawHit"""
        breach_date_str = breach.get('BreachDate', '')
        try:
            posted_at = datetime.fromisoformat(breach_date_str)
            if posted_at.tzinfo is None:
                posted_at = posted_at.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            posted_at = datetime.now(timezone.utc)
        
        data_classes = breach.get('DataClasses', [])
        severity = self._calculate_severity(data_classes)
        
        return RawHit(
            source="hibp",
            source_url=f"https://haveibeenpwned.com/PwnedWebsites#{breach['Name']}",
            raw_content=breach.get('Description', ''),
            metadata={
                "breach_name": breach.get('Name'),
                "posted_at": posted_at,
                "data_classes": data_classes,
                "is_verified": breach.get('IsVerified', False),
                "pwn_count": breach.get('PwnCount', 0),
                "is_sensitive": breach.get('IsSensitive', False),
                "is_retired": breach.get('IsRetired', False),
                "is_spam_list": breach.get('IsSpamList', False),
                "severity": severity
            },
            detected_at=datetime.now(timezone.utc)
        )
    
    def _calculate_severity(self, data_classes: List[str]) -> str:
        """Calculate severity based on compromised data classes"""
        DATA_CLASS_SEVERITY = {
            "Passwords": "critical",
            "Password hints": "high",
            "Credit cards": "critical",
            "Social security numbers": "critical",
            "Bank account numbers": "critical",
            "Email addresses": "medium",
            "Names": "low",
            "Phone numbers": "medium",
            "Physical addresses": "medium",
            "IP addresses": "low",
            "Security questions and answers": "high",
            "Partial credit card data": "high"
        }
        
        severities = []
        for data_class in data_classes:
            severity = DATA_CLASS_SEVERITY.get(data_class, "low")
            severities.append(severity)
        
        if "critical" in severities:
            return "critical"
        elif "high" in severities:
            return "high"
        elif "medium" in severities:
            return "medium"
        else:
            return "low"
    
    async def is_available(self) -> bool:
        """Check if HIBP API is accessible"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/breaches",
                headers={
                    "hibp-api-key": self.api_key,
                    "User-Agent": "BrandIntel/1.0"
                },
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
