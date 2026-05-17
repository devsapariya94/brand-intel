"""GitHub monitor implementation"""
import aiohttp
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from .base import BaseMonitor, MonitorConfig, RawHit
from .rate_limiter import RateLimiter
from .retry import with_retry, RetryConfig

logger = logging.getLogger(__name__)


class GitHubMonitor(BaseMonitor):
    """
    Monitors GitHub for:
    1. Email addresses matching brand patterns in code
    2. API keys/credentials in commits
    3. Brand name mentions in code comments
    4. Internal documentation leaks
    
    Uses GitHub REST API v3 and Search API.
    """
    
    def __init__(self, config: MonitorConfig, github_token: str):
        super().__init__(config)
        self.token = github_token
        self.base_url = "https://api.github.com"
        self.rate_limiter = RateLimiter(max_requests=30, time_window=60)
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
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    async def search(self, brand: Dict[str, Any]) -> List[RawHit]:
        """Search GitHub for brand mentions"""
        hits = []
        
        hits.extend(await self._search_emails(brand))
        hits.extend(await self._search_keywords(brand))
        hits.extend(await self._search_commits(brand))
        
        return hits
    
    async def _search_emails(self, brand: Dict[str, Any]) -> List[RawHit]:
        """Search for email patterns in code"""
        hits = []
        
        for email_pattern in brand.get('email_patterns', []):
            query = f'"{email_pattern}" in:file'
            results = await self._github_code_search(query)
            
            for result in results:
                try:
                    content = await self._fetch_file_content(result)
                    hits.append(self._create_hit_from_code(result, content, brand))
                except Exception as e:
                    logger.error(f"Error fetching GitHub file: {e}")
                    continue
        
        return hits
    
    async def _search_keywords(self, brand: Dict[str, Any]) -> List[RawHit]:
        """Search for keywords in sensitive files"""
        hits = []
        sensitive_files = ['.env', 'config', 'credentials', 'secrets']
        
        for keyword in brand.get('keywords', []):
            for file_type in sensitive_files:
                query = f'{keyword} filename:{file_type}'
                results = await self._github_code_search(query)
                
                for result in results:
                    try:
                        content = await self._fetch_file_content(result)
                        hits.append(self._create_hit_from_code(result, content, brand))
                    except Exception as e:
                        logger.error(f"Error fetching GitHub file: {e}")
                        continue
        
        return hits
    
    async def _search_commits(self, brand: Dict[str, Any]) -> List[RawHit]:
        """Search for recent commits mentioning brand"""
        hits = []
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%d')
        
        for keyword in brand.get('keywords', []):
            query = f'{keyword} author-date:>={yesterday}'
            results = await self._github_commit_search(query)
            
            for result in results:
                author_date = result.get('commit', {}).get('author', {}).get('date', '')
                try:
                    posted_at = datetime.fromisoformat(author_date.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    posted_at = datetime.now(timezone.utc)
                
                hits.append(RawHit(
                    source="github",
                    source_url=result.get('html_url', ''),
                    raw_content=result.get('commit', {}).get('message', ''),
                    metadata={
                        "repo_name": result.get('repository', {}).get('full_name'),
                        "author": result.get('commit', {}).get('author', {}).get('name'),
                        "posted_at": posted_at,
                        "sha": result.get('sha')
                    },
                    detected_at=datetime.now(timezone.utc)
                ))
        
        return hits
    
    @with_retry(RetryConfig(max_retries=3, base_delay=2.0))
    async def _github_code_search(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search GitHub code"""
        await self.rate_limiter.acquire()
        self.increment_api_calls()
        
        session = await self._get_session()
        async with session.get(
            f"{self.base_url}/search/code",
            params={"q": query, "per_page": max_results},
            headers=self._headers,
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return data.get('items', [])
    
    @with_retry(RetryConfig(max_retries=3, base_delay=2.0))
    async def _github_commit_search(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search GitHub commits"""
        await self.rate_limiter.acquire()
        self.increment_api_calls()
        
        session = await self._get_session()
        async with session.get(
            f"{self.base_url}/search/commits",
            params={"q": query, "per_page": max_results},
            headers={
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            },
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return data.get('items', [])
    
    @with_retry(RetryConfig(max_retries=3, base_delay=2.0))
    async def _fetch_file_content(self, file_result: Dict) -> str:
        """Fetch full content of a file"""
        await self.rate_limiter.acquire()
        self.increment_api_calls()
        
        session = await self._get_session()
        async with session.get(
            file_result['url'],
            headers={
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3.raw"
            },
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        ) as response:
            response.raise_for_status()
            return await response.text()
    
    def _create_hit_from_code(self, result: Dict, content: str, brand: Dict) -> RawHit:
        """Convert GitHub code search result to RawHit"""
        return RawHit(
            source="github",
            source_url=result.get('html_url', ''),
            raw_content=content,
            metadata={
                "repo_name": result.get('repository', {}).get('full_name'),
                "file_path": result.get('path'),
                "file_type": result.get('name', '').split('.')[-1] if '.' in result.get('name', '') else None,
                "sha": result.get('sha')
            },
            detected_at=datetime.now(timezone.utc)
        )
    
    async def is_available(self) -> bool:
        """Check if GitHub API is accessible"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/rate_limit",
                headers=self._headers,
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
