"""Dead Letter Queue for failed hit processing"""
import logging
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

logger = logging.getLogger(__name__)


class DeadLetterQueue:
    """
    Manages failed hits that couldn't be processed.
    Provides retry mechanism and manual review capabilities.
    """
    
    def __init__(
        self,
        db_client: AsyncIOMotorClient,
        max_retries: int = 3
    ):
        self.db = db_client.brand_intel
        self.dlq = self.db.dead_letter_queue
        self.max_retries = max_retries
    
    async def add_to_dlq(
        self,
        hit_data: Dict[str, Any],
        error: str,
        error_type: str = "processing_error"
    ) -> str:
        """
        Add a failed hit to the dead letter queue.
        
        Args:
            hit_data: The hit data that failed to process
            error: Error message
            error_type: Type of error (processing_error, storage_error, etc.)
        
        Returns:
            DLQ entry ID
        """
        # Generate unique ID for deduplication
        content_hash = hashlib.sha256(
            str(hit_data.get("raw_content", "")).encode()
        ).hexdigest()
        
        # Check if already in DLQ
        existing = await self.dlq.find_one({
            "content_hash": content_hash,
            "brand_id": hit_data.get("brand_id")
        })
        
        if existing:
            # Update retry count
            await self.dlq.update_one(
                {"_id": existing["_id"]},
                {
                    "$inc": {"retry_count": 1},
                    "$set": {
                        "last_error": error,
                        "last_error_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            logger.debug(f"Updated existing DLQ entry: {existing['_id']}")
            return str(existing["_id"])
        
        # Create new DLQ entry
        dlq_entry = {
            "hit_data": hit_data,
            "content_hash": content_hash,
            "brand_id": hit_data.get("brand_id"),
            "error": error,
            "error_type": error_type,
            "retry_count": 0,
            "status": "pending",  # pending, retrying, failed, resolved
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_error_at": datetime.now(timezone.utc),
            "last_error": error
        }
        
        result = await self.dlq.insert_one(dlq_entry)
        logger.warning(f"Added to DLQ: {result.inserted_id} - {error}")
        return str(result.inserted_id)
    
    async def get_pending_items(
        self,
        limit: int = 100,
        max_retry_count: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get pending items from DLQ for retry.
        
        Args:
            limit: Maximum number of items to return
            max_retry_count: Only return items with retry_count <= this value
        
        Returns:
            List of DLQ entries
        """
        query = {"status": "pending"}
        
        if max_retry_count is not None:
            query["retry_count"] = {"$lte": max_retry_count}
        
        cursor = self.dlq.find(query).sort("created_at", 1).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def mark_as_retrying(self, dlq_id: str):
        """Mark DLQ item as currently being retried"""
        await self.dlq.update_one(
            {"_id": ObjectId(dlq_id)},
            {
                "$set": {
                    "status": "retrying",
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
    
    async def mark_as_resolved(self, dlq_id: str):
        """Mark DLQ item as successfully resolved"""
        await self.dlq.update_one(
            {"_id": ObjectId(dlq_id)},
            {
                "$set": {
                    "status": "resolved",
                    "resolved_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        logger.info(f"DLQ item resolved: {dlq_id}")
    
    async def mark_as_failed(self, dlq_id: str, error: str):
        """Mark DLQ item as permanently failed (max retries exceeded)"""
        await self.dlq.update_one(
            {"_id": ObjectId(dlq_id)},
            {
                "$set": {
                    "status": "failed",
                    "last_error": error,
                    "last_error_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                },
                "$inc": {"retry_count": 1}
            }
        )
        logger.error(f"DLQ item permanently failed: {dlq_id} - {error}")
    
    async def retry_item(self, dlq_id: str, processor_func) -> bool:
        """
        Retry processing a DLQ item.
        
        Args:
            dlq_id: DLQ entry ID
            processor_func: Async function to process the hit
        
        Returns:
            True if successful, False otherwise
        """
        # Get DLQ entry
        entry = await self.dlq.find_one({"_id": ObjectId(dlq_id)})
        if not entry:
            logger.error(f"DLQ entry not found: {dlq_id}")
            return False
        
        # Check retry limit
        if entry["retry_count"] >= self.max_retries:
            await self.mark_as_failed(dlq_id, "Max retries exceeded")
            return False
        
        # Mark as retrying
        await self.mark_as_retrying(dlq_id)
        
        try:
            # Attempt to process
            await processor_func(entry["hit_data"])
            
            # Success - mark as resolved
            await self.mark_as_resolved(dlq_id)
            return True
            
        except Exception as e:
            # Failed - update error
            retry_count = entry["retry_count"] + 1
            
            if retry_count >= self.max_retries:
                await self.mark_as_failed(dlq_id, str(e))
            else:
                # Reset to pending for next retry
                await self.dlq.update_one(
                    {"_id": ObjectId(dlq_id)},
                    {
                        "$set": {
                            "status": "pending",
                            "last_error": str(e),
                            "last_error_at": datetime.now(timezone.utc),
                            "updated_at": datetime.now(timezone.utc)
                        },
                        "$inc": {"retry_count": 1}
                    }
                )
            
            logger.warning(f"DLQ retry failed ({retry_count}/{self.max_retries}): {dlq_id} - {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get DLQ statistics"""
        total = await self.dlq.count_documents({})
        pending = await self.dlq.count_documents({"status": "pending"})
        retrying = await self.dlq.count_documents({"status": "retrying"})
        failed = await self.dlq.count_documents({"status": "failed"})
        resolved = await self.dlq.count_documents({"status": "resolved"})
        
        # Get error type breakdown
        pipeline = [
            {"$group": {"_id": "$error_type", "count": {"$sum": 1}}}
        ]
        by_error_type = {
            doc['_id']: doc['count']
            async for doc in self.dlq.aggregate(pipeline)
        }
        
        return {
            "total": total,
            "pending": pending,
            "retrying": retrying,
            "failed": failed,
            "resolved": resolved,
            "by_error_type": by_error_type
        }
    
    async def get_failed_items(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get permanently failed items for manual review"""
        cursor = self.dlq.find(
            {"status": "failed"}
        ).sort("updated_at", -1).limit(limit)
        
        return await cursor.to_list(length=limit)
    
    async def clear_resolved(self, days_old: int = 7):
        """Clear resolved items older than specified days"""
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_old)
        
        result = await self.dlq.delete_many({
            "status": "resolved",
            "resolved_at": {"$lt": cutoff}
        })
        
        logger.info(f"Cleared {result.deleted_count} resolved DLQ items older than {days_old} days")
        return result.deleted_count
    
    async def requeue_failed(self, dlq_id: str):
        """Manually requeue a failed item for retry"""
        await self.dlq.update_one(
            {"_id": ObjectId(dlq_id)},
            {
                "$set": {
                    "status": "pending",
                    "retry_count": 0,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        logger.info(f"Requeued failed DLQ item: {dlq_id}")

# Made with Bob
