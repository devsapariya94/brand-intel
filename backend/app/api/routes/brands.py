"""Brand management API routes"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timezone

from ..dependencies import get_database
from ..models.requests import BrandCreate, BrandUpdate
from ..models.responses import BrandResponse, BrandStats

router = APIRouter(prefix="/brands", tags=["brands"])


@router.get("", response_model=List[BrandResponse])
async def list_brands(
    active_only: bool = False,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """List all brands with aggregated stats"""
    query = {"active": True} if active_only else {}
    brands = await db.brands.find(query).to_list(length=None)
    
    if not brands:
        return []
    
    brand_ids = [b["_id"] for b in brands]
    
    # Aggregate hit stats for all brands in one query
    hits_pipeline = [
        {"$match": {"brand_id": {"$in": brand_ids}}},
        {"$group": {
            "_id": "$brand_id",
            "total_hits": {"$sum": 1},
            "last_hit": {"$max": "$detected_at"}
        }}
    ]
    hits_stats = await db.raw_hits.aggregate(hits_pipeline).to_list(length=None)
    hits_map = {h["_id"]: h for h in hits_stats}
    
    # 24h hits aggregation
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    hits_24h_pipeline = [
        {"$match": {"brand_id": {"$in": brand_ids}, "detected_at": {"$gte": today_start}}},
        {"$group": {"_id": "$brand_id", "count": {"$sum": 1}}}
    ]
    hits_24h_result = await db.raw_hits.aggregate(hits_24h_pipeline).to_list(length=None)
    hits_24h_map = {h["_id"]: h["count"] for h in hits_24h_result}
    
    # Aggregate last scan for all brands
    last_run_pipeline = [
        {"$match": {"brand_id": {"$in": brand_ids}}},
        {"$sort": {"started_at": -1}},
        {"$group": {"_id": "$brand_id", "last_run": {"$first": "$started_at"}}}
    ]
    last_runs = await db.monitor_runs.aggregate(last_run_pipeline).to_list(length=None)
    last_run_map = {lr["_id"]: lr["last_run"] for lr in last_runs}
    
    result = []
    for brand in brands:
        bid = brand["_id"]
        hit_stats = hits_map.get(bid, {})
        result.append(BrandResponse(
            id=str(bid),
            name=brand["name"],
            domain=brand["domain"],
            keywords=brand.get("keywords", []),
            email_patterns=brand.get("email_patterns", []),
            regex_patterns=brand.get("regex_patterns", []),
            typosquat_variants=brand.get("typosquat_variants", []),
            slack_webhook=brand.get("slack_webhook"),
            alert_email=brand.get("alert_email"),
            monitor_config=brand.get("monitor_config", {}),
            active=brand.get("active", True),
            created_at=brand.get("created_at"),
            updated_at=brand.get("updated_at"),
            stats=BrandStats(
                total_hits=hit_stats.get("total_hits", 0),
                hits_last_24h=hits_24h_map.get(bid, 0),
                last_scan=last_run_map.get(bid),
                last_hit=hit_stats.get("last_hit")
            )
        ))
    
    return result


@router.get("/{brand_id}", response_model=BrandResponse)
async def get_brand(
    brand_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get brand by ID"""
    try:
        brand = await db.brands.find_one({"_id": ObjectId(brand_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid brand ID format")
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Get stats
    total_hits = await db.raw_hits.count_documents({"brand_id": brand["_id"]})
    hits_24h = await db.raw_hits.count_documents({
        "brand_id": brand["_id"],
        "detected_at": {"$gte": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)}
    })
    
    last_run = await db.monitor_runs.find_one(
        {"brand_id": brand["_id"]},
        sort=[("started_at", -1)]
    )
    
    last_hit = await db.raw_hits.find_one(
        {"brand_id": brand["_id"]},
        sort=[("detected_at", -1)]
    )
    
    return BrandResponse(
        id=str(brand["_id"]),
        name=brand["name"],
        domain=brand["domain"],
        keywords=brand.get("keywords", []),
        email_patterns=brand.get("email_patterns", []),
        regex_patterns=brand.get("regex_patterns", []),
        typosquat_variants=brand.get("typosquat_variants", []),
        slack_webhook=brand.get("slack_webhook"),
        alert_email=brand.get("alert_email"),
        monitor_config=brand.get("monitor_config", {}),
        active=brand.get("active", True),
        created_at=brand.get("created_at"),
        updated_at=brand.get("updated_at"),
        stats=BrandStats(
            total_hits=total_hits,
            hits_last_24h=hits_24h,
            last_scan=last_run["started_at"] if last_run else None,
            last_hit=last_hit["detected_at"] if last_hit else None
        )
    )


@router.post("", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
async def create_brand(
    brand: BrandCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create a new brand"""
    # Check if domain already exists
    existing = await db.brands.find_one({"domain": brand.domain})
    if existing:
        raise HTTPException(status_code=400, detail="Brand with this domain already exists")
    
    # Create brand document
    brand_doc = {
        "name": brand.name,
        "domain": brand.domain,
        "keywords": brand.keywords,
        "email_patterns": brand.email_patterns,
        "regex_patterns": brand.regex_patterns,
        "typosquat_variants": brand.typosquat_variants,
        "slack_webhook": brand.slack_webhook,
        "alert_email": brand.alert_email,
        "monitor_config": brand.monitor_config.dict(),
        "active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    result = await db.brands.insert_one(brand_doc)
    brand_doc["_id"] = result.inserted_id
    
    return BrandResponse(
        id=str(brand_doc["_id"]),
        name=brand_doc["name"],
        domain=brand_doc["domain"],
        keywords=brand_doc["keywords"],
        email_patterns=brand_doc["email_patterns"],
        regex_patterns=brand_doc["regex_patterns"],
        typosquat_variants=brand_doc["typosquat_variants"],
        slack_webhook=brand_doc["slack_webhook"],
        alert_email=brand_doc["alert_email"],
        monitor_config=brand_doc["monitor_config"],
        active=brand_doc["active"],
        created_at=brand_doc["created_at"],
        updated_at=brand_doc["updated_at"],
        stats=BrandStats()
    )


@router.put("/{brand_id}", response_model=BrandResponse)
async def update_brand(
    brand_id: str,
    brand_update: BrandUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update a brand"""
    try:
        brand_oid = ObjectId(brand_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid brand ID format")
    
    # Check if brand exists
    existing = await db.brands.find_one({"_id": brand_oid})
    if not existing:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Build update document
    update_doc: dict = {"updated_at": datetime.now(timezone.utc)}
    if brand_update.name is not None:
        update_doc["name"] = brand_update.name
    if brand_update.keywords is not None:
        update_doc["keywords"] = brand_update.keywords
    if brand_update.email_patterns is not None:
        update_doc["email_patterns"] = brand_update.email_patterns
    if brand_update.regex_patterns is not None:
        update_doc["regex_patterns"] = brand_update.regex_patterns
    if brand_update.typosquat_variants is not None:
        update_doc["typosquat_variants"] = brand_update.typosquat_variants
    if brand_update.slack_webhook is not None:
        update_doc["slack_webhook"] = brand_update.slack_webhook
    if brand_update.alert_email is not None:
        update_doc["alert_email"] = brand_update.alert_email
    if brand_update.monitor_config is not None:
        update_doc["monitor_config"] = brand_update.monitor_config.dict()
    if brand_update.active is not None:
        update_doc["active"] = brand_update.active
    
    await db.brands.update_one(
        {"_id": brand_oid},
        {"$set": update_doc}
    )
    
    # Return updated brand
    return await get_brand(brand_id, db)


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand(
    brand_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Delete a brand"""
    try:
        brand_oid = ObjectId(brand_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid brand ID format")
    
    result = await db.brands.delete_one({"_id": brand_oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    return None


@router.patch("/{brand_id}/toggle", response_model=BrandResponse)
async def toggle_brand(
    brand_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Toggle brand active status"""
    try:
        brand_oid = ObjectId(brand_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid brand ID format")
    
    brand = await db.brands.find_one({"_id": brand_oid})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    new_status = not brand.get("active", True)
    await db.brands.update_one(
        {"_id": brand_oid},
        {"$set": {"active": new_status, "updated_at": datetime.now(timezone.utc)}}
    )
    
    return await get_brand(brand_id, db)

# Made with Bob
