"""Monitors module for data ingestion from multiple sources"""

from .base import BaseMonitor, MonitorConfig, RawHit
from .orchestrator import MonitorOrchestrator
from .detector import KeywordMatcher, MatchResult, Match
from .storage import RawHitStorage
from .health import MonitorHealthChecker
from .retry import with_retry, RetryConfig
from .rate_limiter import RateLimiter
from .pastebin import PastebinMonitor
from .github import GitHubMonitor
from .hibp import HIBPMonitor
from .reddit import RedditMonitor

__all__ = [
    "BaseMonitor",
    "MonitorConfig",
    "RawHit",
    "MonitorOrchestrator",
    "KeywordMatcher",
    "MatchResult",
    "Match",
    "RawHitStorage",
    "MonitorHealthChecker",
    "with_retry",
    "RetryConfig",
    "RateLimiter",
    "PastebinMonitor",
    "GitHubMonitor",
    "HIBPMonitor",
    "RedditMonitor",
]
