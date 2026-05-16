"""Main monitoring daemon with APScheduler"""
import asyncio
import signal
import logging
from typing import Optional
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from motor.motor_asyncio import AsyncIOMotorClient

from .config import DaemonConfig
from .circuit_breaker import CircuitBreaker
from .alerting import AlertManager
from .dlq import DeadLetterQueue
from ..monitors.orchestrator import MonitorOrchestrator
from ..monitors.storage import RawHitStorage
from ..monitors.detector import KeywordMatcher
from ..monitors.base import MonitorConfig

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
        self.running = False
        self.shutdown_event = asyncio.Event()
    
    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing monitoring daemon...")
        
        # Initialize database connection
        self.db_client = AsyncIOMotorClient(self.config.mongodb_uri)
        
        # Test database connection
        try:
            await self.db_client.admin.command('ping')
            logger.info("Database connection successful")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
        
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
        monitors = await self._create_monitors()
        
        # Initialize storage and matcher
        storage = RawHitStorage(self.db_client)
        matcher = KeywordMatcher()
        
        # Initialize orchestrator
        self.orchestrator = MonitorOrchestrator(
            monitors=monitors,
            storage=storage,
            matcher=matcher,
            db_client=self.db_client
        )
        logger.info("Monitor orchestrator initialized")
        
        # Validate configuration
        warnings = self.config.validate_config()
        for warning in warnings:
            logger.warning(f"Configuration warning: {warning}")
        
        logger.info("Daemon initialization complete")
    
    async def _create_monitors(self):
        """Create monitor instances with configuration"""
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
        monitors.append(PastebinMonitor(pastebin_config))
        
        # GitHub
        github_config = MonitorConfig(
            enabled=True,
            rate_limit_per_minute=self.config.github_rate_limit,
            timeout_seconds=self.config.monitor_timeout_seconds,
            max_retries=self.config.max_retries
        )
        monitors.append(GitHubMonitor(github_config))
        
        # Reddit
        reddit_config = MonitorConfig(
            enabled=True,
            rate_limit_per_minute=self.config.reddit_rate_limit,
            timeout_seconds=self.config.monitor_timeout_seconds,
            max_retries=self.config.max_retries
        )
        monitors.append(RedditMonitor(reddit_config))
        
        # HIBP
        hibp_config = MonitorConfig(
            enabled=True,
            rate_limit_per_minute=self.config.hibp_rate_limit,
            timeout_seconds=self.config.monitor_timeout_seconds,
            max_retries=self.config.max_retries
        )
        monitors.append(HIBPMonitor(hibp_config))
        
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
                if error_rate > 0.5:  # More than 50% failures
                    await self.alert_manager.alert_high_error_rate(error_rate)
            
            # Process circuit breaker states
            if self.circuit_breaker:
                cb_stats = self.circuit_breaker.get_stats()
                for monitor_name, stats in cb_stats.items():
                    if stats['state'] == 'open':
                        await self.alert_manager.alert_monitor_down(
                            monitor_name=monitor_name,
                            error=f"Circuit breaker open",
                            failure_count=stats['failure_count']
                        )
                    elif stats['state'] == 'closed' and stats['failure_count'] == 0:
                        # Monitor recovered
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
            
            # Get pending items
            pending_items = await self.dlq.get_pending_items(
                limit=50,
                max_retry_count=self.config.dlq_max_retries
            )
            
            if not pending_items:
                logger.debug("No pending DLQ items")
                return
            
            logger.info(f"Found {len(pending_items)} pending DLQ items")
            
            # TODO: Implement retry logic with actual processor
            # For now, just log
            for item in pending_items:
                logger.debug(f"DLQ item {item['_id']}: retry_count={item['retry_count']}")
            
        except Exception as e:
            logger.error(f"DLQ retry job failed: {e}", exc_info=True)
    
    async def health_check_job(self):
        """Periodic health check"""
        try:
            # Check for stale monitors (no runs in 2 hours)
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
    
    def setup_scheduler(self):
        """Configure scheduled jobs"""
        # Main scan job
        self.scheduler.add_job(
            self.scan_job,
            trigger=IntervalTrigger(minutes=self.config.scan_interval_minutes),
            id='monitor_scan',
            name='Monitor all brands',
            replace_existing=True,
            max_instances=1,  # Prevent overlapping runs
            coalesce=True  # If missed, run once
        )
        logger.info(f"Scheduled scan job every {self.config.scan_interval_minutes} minutes")
        
        # DLQ retry job (every 30 minutes)
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
        
        # Health check job (every hour)
        self.scheduler.add_job(
            self.health_check_job,
            trigger=IntervalTrigger(hours=1),
            id='health_check',
            name='Health check',
            replace_existing=True,
            max_instances=1
        )
        logger.info("Scheduled health check job every hour")
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown on signals"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        logger.info("Signal handlers configured")
    
    async def shutdown(self):
        """Graceful shutdown"""
        if not self.running:
            return
        
        logger.info("=" * 60)
        logger.info("Shutting down daemon...")
        logger.info("=" * 60)
        
        self.running = False
        
        # Stop scheduler
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")
        
        # Close orchestrator resources
        if self.orchestrator:
            await self.orchestrator.close_all()
            logger.info("Monitor resources closed")
        
        # Close alert manager
        if self.alert_manager:
            await self.alert_manager.close()
            logger.info("Alert manager closed")
        
        # Close database connection
        if self.db_client:
            self.db_client.close()
            logger.info("Database connection closed")
        
        logger.info("Daemon shutdown complete")
        self.shutdown_event.set()
    
    async def run(self):
        """Main daemon loop"""
        try:
            # Initialize
            await self.initialize()
            
            # Setup scheduler and signals
            self.setup_scheduler()
            self.setup_signal_handlers()
            
            # Start scheduler
            self.running = True
            self.scheduler.start()
            
            logger.info("=" * 60)
            logger.info("Monitoring daemon started successfully")
            logger.info(f"Scan interval: {self.config.scan_interval_minutes} minutes")
            logger.info(f"Max concurrent brands: {self.config.max_concurrent_brands}")
            logger.info(f"Circuit breaker: {'enabled' if self.config.circuit_breaker_enabled else 'disabled'}")
            logger.info(f"Alerting: {'configured' if self.config.slack_webhook_url else 'not configured'}")
            logger.info("=" * 60)
            
            # Run first scan immediately
            logger.info("Running initial scan...")
            await self.scan_job()
            
            # Keep running until shutdown
            await self.shutdown_event.wait()
            
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            await self.shutdown()
        except Exception as e:
            logger.critical(f"Fatal error in daemon: {e}", exc_info=True)
            await self.shutdown()
            raise

# Made with Bob
