"""Monitor control and status API routes"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timezone
import uuid

from ..dependencies import get_database, get_orchestrator, get_circuit_breaker
from ..models.requests import TriggerMonitorRequest
from ..models.responses import (
    MonitorsStatusResponse,
    MonitorStatus,
    CircuitBreakerState,
    ScanResultResponse,
    MonitorResultResponse,
    MonitorRunResponse,
    MonitorHealthResponse
)
from ...monitors.orchestrator import MonitorOrchestrator
from ...daemon.circuit_breaker import CircuitBreaker

router = APIRouter(prefix="/monitors", tags=["monitors"])


@router.get("/status", response_model=MonitorsStatusResponse)
async def get_monitors_status(
    db: AsyncIOMotorDatabase = Depends(get_database),
    orchestrator: MonitorOrchestrator = Depends(get_orchestrator),
    circuit_breaker: Optional[CircuitBreaker] = Depends(get_circuit_breaker)
):
    """Get status of all monitors"""
    monitors_status = []
    
    for monitor in orchestrator.monitors:
        monitor_type = monitor.name.lower().replace("monitor", "")
        
        # Get recent runs
        recent_runs = await db.monitor_runs.find(
            {"monitor_type": monitor_type},
            sort=[("started_at", -1)],
            limit=10
        ).to_list(length=10)
        
        # Calculate success rate
        if recent_runs:
            successful = sum(1 for r in recent_runs if r.get("status") == "completed")
            success_rate = successful / len(recent_runs)
            avg_time = sum(r.get("execution_time_seconds", 0) for r in recent_runs) / len(recent_runs)
            last_run = recent_runs[0].get("started_at")
        else:
            success_rate = 0.0
            avg_time = 0.0
            last_run = None
        
        # Get rate limit status
        rate_status = monitor.get_rate_limit_status()
        
        # Check availability
        is_available = await monitor.is_available()
        if not is_available:
            status = "unhealthy"
        elif not recent_runs:
            status = "unknown"
        elif success_rate >= 0.8:
            status = "healthy"
        else:
            status = "degraded"
        
        monitors_status.append(MonitorStatus(
            name=monitor.name,
            type=monitor_type,
            status=status,
            enabled=True,
            available=is_available,
            rate_limit_remaining=rate_status.get("remaining", 0),
            rate_limit_total=rate_status.get("limit", 60),
            last_run=last_run,
            success_rate=success_rate,
            avg_execution_time=avg_time
        ))
    
    # Get circuit breaker states
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
    
    # Get last and next scan times
    last_scan_run = await db.monitor_runs.find_one(
        {},
        sort=[("started_at", -1)]
    )
    
    return MonitorsStatusResponse(
        monitors=monitors_status,
        circuit_breaker=cb_states,
        last_scan=last_scan_run["started_at"] if last_scan_run else None,
        next_scan=None  # Would need scheduler integration
    )


@router.post("/trigger", response_model=ScanResultResponse)
async def trigger_all_monitors(
    request: TriggerMonitorRequest,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_database),
    orchestrator: MonitorOrchestrator = Depends(get_orchestrator)
):
    """Trigger all monitors for all brands or specific brand"""
    scan_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)
    
    if request.brand_id:
        # Trigger for specific brand
        try:
            brand_oid = ObjectId(request.brand_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid brand ID format")
        
        brand = await db.brands.find_one({"_id": brand_oid})
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        
        if not brand.get("active", False):
            raise HTTPException(status_code=400, detail="Brand is not active")
        
        result = await orchestrator.run_all_monitors(brand)
        
        completed_at = datetime.now(timezone.utc)
        
        return ScanResultResponse(
            scan_id=scan_id,
            brands_scanned=1,
            successful_scans=1 if not result.get("errors") else 0,
            failed_scans=1 if result.get("errors") else 0,
            total_hits_found=result["total_hits_found"],
            total_hits_stored=result["total_hits_stored"],
            total_hits_enriched=result.get("total_hits_enriched", 0),
            results=[MonitorResultResponse(
                monitor_type="all",
                brand_id=str(brand["_id"]),
                brand_name=brand["name"],
                hits_found=result["total_hits_found"],
                hits_stored=result["total_hits_stored"],
                hits_enriched=result.get("total_hits_enriched", 0),
                execution_time_seconds=(completed_at - started_at).total_seconds(),
                status="completed" if not result.get("errors") else "failed",
                started_at=started_at,
                completed_at=completed_at,
                error=str(result.get("errors")) if result.get("errors") else None
            )],
            started_at=started_at,
            completed_at=completed_at
        )
    else:
        # Trigger for all active brands
        result = await orchestrator.run_scheduled_scan(max_concurrent=5)
        
        completed_at = datetime.now(timezone.utc)
        
        # Convert results to response format
        monitor_results = []
        for brand_result in result.get("results", []):
            if isinstance(brand_result, dict):
                monitor_results.append(MonitorResultResponse(
                    monitor_type="all",
                    brand_id=brand_result.get("brand_id", ""),
                    brand_name="",  # Would need to fetch
                    hits_found=brand_result.get("total_hits_found", 0),
                    hits_stored=brand_result.get("total_hits_stored", 0),
                    hits_enriched=brand_result.get("total_hits_enriched", 0),
                    execution_time_seconds=(completed_at - started_at).total_seconds(),
                    status="completed",
                    started_at=started_at,
                    completed_at=completed_at
                ))
        
        return ScanResultResponse(
            scan_id=scan_id,
            brands_scanned=result["brands_scanned"],
            successful_scans=result["successful_scans"],
            failed_scans=result["failed_scans"],
            total_hits_found=sum(r.hits_found for r in monitor_results),
            total_hits_stored=sum(r.hits_stored for r in monitor_results),
            total_hits_enriched=sum(r.hits_enriched for r in monitor_results),
            results=monitor_results,
            started_at=started_at,
            completed_at=completed_at
        )


@router.post("/{monitor_type}/trigger", response_model=MonitorResultResponse)
async def trigger_specific_monitor(
    monitor_type: str,
    request: TriggerMonitorRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    orchestrator: MonitorOrchestrator = Depends(get_orchestrator)
):
    """Trigger specific monitor for a brand"""
    if not request.brand_id:
        raise HTTPException(status_code=400, detail="brand_id is required for specific monitor trigger")
    
    try:
        brand_oid = ObjectId(request.brand_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid brand ID format")
    
    brand = await db.brands.find_one({"_id": brand_oid})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    if not brand.get("active", False):
        raise HTTPException(status_code=400, detail="Brand is not active")
    
    # Find the specific monitor
    monitor = None
    for m in orchestrator.monitors:
        if m.name.lower().replace("monitor", "") == monitor_type.lower():
            monitor = m
            break
    
    if not monitor:
        raise HTTPException(status_code=404, detail=f"Monitor type '{monitor_type}' not found")
    
    started_at = datetime.now(timezone.utc)
    
    # Run the specific monitor
    result = await orchestrator._run_single_monitor(monitor, brand)
    
    completed_at = datetime.now(timezone.utc)
    
    return MonitorResultResponse(
        monitor_type=monitor_type,
        brand_id=str(brand["_id"]),
        brand_name=brand["name"],
        hits_found=result.get("hits_found", 0),
        hits_stored=result.get("hits_stored", 0),
        hits_enriched=result.get("hits_enriched", 0),
        execution_time_seconds=(completed_at - started_at).total_seconds(),
        status="completed" if not result.get("skipped") else "skipped",
        started_at=started_at,
        completed_at=completed_at
    )


@router.get("/runs", response_model=List[MonitorRunResponse])
async def get_monitor_runs(
    limit: int = 50,
    status: Optional[str] = None,
    monitor_type: Optional[str] = None,
    brand_id: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get monitor run history"""
    query = {}
    if status:
        query["status"] = status
    if monitor_type:
        query["monitor_type"] = monitor_type
    if brand_id:
        try:
            query["brand_id"] = ObjectId(brand_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid brand ID format")
    
    runs = await db.monitor_runs.find(query, sort=[("started_at", -1)], limit=limit).to_list(length=limit)
    
    # Get brand names
    result = []
    for run in runs:
        brand_name = None
        if run.get("brand_id"):
            brand = await db.brands.find_one({"_id": run["brand_id"]})
            if brand:
                brand_name = brand["name"]
        
        result.append(MonitorRunResponse(
            id=str(run["_id"]),
            monitor_type=run["monitor_type"],
            brand_id=str(run["brand_id"]) if run.get("brand_id") else None,
            brand_name=brand_name,
            started_at=run["started_at"],
            completed_at=run.get("completed_at"),
            status=run["status"],
            hits_found=run.get("hits_found", 0),
            hits_stored=run.get("hits_stored", 0),
            error_message=run.get("error_message"),
            execution_time_seconds=run.get("execution_time_seconds", 0.0),
            api_calls_made=run.get("api_calls_made", 0)
        ))
    
    return result


@router.get("/runs/{run_id}", response_model=MonitorRunResponse)
async def get_monitor_run(
    run_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get specific monitor run details"""
    try:
        run = await db.monitor_runs.find_one({"_id": ObjectId(run_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid run ID format")
    
    if not run:
        raise HTTPException(status_code=404, detail="Monitor run not found")
    
    brand_name = None
    if run.get("brand_id"):
        brand = await db.brands.find_one({"_id": run["brand_id"]})
        if brand:
            brand_name = brand["name"]
    
    return MonitorRunResponse(
        id=str(run["_id"]),
        monitor_type=run["monitor_type"],
        brand_id=str(run["brand_id"]) if run.get("brand_id") else None,
        brand_name=brand_name,
        started_at=run["started_at"],
        completed_at=run.get("completed_at"),
        status=run["status"],
        hits_found=run.get("hits_found", 0),
        hits_stored=run.get("hits_stored", 0),
        error_message=run.get("error_message"),
        execution_time_seconds=run.get("execution_time_seconds", 0.0),
        api_calls_made=run.get("api_calls_made", 0)
    )


@router.get("/{monitor_type}/health", response_model=MonitorHealthResponse)
async def get_monitor_health(
    monitor_type: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    orchestrator: MonitorOrchestrator = Depends(get_orchestrator),
    circuit_breaker: Optional[CircuitBreaker] = Depends(get_circuit_breaker)
):
    """Get health status for specific monitor"""
    # Find the monitor
    monitor = None
    for m in orchestrator.monitors:
        if m.name.lower().replace("monitor", "") == monitor_type.lower():
            monitor = m
            break
    
    if not monitor:
        raise HTTPException(status_code=404, detail=f"Monitor type '{monitor_type}' not found")
    
    # Get run statistics
    total_runs = await db.monitor_runs.count_documents({"monitor_type": monitor_type})
    successful_runs = await db.monitor_runs.count_documents({"monitor_type": monitor_type, "status": "completed"})
    failed_runs = await db.monitor_runs.count_documents({"monitor_type": monitor_type, "status": "failed"})
    
    success_rate = successful_runs / total_runs if total_runs > 0 else 0.0
    
    # Get average execution time
    recent_runs = await db.monitor_runs.find(
        {"monitor_type": monitor_type, "status": "completed"},
        sort=[("started_at", -1)],
        limit=10
    ).to_list(length=10)
    
    avg_time = sum(r.get("execution_time_seconds", 0) for r in recent_runs) / len(recent_runs) if recent_runs else 0.0
    
    # Get last run
    last_run_doc = await db.monitor_runs.find_one(
        {"monitor_type": monitor_type},
        sort=[("started_at", -1)]
    )
    last_run = last_run_doc["started_at"] if last_run_doc else None
    
    # Get last error
    last_error_doc = await db.monitor_runs.find_one(
        {"monitor_type": monitor_type, "status": "failed"},
        sort=[("started_at", -1)]
    )
    last_error = last_error_doc.get("error_message") if last_error_doc else None
    
    # Get circuit breaker state
    cb_state = "closed"
    if circuit_breaker:
        cb_stats = circuit_breaker.get_stats()
        if monitor_type in cb_stats:
            cb_state = cb_stats[monitor_type]["state"]
    
    # Check availability
    is_available = await monitor.is_available()
    
    status = "healthy"
    if not is_available or cb_state == "open":
        status = "unhealthy"
    elif cb_state == "half_open" or success_rate < 0.8:
        status = "degraded"
    
    return MonitorHealthResponse(
        monitor_type=monitor_type,
        status=status,
        available=is_available,
        total_runs=total_runs,
        successful_runs=successful_runs,
        failed_runs=failed_runs,
        success_rate=success_rate,
        avg_execution_time=avg_time,
        last_run=last_run,
        last_error=last_error,
        circuit_breaker_state=cb_state
    )

# Made with Bob
