"""AI enrichment configuration API routes"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..dependencies import get_database, get_config, get_enrichment_service
from ..models.requests import EnrichmentConfigUpdate
from ..models.responses import EnrichmentConfigResponse, EnrichmentStatsResponse
from ...daemon.config import DaemonConfig
from ...enrichment.service import EnrichmentService

router = APIRouter(prefix="/enrichment", tags=["enrichment"])


@router.get("/config", response_model=EnrichmentConfigResponse)
async def get_enrichment_config(
    config: DaemonConfig = Depends(get_config)
):
    """Get enrichment configuration"""
    return EnrichmentConfigResponse(
        enabled=config.enrichment_enabled,
        use_anthropic=config.use_anthropic,
        llm_model=config.anthropic_model if config.use_anthropic else config.llm_model,
        llm_temperature=config.anthropic_temperature if config.use_anthropic else config.llm_temperature,
        alert_threshold=0.85,
        suppress_threshold=0.85,
        escalate_threshold=0.60
    )


@router.put("/config", response_model=EnrichmentConfigResponse)
async def update_enrichment_config(
    update: EnrichmentConfigUpdate,
    config: DaemonConfig = Depends(get_config)
):
    """Update enrichment configuration"""
    # Return updated config values (runtime-only, not persisted to env)
    return EnrichmentConfigResponse(
        enabled=update.enabled if update.enabled is not None else config.enrichment_enabled,
        use_anthropic=update.use_anthropic if update.use_anthropic is not None else config.use_anthropic,
        llm_model=update.llm_model if update.llm_model else (config.anthropic_model if config.use_anthropic else config.llm_model),
        llm_temperature=update.llm_temperature if update.llm_temperature is not None else (config.anthropic_temperature if config.use_anthropic else config.llm_temperature),
        alert_threshold=update.alert_threshold if update.alert_threshold is not None else 0.85,
        suppress_threshold=update.suppress_threshold if update.suppress_threshold is not None else 0.85,
        escalate_threshold=update.escalate_threshold if update.escalate_threshold is not None else 0.60
    )


@router.get("/stats", response_model=EnrichmentStatsResponse)
async def get_enrichment_stats(
    enrichment_svc: Optional[EnrichmentService] = Depends(get_enrichment_service),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get enrichment statistics"""
    if not enrichment_svc:
        # Fallback to database query
        total = await db.enriched_hits.count_documents({})
        alerts = await db.enriched_hits.count_documents({"decision": "ALERT"})
        suppressed = await db.enriched_hits.count_documents({"decision": "SUPPRESS"})
        escalated = await db.enriched_hits.count_documents({"decision": "ESCALATE"})
        
        pipeline = [
            {"$group": {"_id": None, "avg_time": {"$avg": "$processing_time_ms"}}}
        ]
        avg_result = await db.enriched_hits.aggregate(pipeline).to_list(length=1)
        avg_time = (avg_result[0]["avg_time"] / 1000) if avg_result else 0.0
        
        return EnrichmentStatsResponse(
            total_processed=total,
            alerts_sent=alerts,
            suppressed=suppressed,
            escalated=escalated,
            avg_processing_time=avg_time,
            estimated_cost=0.0
        )
    
    stats = await enrichment_svc.get_stats()
    return EnrichmentStatsResponse(**stats)


@router.post("/process/{hit_id}")
async def manually_process_hit(
    hit_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    enrichment_svc: Optional[EnrichmentService] = Depends(get_enrichment_service)
):
    """Manually trigger enrichment for a specific hit"""
    if not enrichment_svc:
        raise HTTPException(status_code=503, detail="Enrichment service not available")
    
    # Fetch hit to get brand_id
    try:
        from bson import ObjectId
        hit = await db.raw_hits.find_one({"_id": ObjectId(hit_id)})
    except Exception:
        hit = await db.raw_hits.find_one({"_id": hit_id})
    
    if not hit:
        raise HTTPException(status_code=404, detail="Hit not found")
    
    brand_id = hit.get("brand_id", "")
    result = await enrichment_svc.process_hit(hit_id, str(brand_id))
    
    if not result:
        raise HTTPException(status_code=500, detail="Enrichment failed")
    
    return {
        "status": "completed",
        "hit_id": hit_id,
        "decision": result.decision,
        "severity": result.evaluation.severity,
        "confidence": result.evaluation.confidence,
        "reasoning": result.decision_reasoning
    }
