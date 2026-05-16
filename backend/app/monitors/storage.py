"""Raw hit storage layer with deduplication"""
import hashlib
import logging
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from .detector import MatchResult
from .base import RawHit

logger = logging.getLogger(__name__)


class RawHitStorage:
    """
    Handles storage of raw hits in MongoDB with:
    - Deduplication
    - Indexing
    - Batch operations
    """
    
    def __init__(self, db_client: AsyncIOMotorClient):
        self.db = db_client.brand_intel
        self.raw_hits = self.db.raw_hits
    
    async def store_hit(
        self, 
        hit: RawHit, 
        brand_id: str, 
        match_result: MatchResult
    ) -> Optional[str]:
        """
        Store a single raw hit with deduplication.
        
        Returns:
            Hit ID if stored, None if duplicate
        """
        # Calculate content hash for deduplication
        content_hash = hashlib.sha256(hit.raw_content.encode()).hexdigest()
        
        # Check if already exists
        existing = await self.raw_hits.find_one({"content_hash": content_hash, "brand_id": brand_id})
        if existing:
            return None  # Duplicate
        
        # Prepare document
        doc = {
            "brand_id": brand_id,
            "source": hit.source,
            "source_url": hit.source_url,
            "raw_content": hit.raw_content,
            "content_hash": content_hash,
            "detected_at": hit.detected_at,
            "match_details": {
                "matched_keywords": match_result.matched_keywords,
                "matched_patterns": [
                    m.keyword for m in match_result.matches 
                    if m.match_type == "regex"
                ],
                "match_type": match_result.match_types[0] if match_result.match_types else "unknown",
                "confidence_score": match_result.confidence_score,
                "match_locations": [
                    {
                        "keyword": m.keyword,
                        "start_index": m.start_index,
                        "end_index": m.end_index,
                        "context": m.context
                    }
                    for m in match_result.matches
                ]
            },
            "metadata": hit.metadata,
            "processing_status": "pending",
            "deduplication_checked": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Insert
        result = await self.raw_hits.insert_one(doc)
        return str(result.inserted_id)
    
    async def store_hits_batch(
        self, 
        hits: List[tuple]
    ) -> Dict[str, Any]:
        """
        Store multiple hits in a batch operation.
        
        Args:
            hits: List of tuples (RawHit, brand_id, MatchResult)
        
        Returns:
            Statistics about the batch operation
        """
        stored_count = 0
        duplicate_count = 0
        error_count = 0
        stored_ids = []
        
        for hit, brand_id, match_result in hits:
            try:
                hit_id = await self.store_hit(hit, brand_id, match_result)
                if hit_id:
                    stored_count += 1
                    stored_ids.append(hit_id)
                else:
                    duplicate_count += 1
            except Exception as e:
                error_count += 1
                # Log error
                logger.error(f"Error storing hit: {e}")
        
        return {
            "total": len(hits),
            "stored": stored_count,
            "duplicates": duplicate_count,
            "errors": error_count,
            "stored_ids": stored_ids
        }
    
    async def get_pending_hits(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch hits pending enrichment"""
        cursor = self.raw_hits.find(
            {"processing_status": "pending"}
        ).sort("detected_at", -1).limit(limit)
        
        return await cursor.to_list(length=limit)
    
    async def update_processing_status(self, hit_id: str, status: str):
        """Update processing status of a hit"""
        await self.raw_hits.update_one(
            {"_id": ObjectId(hit_id)},
            {
                "$set": {
                    "processing_status": status,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        total_hits = await self.raw_hits.count_documents({})
        pending_hits = await self.raw_hits.count_documents({"processing_status": "pending"})
        
        # Hits by source
        pipeline = [
            {"$group": {"_id": "$source", "count": {"$sum": 1}}}
        ]
        by_source = {
            doc['_id']: doc['count'] 
            async for doc in self.raw_hits.aggregate(pipeline)
        }
        
        return {
            "total_hits": total_hits,
            "pending_hits": pending_hits,
            "by_source": by_source
        }

# Made with Bob
