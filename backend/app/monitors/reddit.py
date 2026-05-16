"""Reddit monitor implementation"""
import asyncio
import logging
import praw
from typing import List, Dict, Any
from datetime import datetime, timezone
from .base import BaseMonitor, MonitorConfig, RawHit

logger = logging.getLogger(__name__)


class RedditMonitor(BaseMonitor):
    """
    Monitors Reddit for breach discussions and mentions.
    
    Uses PRAW (Python Reddit API Wrapper) for:
    1. Subreddit post monitoring
    2. Comment scanning
    3. Keyword search across Reddit
    """
    
    SECURITY_SUBREDDITS = [
        'netsec', 'hacking', 'cybersecurity', 
        'privacy', 'DataBreaches', 'pwned'
    ]
    
    def __init__(self, config: MonitorConfig, client_id: str, client_secret: str):
        super().__init__(config)
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent="BrandIntel/1.0"
        )
        self.reddit.read_only = True
    
    async def search(self, brand: Dict[str, Any]) -> List[RawHit]:
        """Search Reddit for brand mentions"""
        hits = []
        
        hits.extend(await self._search_subreddit_posts(brand))
        hits.extend(await self._search_comments(brand))
        hits.extend(await self._search_reddit_wide(brand))
        
        return hits
    
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
    
    async def _search_subreddit_posts(self, brand: Dict[str, Any]) -> List[RawHit]:
        """Search posts in security subreddits"""
        def _do_search():
            hits = []
            for subreddit_name in self.SECURITY_SUBREDDITS:
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    
                    for post in subreddit.new(limit=100):
                        content = f"{post.title}\n\n{post.selftext}"
                        
                        if self._contains_brand_mention(content, brand):
                            hits.append(RawHit(
                                source="reddit",
                                source_url=f"https://reddit.com{post.permalink}",
                                raw_content=content,
                                metadata={
                                    "subreddit": subreddit_name,
                                    "author": str(post.author) if post.author else "[deleted]",
                                    "posted_at": datetime.fromtimestamp(post.created_utc, tz=timezone.utc),
                                    "score": post.score,
                                    "num_comments": post.num_comments,
                                    "post_id": post.id,
                                    "is_comment": False
                                },
                                detected_at=datetime.now(timezone.utc)
                            ))
                            self.increment_api_calls()
                except Exception as e:
                    logger.error(f"Error searching subreddit {subreddit_name}: {e}")
                    continue
            return hits
        
        return await asyncio.to_thread(_do_search)
    
    async def _search_comments(self, brand: Dict[str, Any]) -> List[RawHit]:
        """Search comments in security subreddits"""
        def _do_search():
            hits = []
            for subreddit_name in self.SECURITY_SUBREDDITS:
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    
                    for comment in subreddit.comments(limit=500):
                        if self._contains_brand_mention(comment.body, brand):
                            hits.append(RawHit(
                                source="reddit",
                                source_url=f"https://reddit.com{comment.permalink}",
                                raw_content=comment.body,
                                metadata={
                                    "subreddit": subreddit_name,
                                    "author": str(comment.author) if comment.author else "[deleted]",
                                    "posted_at": datetime.fromtimestamp(comment.created_utc, tz=timezone.utc),
                                    "score": comment.score,
                                    "comment_id": comment.id,
                                    "is_comment": True
                                },
                                detected_at=datetime.now(timezone.utc)
                            ))
                            self.increment_api_calls()
                except Exception as e:
                    logger.error(f"Error searching comments in {subreddit_name}: {e}")
                    continue
            return hits
        
        return await asyncio.to_thread(_do_search)
    
    async def _search_reddit_wide(self, brand: Dict[str, Any]) -> List[RawHit]:
        """Search Reddit-wide for brand keywords"""
        def _do_search():
            hits = []
            
            for keyword in brand.get('keywords', [])[:3]:
                try:
                    for submission in self.reddit.subreddit('all').search(keyword, limit=50):
                        content = f"{submission.title}\n\n{submission.selftext}"
                        
                        if self._contains_brand_mention(content, brand):
                            hits.append(RawHit(
                                source="reddit",
                                source_url=f"https://reddit.com{submission.permalink}",
                                raw_content=content,
                                metadata={
                                    "subreddit": str(submission.subreddit),
                                    "author": str(submission.author) if submission.author else "[deleted]",
                                    "posted_at": datetime.fromtimestamp(submission.created_utc, tz=timezone.utc),
                                    "score": submission.score,
                                    "num_comments": submission.num_comments,
                                    "post_id": submission.id,
                                    "is_comment": False,
                                    "search_keyword": keyword
                                },
                                detected_at=datetime.now(timezone.utc)
                            ))
                            self.increment_api_calls()
                except Exception as e:
                    logger.error(f"Error in Reddit-wide search for '{keyword}': {e}")
                    continue
            
            return hits
        
        return await asyncio.to_thread(_do_search)
    
    async def is_available(self) -> bool:
        """Check if Reddit API is accessible"""
        try:
            def _check():
                self.reddit.subreddit('test').id
            await asyncio.to_thread(_check)
            return True
        except Exception:
            return False
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Return current rate limit status"""
        return {
            "remaining": "managed_by_praw",
            "reset_time": None,
            "max_requests": "60_per_minute",
            "time_window": 60
        }
