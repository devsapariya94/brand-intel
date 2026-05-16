"""Main monitoring daemon with APScheduler"""
import asyncio
import signal
import logging
from typing import Optional, List
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from motor.motor_asyncio import AsyncIOMotorClient

from .config import DaemonConfig
from .circuit_breaker import CircuitBreaker
from .alerting import AlertManager
from .dlq import DeadLetterQueue
from .healthcheck import HealthCheckServer
from ..monitors.orchestrator import MonitorOrchestrator
from ..monitors.storage import RawHitStorage
from ..monitors.detector import KeywordMatcher
from ..monitors.base import MonitorConfig
from ..monitors.base import BaseMonitor
from ..models.schemas import create_indexes

logger = logging.getLogger(__name__)


class MonitoringDaemon:
    """
    Main daemon process for continuous brand monitoring.
    
    Responsibilities:
    - Schedule periodic scans
    - Coordinate monitor execution
    - Handle failures with circuit breaker
    - Send alerts for critical issues
    - Manage graceful shutdown
    """
    
    def __init__(self, config: DaemonConfig):
        self.config = config
        self.scheduler = AsyncIOScheduler()
        self.db_client: Optional[AsyncIOMotorClient] = None
        self.orchestrator: Optional[MonitorOrchestrator] = None
        self.circuit_breaker: Optional[CircuitBreaker] = None
        self.alert_manager: Optional[AlertManager] = None
        self.dlq: Optional[DeadLetterQueue] = None
        self.health_server: Optional[HealthCheckServer] = None
        self.running = False
        self.shutdown_event = asyncio.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing monitoring daemon...")
        
        self._loop = asyncio.get_running_loop()
        
        # Initialize database connection
        self.db_client = AsyncIOMotorClient(self.config.mongodb_uri)
        
        # Test database connection
        try:
            await self.db_client.admin.command('ping')
            logger.info("Database connection successful")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
        
        # Create MongoDB indexes
        try:
            await create_indexes(self.db_client.brand_intel)
            logger.info("MongoDB indexes created/verified")
        except Exception as e:
            logger.warning(f"Failed to create indexes: {e}")
        
        # Initialize circuit breaker
        if self.config.circuit_breaker_enabled:
            self.circuit_breaker = CircuitBreaker(
                failure_threshold=self.config.circuit_breaker_failure_threshold,
                timeout_seconds=self.config.circuit_breaker_timeout_seconds
            )
            logger.info("Circuit breaker initialized")
        
        # Initialize alert manager
        self.alert_manager = AlertManager(
            db_client=self.db_client,
            slack_webhook_url=self.config.slack_webhook_url,
            alert_email=self.config.alert_email,
            failure_threshold=self.config.alert_failure_threshold
        )
        await self.alert_manager.initialize()
        logger.info("Alert manager initialized")
        
        # Initialize dead letter queue
        if self.config.dlq_enabled:
            self.dlq = DeadLetterQueue(
                db_client=self.db_client,
                max_retries=self.config.dlq_max_retries
            )
            logger.info("Dead letter queue initialized")
        
        # Initialize monitors
        monitors = self._create_monitors()
        
        # Initialize storage and matcher
        storage = RawHitStorage(self.db_client)
        matcher = KeywordMatcher()
        
        # Initialize orchestrator with circuit breaker
        self.orchestrator = MonitorOrchestrator(
            monitors=monitors,
            storage=storage,
            matcher=matcher,
            db_client=self.db_client,
            circuit_breaker=self.circuit_breaker,
            dlq=self.dlq
        )
        logger.info("Monitor orchestrator initialized")
        
        # Initialize health check server
        if self.config.health_check_enabled:
            self.health_server = HealthCheckServer(
                db_client=self.db_client,
                port=self.config.health_check_port
            )
            await self.health_server.start()
            logger.info(f"Health check server enabled on port {self.config.health_check_port}")
        
        # Validate configuration
        warnings = self.config.validate_config()
        for warning in warnings:
            logger.warning(f"Configuration warning: {warning}")
        
        logger.info("Daemon initialization complete")
    
    def _create_monitors(self) -> List[BaseMonitor]:
        """Create monitor instances with configuration and API keys"""
        from ..monitors.pastebin import PastebinMonitor
        from ..monitors.github import GitHubMonitor
        from ..monitors.reddit import RedditMonitor
        from ..monitors.hibp import HIBPMonitor
        
        monitors = []
        
        # Pastebin
        pastebin_config = MonitorConfig(
            enabled=True,
            rate_limit_per_minute=self.config.pastebin_rate_limit,
            timeout_seconds=self.config.monitor_timeout_seconds,
            max_retries=self.config.max_retries
        )
        if self.config.pastebin_api_key:
            monitors.append(PastebinMonitor(pastebin_config, api_key=self.config.pastebin_api_key))
            logger.info("Pastebin monitor created")
        else:
            logger.warning("Pastebin monitor skipped: no API key configured")
        
        # GitHub
        github_config = MonitorConfig(
            enabled=True,
            rate_limit_per_minute=self.config.github_rate_limit,
            timeout_seconds=self.config.monitor_timeout_seconds,
            max_retries=self.config.max_retries
        )
        if self.config.github_token:
            monitors.append(GitHubMonitor(github_config, github_token=self.config.github_token))
            logger.info("GitHub monitor created")
        else:
            logger.warning("GitHub monitor skipped: no token configured")
        
        # Reddit
        reddit_config = MonitorConfig(
            enabled=True,
            rate_limit_per_minute=self.config.reddit_rate_limit,
            timeout_seconds=self.config.monitor_timeout_seconds,
            max_retries=self.config.max_retries
        )
        if self.config.reddit_client_id and self.config.reddit_client_secret:
            monitors.append(RedditMonitor(
                reddit_config,
                client_id=self.config.reddit_client_id,
                client_secret=self.config.reddit_client_secret
            ))
            logger.info("Reddit monitor created")
        else:
            logger.warning("Reddit monitor skipped: no credentials configured")
        
        # HIBP
        hibp_config = MonitorConfig(
            enabled=True,
            rate_limit_per_minute=self.config.hibp_rate_limit,
            timeout_seconds=self.config.monitor_timeout_seconds,
            max_retries=self.config.max_retries
        )
        if self.config.hibp_api_key:
            monitors.append(HIBPMonitor(
                hibp_config,
                api_key=self.config.hibp_api_key,
                db_client=self.db_client
            ))
            logger.info("HIBP monitor created")
        else:
            logger.warning("HIBP monitor skipped: no API key configured")
        
        logger.info(f"Created {len(monitors)} monitors")
        return monitors
    
    async def scan_job(self):
        """Main scan job executed on schedule"""
        try:
            logger.info("=" * 60)
            logger.info("Starting scheduled scan cycle")
            logger.info("=" * 60)
            
            start_time = datetime.now(timezone.utc)
            
            # Run all monitors
            result = await self.orchestrator.run_scheduled_scan(
                max_concurrent=self.config.max_concurrent_brands
            )
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            logger.info(
                f"Scan cycle completed in {execution_time:.2f}s: "
                f"{result['brands_scanned']} brands, "
                f"{result['successful_scans']} successful, "
                f"{result['failed_scans']} failed"
            )
            
            # Check for high error rate
            if result['brands_scanned'] > 0:
                error_rate = result['failed_scans'] / result['brands_scanned']
                if error_rate > 0.5:
                    await self.alert_manager.alert_high_error_rate(error_rate)
            
            # Process circuit breaker states
            if self.circuit_breaker:
                cb_stats = self.circuit_breaker.get_stats()
                for monitor_name, stats in cb_stats.items():
                    if stats['state'] == 'open':
                        await self.alert_manager.alert_monitor_down(
                            monitor_name=monitor_name,
                            error="Circuit breaker open",
                            failure_count=stats['failure_count']
                        )
                    elif stats['state'] == 'closed' and stats['failure_count'] == 0:
                        await self.alert_manager.alert_monitor_recovered(monitor_name)
            
            # Check DLQ overflow
            if self.dlq:
                dlq_stats = await self.dlq.get_stats()
                if dlq_stats['pending'] > 100:
                    await self.alert_manager.alert_dlq_overflow(
                        dlq_count=dlq_stats['pending']
                    )
            
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Scan job failed: {e}", exc_info=True)
            if self.alert_manager:
                await self.alert_manager.alert_database_error(str(e))
    
    async def dlq_retry_job(self):
        """Periodic job to retry DLQ items"""
        if not self.dlq:
            return
        
        try:
            logger.info("Processing DLQ retry job...")
            
            pending_items = await self.dlq.get_pending_items(
                limit=50,
                max_retry_count=self.config.dlq_max_retries
            )
            
            if not pending_items:
                logger.debug("No pending DLQ items")
                return
            
            logger.info(f"Found {len(pending_items)} pending DLQ items")
            
            for item in pending_items:
                try:
                    await self.dlq.retry_item(
                        dlq_id=str(item['_id']),
                        processor_func=self._process_dlq_item
                    )
                except Exception as e:
                    logger.error(f"Failed to retry DLQ item {item['_id']}: {e}")
            
        except Exception as e:
            logger.error(f"DLQ retry job failed: {e}", exc_info=True)
    
    async def _process_dlq_item(self, hit_data: dict):
        """Process a single DLQ item by re-storing it"""
        from ..monitors.base import RawHit
        from ..monitors.detector import KeywordMatcher
        
        brand_id = hit_data.get('brand_id')
        if not brand_id:
            raise ValueError("DLQ item missing brand_id")
        
        brand = await self.db_client.brand_intel.brands.find_one({"_id": brand_id})
        if not brand:
            raise ValueError(f"Brand {brand_id} not found")
        
        raw_hit = RawHit(
            source=hit_data.get('source', 'unknown'),
            source_url=hit_data.get('source_url', ''),
            raw_content=hit_data.get('raw_content', ''),
            metadata=hit_data.get('metadata', {}),
            detected_at=hit_data.get('detected_at', datetime.now(timezone.utc))
        )
        
        matcher = KeywordMatcher()
        match_result = matcher.match(raw_hit.raw_content, brand)
        
        if not match_result.is_match():
            raise ValueError("Hit no longer matches brand keywords")
        
        storage = RawHitStorage(self.db_client)
        await storage.store_hit(raw_hit, str(brand_id), match_result)
    
    async def health_check_job(self):
        """Periodic health check"""
        try:
            from ..monitors.health import MonitorHealthChecker
            health_checker = MonitorHealthChecker(self.db_client)
            
            stale_monitors = await health_checker.check_stale_monitors(
                max_age_hours=2
            )
            
            if stale_monitors:
                logger.warning(f"Stale monitors detected: {stale_monitors}")
                for monitor in stale_monitors:
                    await self.alert_manager.alert_monitor_down(
                        monitor_name=monitor,
                        error="No recent runs",
                        failure_count=1
                    )
            
        except Exception as e:
            logger.error(f"Health check job failed: {e}", exc_info=True)
    
    async def cleanup_stale_runs_job(self):
        """Clean up stale 'running' monitor_runs records from crashes"""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            result = await self.db_client.brand_intel.monitor_runs.update_many(
                {
                    "status": "running",
                    "started_at": {"$lt": cutoff}
                },
                {
                    "$set": {
                        "status": "failed",
                        "error_message": "Stale run - process crashed",
                        "completed_at": datetime.now(timezone.utc)
                    }
                }
            )
            if result.modified_count > 0:
                logger.info(f"Cleaned up {result.modified_count} stale monitor runs")
        except Exception as e:
            logger.error(f"Stale run cleanup failed: {e}", exc_info=True)
    
    def setup_scheduler(self):
        """Configure scheduled jobs"""
        self.scheduler.add_job(
            self.scan_job,
            trigger=IntervalTrigger(minutes=self.config.scan_interval_minutes),
            id='monitor_scan',
            name='Monitor all brands',
            replace_existing=True,
            max_instances=1,
            coalesce=True
        )
        logger.info(f"Scheduled scan job every {self.config.scan_interval_minutes} minutes")
        
        if self.dlq:
            self.scheduler.add_job(
                self.dlq_retry_job,
                trigger=IntervalTrigger(minutes=30),
                id='dlq_retry',
                name='Retry DLQ items',
                replace_existing=True,
                max_instances=1
            )
            logger.info("Scheduled DLQ retry job every 30 minutes")
        
        self.scheduler.add_job(
            self.health_check_job,
            trigger=IntervalTrigger(hours=1),
            id='health_check',
            name='Health check',
            replace_existing=True,
            max_instances=1
        )
        logger.info("Scheduled health check job every hour")
        
        self.scheduler.add_job(
            self.cleanup_stale_runs_job,
            trigger=IntervalTrigger(hours=6),
            id='cleanup_stale_runs',
            name='Cleanup stale monitor runs',
            replace_existing=True,
            max_instances=1
        )
        logger.info("Scheduled stale run cleanup job every 6 hours")
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown on signals"""
        loop = asyncio.get_running_loop()
        
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(self._handle_signal(s))
            )
        logger.info("Signal handlers configured")
    
    async def _handle_signal(self, signum: int):
        """Handle received signal safely within event loop"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown"""
        if not self.running:
            return
        
        logger.info("=" * 60)
        logger.info("Shutting down daemon...")
        logger.info("=" * 60)
        
        self.running = False
        
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")
        
        if self.health_server:
            await self.health_server.stop()
            logger.info("Health check server stopped")
        
        if self.orchestrator:
            await self.orchestrator.close_all()
            logger.info("Monitor resources closed")
        
        if self.alert_manager:
            await self.alert_manager.close()
            logger.info("Alert manager closed")
        
        if self.db_client:
            self.db_client.close()
            logger.info("Database connection closed")
        
        logger.info("Daemon shutdown complete")
        self.shutdown_event.set()
    
    async def run(self):
        """Main daemon loop"""
        try:
            await self.initialize()
            
            self.setup_scheduler()
            self.setup_signal_handlers()
            
            self.running = True
            self.scheduler.start()
            
            logger.info("=" * 60)
            logger.info("Monitoring daemon started successfully")
            logger.info(f"Scan interval: {self.config.scan_interval_minutes} minutes")
            logger.info(f"Max concurrent brands: {self.config.max_concurrent_brands}")
            logger.info(f"Circuit breaker: {'enabled' if self.config.circuit_breaker_enabled else 'disabled'}")
            logger.info(f"Alerting: {'configured' if self.config.slack_webhook_url else 'not configured'}")
            logger.info("=" * 60)
            
            logger.info("Running initial scan...")
            await self.scan_job()
            
            await self.shutdown_event.wait()
            
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            await self.shutdown()
        except Exception as e:
            logger.critical(f"Fatal error in daemon: {e}", exc_info=True)
            await self.shutdown()
            raise
