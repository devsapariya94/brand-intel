"""Raw hits and alerts API routes"""
from typing import List, Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timezone, timedelta

from ..dependencies import get_database
from ..models.requests import UpdateHitStatusRequest
from ..models.responses import (
    RawHitResponse,
    PaginatedHitsResponse,
    HitsStatsResponse,
    TimelinePoint,
    KeywordStat
)

router = APIRouter(prefix="/hits", tags=["hits"])


def _brand_id_query_values(brand_id: str) -> List[object]:
    values: List[object] = [brand_id]
    try:
        values.append(ObjectId(brand_id))
    except Exception:
        pass
    return values


async def _brand_name_for_hit(db: AsyncIOMotorDatabase, brand_id) -> str:
    brand = await db.brands.find_one({"_id": brand_id})
    if not brand:
        try:
            brand = await db.brands.find_one({"_id": ObjectId(brand_id)})
        except Exception:
            brand = None
    return brand["name"] if brand else "Unknown"


async def _enrichment_for_hit(db: AsyncIOMotorDatabase, hit_id: str) -> Optional[dict]:
    enrichment = await db.enriched_hits.find_one({"hit_id": hit_id})
    if not enrichment:
        return None
    enrichment.pop("_id", None)
    return enrichment


async def _raw_hit_response(db: AsyncIOMotorDatabase, hit: dict, brand_name: Optional[str] = None) -> RawHitResponse:
    hit_id = str(hit["_id"])
    return RawHitResponse(
        id=hit_id,
        brand_id=str(hit["brand_id"]),
        brand_name=brand_name or await _brand_name_for_hit(db, hit.get("brand_id")),
        source=hit["source"],
        source_url=hit["source_url"],
        raw_content=hit["raw_content"],
        content_preview=hit["raw_content"][:500] if len(hit["raw_content"]) > 500 else hit["raw_content"],
        detected_at=hit["detected_at"],
        match_details=hit["match_details"],
        processing_status=hit.get("processing_status", "pending"),
        created_at=hit.get("created_at", hit["detected_at"]),
        updated_at=hit.get("updated_at", hit["detected_at"]),
        reviewed_by=hit.get("reviewed_by"),
        reviewed_at=hit.get("reviewed_at"),
        notes=hit.get("notes"),
        enrichment=await _enrichment_for_hit(db, hit_id)
    )


@router.get("", response_model=PaginatedHitsResponse)
async def list_hits(
    brand_id: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = Query(50, le=200),
    page: int = Query(1, ge=1),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """List raw hits with filtering and pagination"""
    query = {}
    if brand_id:
        query["brand_id"] = {"$in": _brand_id_query_values(brand_id)}
    if status:
        query["processing_status"] = status
    if source:
        query["source"] = source
    
    # Get total count
    total = await db.raw_hits.count_documents(query)
    
    # Get paginated results
    skip = (page - 1) * limit
    hits = await db.raw_hits.find(query, sort=[("detected_at", -1)], skip=skip, limit=limit).to_list(length=limit)
    
    # Batch-fetch brand names to avoid N+1
    object_brand_ids = []
    for h in hits:
        bid = h.get("brand_id")
        if isinstance(bid, ObjectId):
            object_brand_ids.append(bid)
        else:
            try:
                object_brand_ids.append(ObjectId(bid))
            except Exception:
                pass
    brands = await db.brands.find({"_id": {"$in": list(set(object_brand_ids))}}).to_list(length=None)
    brand_map = {str(b["_id"]): b["name"] for b in brands}
    
    # Convert to response format
    result = []
    for hit in hits:
        brand_name = brand_map.get(str(hit.get("brand_id")), "Unknown")
        result.append(await _raw_hit_response(db, hit, brand_name))
    
    return PaginatedHitsResponse(
        hits=result,
        total=total,
        page=page,
        page_size=limit,
        has_next=(skip + limit) < total,
        has_prev=page > 1
    )


@router.get("/stats", response_model=HitsStatsResponse)
async def get_hits_stats_route(
    brand_id: Optional[str] = None,
    days: int = Query(7, ge=1, le=90),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get hits statistics before the dynamic hit-id route is matched."""
    return await _build_hits_stats(brand_id, days, db)


@router.get("/{hit_id}", response_model=RawHitResponse)
async def get_hit(
    hit_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get hit details"""
    try:
        hit = await db.raw_hits.find_one({"_id": ObjectId(hit_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid hit ID format")
    
    if not hit:
        raise HTTPException(status_code=404, detail="Hit not found")
    
    return await _raw_hit_response(db, hit)


@router.patch("/{hit_id}/status", response_model=RawHitResponse)
async def update_hit_status(
    hit_id: str,
    request: UpdateHitStatusRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update hit processing status"""
    try:
        hit_oid = ObjectId(hit_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid hit ID format")
    
    hit = await db.raw_hits.find_one({"_id": hit_oid})
    if not hit:
        raise HTTPException(status_code=404, detail="Hit not found")
    
    update_doc = {
        "processing_status": request.status,
        "updated_at": datetime.now(timezone.utc),
        "reviewed_at": datetime.now(timezone.utc),
        "reviewed_by": "api_user"  # Would come from auth
    }
    if request.notes:
        update_doc["notes"] = request.notes
    
    await db.raw_hits.update_one(
        {"_id": hit_oid},
        {"$set": update_doc}
    )
    
    return await get_hit(hit_id, db)


async def _build_hits_stats(
    brand_id: Optional[str] = None,
    days: int = Query(7, ge=1, le=90),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get hits statistics"""
    query = {}
    if brand_id:
        query["brand_id"] = {"$in": _brand_id_query_values(brand_id)}
    
    # Total hits
    total_hits = await db.raw_hits.count_documents(query)
    
    # By source
    by_source_pipeline = [
        {"$match": query},
        {"$group": {"_id": "$source", "count": {"$sum": 1}}}
    ]
    by_source_result = await db.raw_hits.aggregate(by_source_pipeline).to_list(length=None)
    by_source = {item["_id"]: item["count"] for item in by_source_result}
    
    # By status
    by_status_pipeline = [
        {"$match": query},
        {"$group": {"_id": "$processing_status", "count": {"$sum": 1}}}
    ]
    by_status_result = await db.raw_hits.aggregate(by_status_pipeline).to_list(length=None)
    by_status = {item["_id"]: item["count"] for item in by_status_result}
    
    # By brand
    by_brand_pipeline = [
        {"$match": query},
        {"$group": {"_id": "$brand_id", "count": {"$sum": 1}}}
    ]
    by_brand_result = await db.raw_hits.aggregate(by_brand_pipeline).to_list(length=None)
    by_brand = {}
    for item in by_brand_result:
        brand_name = await _brand_name_for_hit(db, item["_id"])
        by_brand[brand_name] = item["count"]
    
    # Timeline
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    timeline_query = {**query, "detected_at": {"$gte": start_date}}
    timeline_pipeline = [
        {"$match": timeline_query},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$detected_at"}},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    timeline_result = await db.raw_hits.aggregate(timeline_pipeline).to_list(length=None)
    timeline = [TimelinePoint(date=item["_id"], count=item["count"]) for item in timeline_result]
    
    # Top keywords
    top_keywords_pipeline = [
        {"$match": query},
        {"$unwind": "$match_details.matched_keywords"},
        {"$group": {"_id": "$match_details.matched_keywords", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    top_keywords_result = await db.raw_hits.aggregate(top_keywords_pipeline).to_list(length=None)
    top_keywords = [KeywordStat(keyword=item["_id"], count=item["count"]) for item in top_keywords_result]
    
    return HitsStatsResponse(
        total_hits=total_hits,
        by_source=by_source,
        by_status=by_status,
        by_brand=by_brand,
        timeline=timeline,
        top_keywords=top_keywords
    )

# Made with Bob
