"""FastAPI application for Brand Intel monitoring system"""
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

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
from ..enrichment.service import EnrichmentService

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
        dlq=dlq if config.dlq_enabled else None
    )
    dependencies.set_orchestrator(orchestrator)
    logger.info("Orchestrator initialized")
    
    # Initialize enrichment service
    enrichment_svc = None
    if config.enrichment_enabled and (config.llm_api_key or config.anthropic_api_key):
        try:
            enrichment_svc = EnrichmentService(db_client, config)
            dependencies.set_enrichment_service(enrichment_svc)
            logger.info("Enrichment service initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize enrichment service: {e}")
    
    logger.info("Brand Intel API started successfully")
    
    app.state.startup_time = startup_time
    
    yield
    
    # Shutdown
    logger.info("Shutting down Brand Intel API...")
    
    if orchestrator:
        await orchestrator.close_all()
    
    if db_client:
        db_client.close()
    
    logger.info("Brand Intel API shutdown complete")


def _create_monitors(config: DaemonConfig, db_client=None):
    """Create monitor instances"""
    from ..monitors.pastebin import PastebinMonitor
    from ..monitors.github import GitHubMonitor
    from ..monitors.reddit import RedditMonitor
    from ..monitors.hibp import HIBPMonitor
    
    monitors = []
    
    # Pastebin
    if config.pastebin_api_key:
        pastebin_config = MonitorConfig(
            enabled=True,
            rate_limit_per_minute=config.pastebin_rate_limit,
            timeout_seconds=config.monitor_timeout_seconds,
            max_retries=config.max_retries
        )
        monitors.append(PastebinMonitor(pastebin_config, api_key=config.pastebin_api_key))
        logger.info("Pastebin monitor created")
    
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
    
    # Reddit
    if config.reddit_client_id and config.reddit_client_secret:
        reddit_config = MonitorConfig(
            enabled=True,
            rate_limit_per_minute=config.reddit_rate_limit,
            timeout_seconds=config.monitor_timeout_seconds,
            max_retries=config.max_retries
        )
        monitors.append(RedditMonitor(
            reddit_config,
            client_id=config.reddit_client_id,
            client_secret=config.reddit_client_secret
        ))
        logger.info("Reddit monitor created")
    
    # HIBP
    if config.hibp_api_key:
        hibp_config = MonitorConfig(
            enabled=True,
            rate_limit_per_minute=config.hibp_rate_limit,
            timeout_seconds=config.monitor_timeout_seconds,
            max_retries=config.max_retries
        )
        monitors.append(HIBPMonitor(
            hibp_config,
            api_key=config.hibp_api_key,
            db_client=db_client
        ))
        logger.info("HIBP monitor created")
    
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
