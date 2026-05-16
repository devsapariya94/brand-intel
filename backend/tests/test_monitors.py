"""Unit tests for monitors component"""
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from app.monitors.detector import (
    KeywordMatcher, ExactMatcher, FuzzyMatcher, 
    RegexMatcher, DomainSimilarityMatcher, Match, MatchResult
)
from app.monitors.base import MonitorConfig, RawHit
from app.monitors.rate_limiter import RateLimiter
from app.monitors.retry import with_retry, RetryConfig


class TestExactMatcher:
    """Test exact keyword matching"""
    
    def test_exact_keyword_matching(self):
        matcher = ExactMatcher()
        
        content = "Found credentials for testcorp.com in this paste"
        keywords = ["testcorp"]
        
        matches = matcher.match(content, keywords)
        
        assert len(matches) > 0
        assert matches[0].keyword == "testcorp"
        assert matches[0].match_type == "exact"
        assert matches[0].confidence == 1.0
    
    def test_case_insensitive_matching(self):
        matcher = ExactMatcher()
        
        content = "TESTCORP leaked data"
        keywords = ["testcorp"]
        
        matches = matcher.match(content, keywords)
        
        assert len(matches) > 0
        assert matches[0].keyword == "testcorp"
    
    def test_multiple_occurrences(self):
        matcher = ExactMatcher()
        
        content = "testcorp data and testcorp credentials"
        keywords = ["testcorp"]
        
        matches = matcher.match(content, keywords)
        
        assert len(matches) == 2
    
    def test_email_pattern_matching(self):
        matcher = ExactMatcher()
        
        content = "Contact: admin@testcorp.com for more info"
        patterns = ["@testcorp.com"]
        
        matches = matcher.match_emails(content, patterns)
        
        assert len(matches) > 0
        assert matches[0].match_type == "email_pattern"
        assert "admin@testcorp.com" in matches[0].context


class TestFuzzyMatcher:
    """Test fuzzy matching for typosquatting"""
    
    def test_fuzzy_matching(self):
        matcher = FuzzyMatcher(threshold=85)
        
        content = "Check out testcorpp for leaked data"
        keywords = ["testcorp"]
        
        matches = matcher.match(content, keywords)
        
        assert len(matches) > 0
        assert matches[0].match_type == "fuzzy"
        assert matches[0].confidence > 0.85
    
    def test_threshold_filtering(self):
        matcher = FuzzyMatcher(threshold=90)
        
        content = "completely different word"
        keywords = ["testcorp"]
        
        matches = matcher.match(content, keywords)
        
        assert len(matches) == 0
    
    def test_multi_word_keyword(self):
        matcher = FuzzyMatcher(threshold=80)
        
        content = "The test corp data was leaked"
        keywords = ["test corp"]
        
        matches = matcher.match(content, keywords)
        
        assert len(matches) > 0
        assert matches[0].match_type == "fuzzy"
    
    def test_empty_keyword(self):
        matcher = FuzzyMatcher(threshold=85)
        
        content = "some content"
        keywords = [""]
        
        matches = matcher.match(content, keywords)
        
        assert len(matches) == 0


class TestRegexMatcher:
    """Test regex pattern matching"""
    
    def test_regex_pattern_matching(self):
        matcher = RegexMatcher()
        
        content = "api_key_testcorp = 'secret123'"
        patterns = [r"api[_-]?key.*testcorp"]
        
        matches = matcher.match(content, patterns)
        
        assert len(matches) > 0
        assert matches[0].match_type == "regex"
    
    def test_invalid_regex_handling(self):
        matcher = RegexMatcher()
        
        content = "some content"
        patterns = ["[invalid(regex"]
        
        matches = matcher.match(content, patterns)
        
        assert len(matches) == 0


class TestDomainSimilarityMatcher:
    """Test domain similarity matching"""
    
    def test_domain_similarity(self):
        matcher = DomainSimilarityMatcher(threshold=0.8)
        
        content = "Visit testcorp.co for more info"
        target_domain = "testcorp.com"
        
        matches = matcher.match(content, target_domain)
        
        assert len(matches) > 0
        assert matches[0].match_type == "domain_similarity"
        assert matches[0].confidence >= 0.8
    
    def test_exact_domain_excluded(self):
        matcher = DomainSimilarityMatcher(threshold=0.8)
        
        content = "Visit testcorp.com"
        target_domain = "testcorp.com"
        
        matches = matcher.match(content, target_domain)
        
        assert len(matches) == 0


class TestMatchResult:
    """Test match result aggregation"""
    
    def test_match_result_confidence_scoring(self):
        matches = [
            Match("testcorp", "exact", 0, 8, "testcorp", 1.0),
            Match("testcorp", "fuzzy", 20, 29, "testcorpp", 0.9),
        ]
        
        result = MatchResult(matches)
        
        assert result.confidence_score > 0.8
        assert result.is_match(threshold=0.5)
        assert "testcorp" in result.matched_keywords
    
    def test_empty_match_result(self):
        result = MatchResult([])
        
        assert result.confidence_score == 0.0
        assert not result.is_match()
        assert len(result.matched_keywords) == 0


class TestKeywordMatcher:
    """Test integrated keyword matcher"""
    
    def test_full_matching_pipeline(self):
        matcher = KeywordMatcher()
        
        content = "Leaked testcorp credentials at testcorp.com with admin@testcorp.com"
        brand = {
            "keywords": ["testcorp"],
            "email_patterns": ["@testcorp.com"],
            "regex_patterns": [r"testcorp.*credentials"],
            "domain": "testcorp.com"
        }
        
        result = matcher.match(content, brand)
        
        assert result.is_match()
        assert len(result.matches) > 0
        assert "testcorp" in result.matched_keywords
    
    def test_no_match(self):
        matcher = KeywordMatcher()
        
        content = "Some random content without brand mentions"
        brand = {
            "keywords": ["testcorp"],
            "email_patterns": ["@testcorp.com"],
            "regex_patterns": [],
            "domain": "testcorp.com"
        }
        
        result = matcher.match(content, brand)
        
        assert not result.is_match()


class TestMonitorConfig:
    """Test monitor configuration"""
    
    def test_default_config(self):
        config = MonitorConfig()
        
        assert config.enabled is True
        assert config.rate_limit_per_minute == 60
        assert config.timeout_seconds == 30
        assert config.max_retries == 3


class TestRawHit:
    """Test RawHit model"""
    
    def test_raw_hit_creation(self):
        hit = RawHit(
            source="pastebin",
            source_url="https://pastebin.com/test123",
            raw_content="Test content",
            metadata={"paste_id": "test123"},
            detected_at=datetime.now(timezone.utc)
        )
        
        assert hit.source == "pastebin"
        assert hit.source_url == "https://pastebin.com/test123"
        assert hit.metadata["paste_id"] == "test123"


class TestRateLimiter:
    """Test rate limiter"""
    
    @pytest.mark.asyncio
    async def test_allows_requests_within_limit(self):
        limiter = RateLimiter(max_requests=5, time_window=1)
        
        for _ in range(5):
            await limiter.acquire()
        
        assert limiter.get_remaining() == 0
    
    @pytest.mark.asyncio
    async def test_blocks_when_limit_reached(self):
        limiter = RateLimiter(max_requests=2, time_window=1)
        
        await limiter.acquire()
        await limiter.acquire()
        
        assert limiter.get_remaining() == 0
    
    @pytest.mark.asyncio
    async def test_resets_after_time_window(self):
        limiter = RateLimiter(max_requests=2, time_window=1)
        
        await limiter.acquire()
        await limiter.acquire()
        
        assert limiter.get_remaining() == 0
        
        await asyncio.sleep(1.1)
        
        assert limiter.get_remaining() == 2
    
    def test_get_remaining_initial(self):
        limiter = RateLimiter(max_requests=10, time_window=60)
        
        assert limiter.get_remaining() == 10
    
    def test_get_reset_time_empty(self):
        limiter = RateLimiter(max_requests=10, time_window=60)
        
        assert limiter.get_reset_time() is None


class TestRetry:
    """Test retry logic"""
    
    @pytest.mark.asyncio
    async def test_success_on_first_try(self):
        call_count = 0
        
        @with_retry(RetryConfig(max_retries=3, base_delay=0.01))
        async def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"
        
        result = await succeed()
        
        assert result == "ok"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retries_on_failure_then_succeeds(self):
        call_count = 0
        
        @with_retry(RetryConfig(max_retries=3, base_delay=0.01))
        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary error")
            return "ok"
        
        result = await flaky()
        
        assert result == "ok"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        call_count = 0
        
        @with_retry(RetryConfig(max_retries=2, base_delay=0.01))
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("permanent error")
        
        with pytest.raises(RuntimeError, match="permanent error"):
            await always_fail()
        
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_default_config_no_mutable_state(self):
        config1 = RetryConfig()
        config2 = RetryConfig()
        
        assert config1 is not config2


class TestStorage:
    """Test raw hit storage"""
    
    @pytest.mark.asyncio
    async def test_store_hit_deduplication_by_brand(self):
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.brand_intel.raw_hits = mock_collection
        
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = MagicMock(inserted_id="hit123")
        
        from app.monitors.storage import RawHitStorage
        from app.monitors.detector import MatchResult
        
        storage = RawHitStorage(mock_db)
        
        hit = RawHit(
            source="pastebin",
            source_url="https://pastebin.com/abc",
            raw_content="test content",
            metadata={},
            detected_at=datetime.now(timezone.utc)
        )
        match_result = MatchResult([Match("test", "exact", 0, 4, "test", 1.0)])
        
        result = await storage.store_hit(hit, "brand1", match_result)
        
        assert result == "hit123"
        call_args = mock_collection.find_one.call_args[0][0]
        assert "content_hash" in call_args
        assert "brand_id" in call_args
        assert call_args["brand_id"] == "brand1"
    
    @pytest.mark.asyncio
    async def test_store_hit_returns_none_for_duplicate(self):
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.brand_intel.raw_hits = mock_collection
        
        mock_collection.find_one.return_value = {"_id": "existing"}
        
        from app.monitors.storage import RawHitStorage
        from app.monitors.detector import MatchResult
        
        storage = RawHitStorage(mock_db)
        
        hit = RawHit(
            source="pastebin",
            source_url="https://pastebin.com/abc",
            raw_content="test content",
            metadata={},
            detected_at=datetime.now(timezone.utc)
        )
        match_result = MatchResult([Match("test", "exact", 0, 4, "test", 1.0)])
        
        result = await storage.store_hit(hit, "brand1", match_result)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_store_hits_batch_stats(self):
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.brand_intel.raw_hits = mock_collection
        
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = MagicMock(inserted_id="hit123")
        
        from app.monitors.storage import RawHitStorage
        from app.monitors.detector import MatchResult
        
        storage = RawHitStorage(mock_db)
        
        hit = RawHit(
            source="pastebin",
            source_url="https://pastebin.com/abc",
            raw_content="test content",
            metadata={},
            detected_at=datetime.now(timezone.utc)
        )
        match_result = MatchResult([Match("test", "exact", 0, 4, "test", 1.0)])
        
        hits = [
            (hit, "brand1", match_result),
            (hit, "brand1", match_result),
        ]
        
        result = await storage.store_hits_batch(hits)
        
        assert result["total"] == 2
        assert result["stored"] == 2
        assert result["duplicates"] == 0
    
    @pytest.mark.asyncio
    async def test_update_processing_status_uses_objectid(self):
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.brand_intel.raw_hits = mock_collection
        
        from app.monitors.storage import RawHitStorage
        
        storage = RawHitStorage(mock_db)
        
        await storage.update_processing_status("507f191e810c19729de860ea", "enriched")
        
        call_args = mock_collection.update_one.call_args[0][0]
        from bson import ObjectId
        assert isinstance(call_args["_id"], ObjectId)


class TestOrchestrator:
    """Test monitor orchestrator"""
    
    @pytest.mark.asyncio
    async def test_run_all_monitors_filters_by_config(self):
        from app.monitors.orchestrator import MonitorOrchestrator
        from app.monitors.detector import KeywordMatcher
        from app.monitors.storage import RawHitStorage
        
        mock_monitor = MagicMock()
        mock_monitor.name = "TestMonitor"
        mock_monitor.run = AsyncMock(return_value=[])
        
        mock_storage = MagicMock()
        mock_storage.store_hits_batch = AsyncMock(return_value={"stored": 0})
        
        mock_matcher = MagicMock()
        
        mock_db = MagicMock()
        mock_db.brand_intel = MagicMock()
        
        orchestrator = MonitorOrchestrator(
            monitors=[mock_monitor],
            storage=mock_storage,
            matcher=mock_matcher,
            db_client=mock_db
        )
        
        brand = {
            "_id": "brand123",
            "monitor_config": {
                "test_enabled": False
            }
        }
        
        result = await orchestrator.run_all_monitors(brand)
        
        assert result["monitors_run"] == 0
        mock_monitor.run.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_run_all_monitors_aggregates_errors(self):
        from app.monitors.orchestrator import MonitorOrchestrator
        from app.monitors.detector import KeywordMatcher
        from app.monitors.storage import RawHitStorage
        
        mock_monitor = MagicMock()
        mock_monitor.name = "TestMonitor"
        mock_monitor.run = AsyncMock(side_effect=RuntimeError("API down"))
        
        mock_storage = MagicMock()
        mock_storage.store_hits_batch = AsyncMock(return_value={"stored": 0})
        
        mock_matcher = MagicMock()
        
        mock_db = MagicMock()
        mock_db.brand_intel = MagicMock()
        mock_db.brand_intel.monitor_runs = AsyncMock()
        mock_db.brand_intel.monitor_runs.insert_one = AsyncMock(
            return_value=MagicMock(inserted_id="run123")
        )
        mock_db.brand_intel.monitor_runs.update_one = AsyncMock()
        
        orchestrator = MonitorOrchestrator(
            monitors=[mock_monitor],
            storage=mock_storage,
            matcher=mock_matcher,
            db_client=mock_db
        )
        
        brand = {
            "_id": "brand123",
            "monitor_config": {
                "test_enabled": True
            }
        }
        
        result = await orchestrator.run_all_monitors(brand)
        
        assert len(result["errors"]) == 1
        assert result["errors"][0]["monitor"] == "TestMonitor"
    
    @pytest.mark.asyncio
    async def test_run_scheduled_scan_uses_semaphore(self):
        from app.monitors.orchestrator import MonitorOrchestrator
        from app.monitors.detector import KeywordMatcher
        from app.monitors.storage import RawHitStorage
        
        mock_storage = MagicMock()
        mock_storage.store_hits_batch = AsyncMock(return_value={"stored": 0})
        
        mock_matcher = MagicMock()
        
        mock_db = MagicMock()
        mock_db.brand_intel = MagicMock()
        mock_db.brand_intel.brands = MagicMock()
        mock_db.brand_intel.brands.find = MagicMock()
        mock_db.brand_intel.brands.find.return_value.to_list = AsyncMock(
            return_value=[
                {"_id": "b1", "active": True, "monitor_config": {}},
                {"_id": "b2", "active": True, "monitor_config": {}},
            ]
        )
        
        orchestrator = MonitorOrchestrator(
            monitors=[],
            storage=mock_storage,
            matcher=mock_matcher,
            db_client=mock_db
        )
        
        orchestrator.run_all_monitors = AsyncMock(return_value={
            "brand_id": "test",
            "monitors_run": 0,
            "total_hits_found": 0,
            "total_hits_stored": 0,
            "errors": [],
            "completed_at": datetime.now(timezone.utc)
        })
        
        result = await orchestrator.run_scheduled_scan(max_concurrent=2)
        
        assert result["brands_scanned"] == 2
        assert result["successful_scans"] == 2


class TestMonitorHealthChecker:
    """Test monitor health checker"""
    
    @pytest.mark.asyncio
    async def test_get_health_status_unknown_when_no_runs(self):
        mock_db = MagicMock()
        mock_db.brand_intel = MagicMock()
        mock_db.brand_intel.monitor_runs = MagicMock()
        mock_db.brand_intel.monitor_runs.find = MagicMock()
        mock_db.brand_intel.monitor_runs.find.return_value.to_list = AsyncMock(return_value=[])
        
        from app.monitors.health import MonitorHealthChecker
        
        checker = MonitorHealthChecker(mock_db)
        
        result = await checker.get_health_status()
        
        assert result["overall_status"] == "unknown"
        assert result["monitors"]["pastebin"]["status"] == "unknown"
    
    @pytest.mark.asyncio
    async def test_get_health_status_healthy(self):
        mock_db = MagicMock()
        mock_db.brand_intel = MagicMock()
        mock_db.brand_intel.monitor_runs = MagicMock()
        
        now = datetime.now(timezone.utc)
        runs = [
            {
                "monitor_type": "pastebin",
                "status": "completed",
                "started_at": now,
                "execution_time_seconds": 1.0,
                "hits_found": 5,
                "hits_stored": 3,
            }
        ] * 10
        
        mock_db.brand_intel.monitor_runs.find = MagicMock()
        mock_db.brand_intel.monitor_runs.find.return_value.to_list = AsyncMock(return_value=runs)
        
        from app.monitors.health import MonitorHealthChecker
        
        checker = MonitorHealthChecker(mock_db)
        
        result = await checker.get_health_status()
        
        assert result["monitors"]["pastebin"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_check_stale_monitors(self):
        mock_db = MagicMock()
        mock_db.brand_intel = MagicMock()
        mock_db.brand_intel.monitor_runs = MagicMock()
        
        old_time = datetime.now(timezone.utc) - timedelta(hours=5)
        
        async def mock_find_one(query, sort=None):
            return None
        
        mock_db.brand_intel.monitor_runs.find_one = mock_find_one
        
        from app.monitors.health import MonitorHealthChecker
        
        checker = MonitorHealthChecker(mock_db)
        
        stale = await checker.check_stale_monitors(max_age_hours=2)
        
        assert len(stale) == 4
        assert "pastebin" in stale
        assert "github" in stale


@pytest.mark.asyncio
async def test_monitor_integration():
    """
    Integration test placeholder.
    This would test the full pipeline: monitor -> match -> store
    Requires MongoDB connection and mock API responses.
    """
    pass
