"""Health check HTTP endpoint for daemon monitoring"""
import asyncio
import logging
from typing import Optional
from datetime import datetime, timezone
from aiohttp import web
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)


class HealthCheckServer:
    """
    Simple HTTP server for health checks.
    Runs on a separate port from the main daemon.
    """
    
    def __init__(
        self,
        db_client: AsyncIOMotorClient,
        port: int = 8001
    ):
        self.db_client = db_client
        self.port = port
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
    
    async def health_handler(self, request: web.Request) -> web.Response:
        """
        Health check endpoint.
        Returns 200 if healthy, 503 if unhealthy.
        """
        try:
            # Check database connection
            await self.db_client.admin.command('ping')
            db_status = "healthy"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            db_status = "unhealthy"
            return web.json_response(
                {
                    "status": "unhealthy",
                    "database": db_status,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                status=503
            )
        
        # Get basic stats
        try:
            db = self.db_client.brand_intel
            active_brands = await db.brands.count_documents({"active": True})
            recent_runs = await db.monitor_runs.count_documents({})
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            active_brands = 0
            recent_runs = 0
        
        return web.json_response({
            "status": "healthy",
            "database": db_status,
            "active_brands": active_brands,
            "total_runs": recent_runs,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def readiness_handler(self, request: web.Request) -> web.Response:
        """
        Readiness check endpoint.
        Returns 200 if ready to accept traffic.
        """
        try:
            # Check if database is accessible
            await self.db_client.admin.command('ping')
            
            return web.json_response({
                "status": "ready",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            return web.json_response(
                {
                    "status": "not_ready",
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                status=503
            )
    
    async def liveness_handler(self, request: web.Request) -> web.Response:
        """
        Liveness check endpoint.
        Returns 200 if daemon is alive.
        """
        return web.json_response({
            "status": "alive",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def stats_handler(self, request: web.Request) -> web.Response:
        """
        Statistics endpoint.
        Returns detailed daemon statistics.
        """
        try:
            db = self.db_client.brand_intel
            
            # Get counts
            total_brands = await db.brands.count_documents({})
            active_brands = await db.brands.count_documents({"active": True})
            total_runs = await db.monitor_runs.count_documents({})
            completed_runs = await db.monitor_runs.count_documents({"status": "completed"})
            failed_runs = await db.monitor_runs.count_documents({"status": "failed"})
            total_hits = await db.raw_hits.count_documents({})
            pending_hits = await db.raw_hits.count_documents({"processing_status": "pending"})
            
            # Get recent run
            recent_run = await db.monitor_runs.find_one(
                {},
                sort=[("started_at", -1)]
            )
            
            last_run_time = recent_run["started_at"].isoformat() if recent_run else None
            
            return web.json_response({
                "brands": {
                    "total": total_brands,
                    "active": active_brands
                },
                "runs": {
                    "total": total_runs,
                    "completed": completed_runs,
                    "failed": failed_runs,
                    "success_rate": completed_runs / total_runs if total_runs > 0 else 0
                },
                "hits": {
                    "total": total_hits,
                    "pending": pending_hits
                },
                "last_run": last_run_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return web.json_response(
                {"error": str(e)},
                status=500
            )
    
    async def start(self):
        """Start health check server"""
        self.app = web.Application()
        
        # Add routes
        self.app.router.add_get('/health', self.health_handler)
        self.app.router.add_get('/ready', self.readiness_handler)
        self.app.router.add_get('/alive', self.liveness_handler)
        self.app.router.add_get('/stats', self.stats_handler)
        
        # Start server
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await self.site.start()
        
        logger.info(f"Health check server started on port {self.port}")
        logger.info(f"  - Health: http://localhost:{self.port}/health")
        logger.info(f"  - Ready: http://localhost:{self.port}/ready")
        logger.info(f"  - Alive: http://localhost:{self.port}/alive")
        logger.info(f"  - Stats: http://localhost:{self.port}/stats")
    
    async def stop(self):
        """Stop health check server"""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("Health check server stopped")

# Made with Bob
