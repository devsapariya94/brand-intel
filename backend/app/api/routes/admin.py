"""Admin operations API routes"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timezone

from ..dependencies import get_database, get_dlq, get_circuit_breaker
from ..models.requests import CircuitBreakerResetRequest
from ..models.responses import DLQItemResponse, LogEntry
from ...daemon.dlq import DeadLetterQueue
from ...daemon.circuit_breaker import CircuitBreaker

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dlq", response_model=List[DLQItemResponse])
async def get_dlq_items(
    limit: int = Query(50, le=200),
    db: AsyncIOMotorDatabase = Depends(get_database),
    dlq: Optional[DeadLetterQueue] = Depends(get_dlq)
):
    """Get DLQ items"""
    if not dlq:
        return []
    
    items = await dlq.get_pending_items(limit=limit)
    
    result = []
    for item in items:
        brand = await db.brands.find_one({"_id": item.get("hit_data", {}).get("brand_id")})
        brand_name = brand["name"] if brand else "Unknown"
        
        result.append(DLQItemResponse(
            id=str(item["_id"]),
            brand_id=str(item.get("hit_data", {}).get("brand_id", "")),
            brand_name=brand_name,
            source=item.get("hit_data", {}).get("source", "unknown"),
            error=item.get("error", ""),
            retry_count=item.get("retry_count", 0),
            max_retries=item.get("max_retries", 3),
            created_at=item.get("created_at", datetime.now(timezone.utc)),
            last_retry=item.get("last_retry_at"),
            status=item.get("status", "pending")
        ))
    
    return result


@router.post("/dlq/{item_id}/retry")
async def retry_dlq_item(
    item_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    dlq: Optional[DeadLetterQueue] = Depends(get_dlq)
):
    """Retry a DLQ item"""
    if not dlq:
        raise HTTPException(status_code=503, detail="DLQ not available")
    
    try:
        from bson import ObjectId
        result = await dlq.retry_item(
            dlq_id=item_id,
            processor_func=lambda hit_data: _process_dlq_item_sync(db, hit_data)
        )
        return {"status": "retried", "item_id": item_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _process_dlq_item_sync(db, hit_data: dict):
    """Process a DLQ item by re-storing it"""
    from ..monitors.base import RawHit
    from ..monitors.detector import KeywordMatcher
    
    brand_id = hit_data.get("brand_id")
    if not brand_id:
        raise ValueError("DLQ item missing brand_id")
    
    brand = await db.brands.find_one({"_id": brand_id})
    if not brand:
        raise ValueError(f"Brand {brand_id} not found")
    
    raw_hit = RawHit(
        source=hit_data.get("source", "unknown"),
        source_url=hit_data.get("source_url", ""),
        raw_content=hit_data.get("raw_content", ""),
        metadata=hit_data.get("metadata", {}),
        detected_at=hit_data.get("detected_at")
    )
    
    matcher = KeywordMatcher()
    match_result = matcher.match(raw_hit.raw_content, brand)
    
    if not match_result.is_match():
        raise ValueError("Hit no longer matches brand keywords")
    
    from ..monitors.storage import RawHitStorage
    storage = RawHitStorage(db.client)
    await storage.store_hit(raw_hit, str(brand_id), match_result)


@router.delete("/dlq/{item_id}")
async def delete_dlq_item(
    item_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Remove a DLQ item"""
    try:
        result = await db.dlq.delete_one({"_id": ObjectId(item_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="DLQ item not found")
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/circuit-breaker/reset")
async def reset_circuit_breaker(
    request: CircuitBreakerResetRequest,
    circuit_breaker: Optional[CircuitBreaker] = Depends(get_circuit_breaker)
):
    """Reset circuit breaker for a monitor"""
    if not circuit_breaker:
        raise HTTPException(status_code=503, detail="Circuit breaker not available")
    
    circuit_breaker.reset(request.monitor_type)
    return {"status": "reset", "monitor_type": request.monitor_type}


@router.get("/logs", response_model=List[LogEntry])
async def get_logs(
    level: Optional[str] = None,
    limit: int = Query(100, le=1000),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get system logs"""
    # Placeholder - would need logging collection
    return []


@router.post("/cleanup")
async def trigger_cleanup(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Trigger cleanup jobs"""
    # Clean up old monitor runs
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    result = await db.monitor_runs.delete_many({"started_at": {"$lt": cutoff}})
    
    return {
        "status": "completed",
        "monitor_runs_deleted": result.deleted_count
    }

# Made with Bob
