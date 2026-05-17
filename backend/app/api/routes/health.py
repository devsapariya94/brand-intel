"""System health API routes"""
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone, timedelta
import time
from typing import Optional

from ..dependencies import get_database, get_orchestrator, get_circuit_breaker, get_dlq
from ..models.responses import (
    DetailedHealthResponse,
    MetricsResponse,
    ComponentHealth,
    DLQHealth,
    CircuitBreakerState
)
from ...monitors.orchestrator import MonitorOrchestrator
from ...daemon.circuit_breaker import CircuitBreaker
from ...daemon.dlq import DeadLetterQueue

router = APIRouter(prefix="/health", tags=["health"])


def get_startup_time() -> float:
    """Get the startup time from app state"""
    from ..main import app
    return getattr(app.state, 'startup_time', time.time())


@router.get("")
async def basic_health_check():
    """Basic health check"""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}


@router.get("/detailed", response_model=DetailedHealthResponse)
async def get_detailed_health(
    db: AsyncIOMotorDatabase = Depends(get_database),
    orchestrator: MonitorOrchestrator = Depends(get_orchestrator),
    circuit_breaker: Optional[CircuitBreaker] = Depends(get_circuit_breaker),
    dlq: Optional[DeadLetterQueue] = Depends(get_dlq)
):
    """Get detailed system health"""
    # Check database
    try:
        await db.command("ping")
        db_health = ComponentHealth(
            status="healthy",
            available=True,
            last_check=datetime.now(timezone.utc)
        )
    except Exception as e:
        db_health = ComponentHealth(
            status="unhealthy",
            available=False,
            last_check=datetime.now(timezone.utc),
            error=str(e)
        )
    
    # Check monitors
    monitors_health = {}
    for monitor in orchestrator.monitors:
        monitor_type = monitor.name.lower().replace("monitor", "")
        try:
            is_available = await monitor.is_available()
            monitors_health[monitor_type] = ComponentHealth(
                status="healthy" if is_available else "unhealthy",
                available=is_available,
                last_check=datetime.now(timezone.utc)
            )
        except Exception as e:
            monitors_health[monitor_type] = ComponentHealth(
                status="unhealthy",
                available=False,
                last_check=datetime.now(timezone.utc),
                error=str(e)
            )
    
    # Circuit breaker states
    cb_states = {}
    if circuit_breaker:
        cb_stats = circuit_breaker.get_stats()
        for monitor_type, stats in cb_stats.items():
            cb_states[monitor_type] = CircuitBreakerState(
                state=stats["state"],
                failure_count=stats["failure_count"],
                last_failure=stats.get("last_failure_time"),
                next_retry=stats.get("next_retry_time")
            )
    
    # DLQ health
    dlq_health = DLQHealth(pending=0, failed=0, retrying=0)
    if dlq:
        dlq_stats = await dlq.get_stats()
        dlq_health = DLQHealth(
            pending=dlq_stats.get("pending", 0),
            failed=dlq_stats.get("failed", 0),
            retrying=dlq_stats.get("retrying", 0)
        )
    
    # Enrichment health (placeholder)
    enrichment_health = ComponentHealth(
        status="healthy",
        available=True,
        last_check=datetime.now(timezone.utc)
    )
    
    # Overall status
    overall_status = "healthy"
    if db_health.status == "unhealthy":
        overall_status = "unhealthy"
    elif any(m.status == "unhealthy" for m in monitors_health.values()):
        overall_status = "degraded"
    
    # Get last scan
    last_scan_run = await db.monitor_runs.find_one({}, sort=[("started_at", -1)])
    
    return DetailedHealthResponse(
        status=overall_status,
        database=db_health,
        monitors=monitors_health,
        circuit_breaker=cb_states,
        dlq=dlq_health,
        enrichment=enrichment_health,
        uptime_seconds=time.time() - get_startup_time(),
        last_scan=last_scan_run["started_at"] if last_scan_run else None
    )


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    db: AsyncIOMotorDatabase = Depends(get_database),
    dlq: Optional[DeadLetterQueue] = Depends(get_dlq)
):
    """Get system metrics"""
    # Count brands
    total_brands = await db.brands.count_documents({})
    active_brands = await db.brands.count_documents({"active": True})
    
    # Count hits
    total_hits = await db.raw_hits.count_documents({})
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    hits_last_24h = await db.raw_hits.count_documents({"detected_at": {"$gte": yesterday}})
    
    # Monitor runs
    monitor_runs_last_24h = await db.monitor_runs.count_documents({"started_at": {"$gte": yesterday}})
    
    # Success rate
    total_runs = await db.monitor_runs.count_documents({})
    successful_runs = await db.monitor_runs.count_documents({"status": "completed"})
    success_rate = successful_runs / total_runs if total_runs > 0 else 0.0
    
    # Average execution time
    recent_runs = await db.monitor_runs.find(
        {"status": "completed"},
        sort=[("started_at", -1)],
        limit=100
    ).to_list(length=100)
    avg_execution_time = sum(r.get("execution_time_seconds", 0) for r in recent_runs) / len(recent_runs) if recent_runs else 0.0
    
    # DLQ pending
    dlq_pending = 0
    if dlq:
        dlq_stats = await dlq.get_stats()
        dlq_pending = dlq_stats.get("pending", 0)

    enrichment_queue = await db.raw_hits.count_documents({"processing_status": "pending"})
    
    return MetricsResponse(
        total_brands=total_brands,
        active_brands=active_brands,
        total_hits=total_hits,
        hits_last_24h=hits_last_24h,
        monitor_runs_last_24h=monitor_runs_last_24h,
        success_rate=success_rate,
        avg_execution_time=avg_execution_time,
        dlq_pending=dlq_pending,
        enrichment_queue=enrichment_queue
    )


@router.get("/circuit-breaker")
async def get_circuit_breaker_status(
    circuit_breaker: Optional[CircuitBreaker] = Depends(get_circuit_breaker)
):
    """Get circuit breaker status"""
    if not circuit_breaker:
        return {"enabled": False}
    
    stats = circuit_breaker.get_stats()
    return {"enabled": True, "monitors": stats}

# Made with Bob
