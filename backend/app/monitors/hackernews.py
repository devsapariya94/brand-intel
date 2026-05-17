"""Hacker News monitor implementation"""
import aiohttp
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from .base import BaseMonitor, MonitorConfig, RawHit
from .rate_limiter import RateLimiter
from .retry import with_retry, RetryConfig

logger = logging.getLogger(__name__)

FIREBASE_BASE = "https://hacker-news.firebaseio.com/v0"


class HackerNewsMonitor(BaseMonitor):
    """
    Monitors Hacker News for brand mentions in:
    1. Top/new stories
    2. Comments on stories
    3. Ask HN / Show HN posts
    4. Brand name and keyword discussions
    
    Uses the free Firebase HN API - no API key required.
    """
    
    def __init__(self, config: MonitorConfig):
        super().__init__(config)
        self.rate_limiter = RateLimiter(max_requests=60, time_window=60)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def search(self, brand: Dict[str, Any]) -> List[RawHit]:
        """Search HN for brand mentions"""
        hits = []
        
        keywords = brand.get("keywords", [])
        domain = brand.get("domain", "").lower()
        brand_name = brand.get("name", "").lower()
        
        search_terms = list(set(keywords + [brand_name] + ([domain] if domain else [])))
        search_terms = [t for t in search_terms if len(t) >= 3]
        
        for term in search_terms:
            try:
                story_hits = await self._search_stories(term, brand)
                hits.extend(story_hits)
            except Exception as e:
                logger.error(f"Error searching HN stories for '{term}': {e}")
            
            try:
                comment_hits = await self._search_comments(term, brand)
                hits.extend(comment_hits)
            except Exception as e:
                logger.error(f"Error searching HN comments for '{term}': {e}")
        
        return hits
    
    async def _search_stories(self, term: str, brand: Dict[str, Any]) -> List[RawHit]:
        """Search recent top/new stories for a term"""
        hits = []
        
        story_ids = await self._get_recent_story_ids(limit=100)
        
        for story_id in story_ids[:50]:
            try:
                story = await self._get_item(story_id)
                if not story or story.get("type") != "story":
                    continue
                
                title = (story.get("title") or "").lower()
                text = (story.get("text") or "").lower()
                url = (story.get("url") or "").lower()
                
                if term.lower() in title or term.lower() in text or term.lower() in url:
                    hits.append(self._create_hit_from_story(story, brand))
            except Exception:
                continue
        
        return hits
    
    async def _search_comments(self, term: str, brand: Dict[str, Any]) -> List[RawHit]:
        """Search recent comments for a term"""
        hits = []
        
        story_ids = await self._get_recent_story_ids(limit=50)
        
        for story_id in story_ids[:20]:
            try:
                story = await self._get_item(story_id)
                if not story or not story.get("kids"):
                    continue
                
                for kid_id in story.get("kids", [])[:30]:
                    try:
                        comment = await self._get_item(kid_id)
                        if not comment or comment.get("type") != "comment":
                            continue
                        
                        text = (comment.get("text") or "").lower()
                        if term.lower() in text:
                            hits.append(self._create_hit_from_comment(comment, story, brand))
                    except Exception:
                        continue
            except Exception:
                continue
        
        return hits
    
    @with_retry(RetryConfig(max_retries=2, base_delay=1.0))
    async def _get_item(self, item_id: int) -> Optional[Dict]:
        """Get a HN item (story or comment) by ID"""
        await self.rate_limiter.acquire()
        self.increment_api_calls()
        
        session = await self._get_session()
        async with session.get(
            f"{FIREBASE_BASE}/item/{item_id}.json",
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        ) as response:
            response.raise_for_status()
            return await response.json()
    
    @with_retry(RetryConfig(max_retries=2, base_delay=1.0))
    async def _get_recent_story_ids(self, limit: int = 100) -> List[int]:
        """Get IDs of recent stories"""
        await self.rate_limiter.acquire()
        self.increment_api_calls()
        
        session = await self._get_session()
        async with session.get(
            f"{FIREBASE_BASE}/topstories.json",
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        ) as response:
            response.raise_for_status()
            ids = await response.json()
            return ids[:limit] if ids else []
    
    def _create_hit_from_story(self, story: Dict, brand: Dict) -> RawHit:
        """Convert HN story to RawHit"""
        by_user = story.get("by", "unknown")
        title = story.get("title", "")
        text = story.get("text", "")
        url = story.get("url", "")
        score = story.get("score", 0)
        time_ts = story.get("time", 0)
        
        try:
            posted_at = datetime.fromtimestamp(time_ts, tz=timezone.utc)
        except Exception:
            posted_at = datetime.now(timezone.utc)
        
        content = f"Title: {title}\n\n{text}" if text else f"Title: {title}\nURL: {url}"
        
        return RawHit(
            source="hackernews",
            source_url=f"https://news.ycombinator.com/item?id={story['id']}",
            raw_content=content,
            metadata={
                "type": "story",
                "title": title,
                "author": by_user,
                "score": score,
                "descendants": story.get("descendants", 0),
                "posted_at": posted_at,
            },
            detected_at=datetime.now(timezone.utc)
        )
    
    def _create_hit_from_comment(self, comment: Dict, story: Dict, brand: Dict) -> RawHit:
        """Convert HN comment to RawHit"""
        by_user = comment.get("by", "unknown")
        text = comment.get("text", "")
        story_title = story.get("title", "")
        time_ts = comment.get("time", 0)
        
        try:
            posted_at = datetime.fromtimestamp(time_ts, tz=timezone.utc)
        except Exception:
            posted_at = datetime.now(timezone.utc)
        
        return RawHit(
            source="hackernews",
            source_url=f"https://news.ycombinator.com/item?id={comment['id']}",
            raw_content=f"Comment on: {story_title}\n\n{text}",
            metadata={
                "type": "comment",
                "author": by_user,
                "parent_story": story.get("id"),
                "story_title": story_title,
                "posted_at": posted_at,
            },
            detected_at=datetime.now(timezone.utc)
        )
    
    async def is_available(self) -> bool:
        """Check if HN Firebase API is accessible"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{FIREBASE_BASE}/topstories.json",
                timeout=aiohttp.ClientTimeout(total=5)
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
