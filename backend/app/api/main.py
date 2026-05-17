"""FastAPI application for Brand Intel monitoring system"""
import logging
import os
import time
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

# Load .env file
env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(env_path)

from .routes import (
    brands_router,
    monitors_router,
    hits_router,
    health_router,
    enrichment_router,
    admin_router
)
from . import dependencies
from ..daemon.config import DaemonConfig
from ..monitors.orchestrator import MonitorOrchestrator
from ..monitors.storage import RawHitStorage
from ..monitors.detector import KeywordMatcher
from ..monitors.base import MonitorConfig
from ..daemon.circuit_breaker import CircuitBreaker
from ..daemon.dlq import DeadLetterQueue
from ..daemon.alerting import AlertManager
from ..enrichment.service import EnrichmentService
from ..models.schemas import create_indexes
from ..models.enrichment_schemas import create_enrichment_indexes

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    startup_time = time.time()
    logger.info("Starting Brand Intel API...")
    
    # Load configuration
    config = DaemonConfig.from_env()
    dependencies.set_config(config)
    
    # Initialize database
    db_client = AsyncIOMotorClient(config.mongodb_uri)
    dependencies.set_db_client(db_client)
    
    # Test database connection
    try:
        await db_client.admin.command('ping')
        await create_indexes(db_client.brand_intel)
        await create_enrichment_indexes(db_client.brand_intel)
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise
    
    # Initialize circuit breaker
    circuit_breaker = None
    if config.circuit_breaker_enabled:
        circuit_breaker = CircuitBreaker(
            failure_threshold=config.circuit_breaker_failure_threshold,
            timeout_seconds=config.circuit_breaker_timeout_seconds
        )
        dependencies.set_circuit_breaker(circuit_breaker)
        logger.info("Circuit breaker initialized")
    
    # Initialize DLQ
    dlq = None
    if config.dlq_enabled:
        dlq = DeadLetterQueue(
            db_client=db_client,
            max_retries=config.dlq_max_retries
        )
        dependencies.set_dlq(dlq)
        logger.info("DLQ initialized")
    
    # Initialize alert manager
    alert_manager = AlertManager(
        db_client=db_client,
        slack_webhook_url=config.slack_webhook_url,
        alert_email=config.alert_email,
        failure_threshold=config.alert_failure_threshold
    )
    await alert_manager.initialize()
    logger.info("Alert manager initialized")
    
    # Initialize enrichment service
    enrichment_svc = None
    if config.enrichment_enabled and (config.llm_api_key or config.anthropic_api_key):
        try:
            enrichment_svc = EnrichmentService(db_client, config, alert_manager=alert_manager)
            dependencies.set_enrichment_service(enrichment_svc)
            logger.info("Enrichment service initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize enrichment service: {e}")

    # Initialize monitors
    monitors = _create_monitors(config, db_client)
    
    # Initialize orchestrator
    storage = RawHitStorage(db_client)
    matcher = KeywordMatcher()
    orchestrator = MonitorOrchestrator(
        monitors=monitors,
        storage=storage,
        matcher=matcher,
        db_client=db_client,
        circuit_breaker=circuit_breaker if config.circuit_breaker_enabled else None,
        dlq=dlq if config.dlq_enabled else None,
        enrichment_service=enrichment_svc
    )
    dependencies.set_orchestrator(orchestrator)
    logger.info("Orchestrator initialized")
    
    logger.info("Brand Intel API started successfully")
    
    app.state.startup_time = startup_time
    
    yield
    
    # Shutdown
    logger.info("Shutting down Brand Intel API...")
    
    if orchestrator:
        await orchestrator.close_all()
    
    if alert_manager:
        await alert_manager.close()
    
    if db_client:
        db_client.close()
    
    logger.info("Brand Intel API shutdown complete")


def _create_monitors(config: DaemonConfig, db_client=None):
    """Create monitor instances"""
    from ..monitors.github import GitHubMonitor
    from ..monitors.hackernews import HackerNewsMonitor
    from ..monitors.ransomware import RansomwareMonitor
    from ..monitors.xposedornot import XposedOrNotMonitor
    from ..monitors.intelx import IntelXMonitor
    
    monitors = []
    
    # GitHub
    if config.github_token:
        github_config = MonitorConfig(
            enabled=True,
            rate_limit_per_minute=config.github_rate_limit,
            timeout_seconds=config.monitor_timeout_seconds,
            max_retries=config.max_retries
        )
        monitors.append(GitHubMonitor(github_config, github_token=config.github_token))
        logger.info("GitHub monitor created")
    
    # Hacker News (free, no API key)
    hn_config = MonitorConfig(
        enabled=True,
        rate_limit_per_minute=60,
        timeout_seconds=config.monitor_timeout_seconds,
        max_retries=config.max_retries
    )
    monitors.append(HackerNewsMonitor(hn_config))
    logger.info("HackerNews monitor created")
    
    # Ransomware.live (free, no API key)
    ransom_config = MonitorConfig(
        enabled=True,
        rate_limit_per_minute=1,
        timeout_seconds=config.monitor_timeout_seconds,
        max_retries=config.max_retries
    )
    monitors.append(RansomwareMonitor(ransom_config))
    logger.info("Ransomware monitor created")

    # XposedOrNot (free, no API key for basic checks)
    xon_config = MonitorConfig(
        enabled=True,
        rate_limit_per_minute=30,
        timeout_seconds=config.monitor_timeout_seconds,
        max_retries=config.max_retries
    )
    monitors.append(XposedOrNotMonitor(xon_config))
    logger.info("XposedOrNot monitor created")

    # Intelligence X (free tier, requires API key)
    if config.intelx_api_key:
        intelx_config = MonitorConfig(
            enabled=True,
            rate_limit_per_minute=10,
            timeout_seconds=config.monitor_timeout_seconds,
            max_retries=config.max_retries
        )
        monitors.append(IntelXMonitor(intelx_config, api_key=config.intelx_api_key))
        logger.info("IntelX monitor created")
    
    logger.info(f"Created {len(monitors)} monitors")
    return monitors


# Create FastAPI app
app = FastAPI(
    title="Brand Intel API",
    description="API for Brand Intel monitoring system",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(brands_router, prefix="/api/v1")
app.include_router(monitors_router, prefix="/api/v1")
app.include_router(hits_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(enrichment_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Brand Intel API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/v1")
async def api_root():
    """API root endpoint"""
    return {
        "message": "Brand Intel API v1",
        "endpoints": {
            "brands": "/api/v1/brands",
            "monitors": "/api/v1/monitors",
            "hits": "/api/v1/hits",
            "health": "/api/v1/health",
            "enrichment": "/api/v1/enrichment",
            "admin": "/api/v1/admin"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Made with Bob
