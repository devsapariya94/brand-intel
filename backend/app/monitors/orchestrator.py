"""Monitor orchestrator for coordinating all monitors"""
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from .base import BaseMonitor
from .storage import RawHitStorage
from .detector import KeywordMatcher

logger = logging.getLogger(__name__)


class MonitorOrchestrator:
    """
    Coordinates all monitors to run in parallel.
    Handles scheduling, error recovery, and result aggregation.
    """
    
    def __init__(
        self,
        monitors: List[BaseMonitor],
        storage: RawHitStorage,
        matcher: KeywordMatcher,
        db_client: AsyncIOMotorClient,
        circuit_breaker: Optional = None,
        dlq: Optional = None,
        enrichment_service: Optional = None
    ):
        self.monitors = monitors
        self.storage = storage
        self.matcher = matcher
        self.db = db_client.brand_intel
        self.circuit_breaker = circuit_breaker
        self.dlq = dlq
        self.enrichment_service = enrichment_service
    
    async def run_all_monitors(self, brand: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all enabled monitors for a brand in parallel.
        
        Returns:
            Summary statistics
        """
        enabled_monitors = []
        for monitor in self.monitors:
            monitor_key = f"{monitor.name.lower().replace('monitor', '')}_enabled"
            if brand.get('monitor_config', {}).get(monitor_key, True):
                enabled_monitors.append(monitor)
        
        tasks = [
            self._run_single_monitor(monitor, brand)
            for monitor in enabled_monitors
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_hits = 0
        total_stored = 0
        total_enriched = 0
        stored_ids = []
        errors = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append({
                    "monitor": enabled_monitors[i].name,
                    "error": str(result)
                })
            else:
                total_hits += result['hits_found']
                total_stored += result['hits_stored']
                total_enriched += result.get('hits_enriched', 0)
                stored_ids.extend(result.get("stored_ids", []))
        
        return {
            "brand_id": str(brand['_id']),
            "monitors_run": len(enabled_monitors),
            "total_hits_found": total_hits,
            "total_hits_stored": total_stored,
            "total_hits_enriched": total_enriched,
            "stored_ids": stored_ids,
            "errors": errors,
            "completed_at": datetime.now(timezone.utc)
        }
    
    async def _run_single_monitor(
        self,
        monitor: BaseMonitor,
        brand: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run a single monitor with circuit breaker and error handling"""
        monitor_type = monitor.name.lower().replace("monitor", "")
        
        if self.circuit_breaker and not self.circuit_breaker.should_allow(monitor_type):
            logger.warning(f"Circuit breaker blocking {monitor_type} for brand {brand.get('name')}")
            return {"hits_found": 0, "hits_stored": 0, "skipped": True}
        
        run_record = {
            "monitor_type": monitor_type,
            "brand_id": brand['_id'],
            "started_at": datetime.now(timezone.utc),
            "status": "running",
            "api_calls_made": 0,
            "rate_limit_hit": False
        }
        run_result = await self.db.monitor_runs.insert_one(run_record)
        run_id = run_result.inserted_id
        
        try:
            api_calls_before = monitor.get_api_calls_count()
            start_time = datetime.now(timezone.utc)
            raw_hits = await monitor.run(brand)
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            api_calls_made = monitor.get_api_calls_count() - api_calls_before
            
            matched_hits = []
            for hit in raw_hits:
                match_result = self.matcher.match(hit.raw_content, brand)
                if match_result.is_match():
                    matched_hits.append((hit, str(brand['_id']), match_result))
            
            storage_result = await self.storage.store_hits_batch(matched_hits)

            enriched_count = 0
            if self.enrichment_service and storage_result.get("stored_ids"):
                for hit_id in storage_result["stored_ids"]:
                    try:
                        result = await self.enrichment_service.process_hit(hit_id, str(brand["_id"]))
                        if result:
                            enriched_count += 1
                    except Exception as enrichment_err:
                        logger.error(f"Failed to enrich hit {hit_id}: {enrichment_err}", exc_info=True)
            
            await self.db.monitor_runs.update_one(
                {"_id": run_id},
                {
                    "$set": {
                        "completed_at": datetime.now(timezone.utc),
                        "status": "completed",
                        "hits_found": len(raw_hits),
                        "hits_stored": storage_result['stored'],
                        "hits_enriched": enriched_count,
                        "execution_time_seconds": execution_time,
                        "api_calls_made": api_calls_made
                    }
                }
            )
            
            if self.circuit_breaker:
                self.circuit_breaker.record_success(monitor_type)
            
            return {
                "hits_found": len(raw_hits),
                "hits_stored": storage_result['stored'],
                "hits_enriched": enriched_count,
                "stored_ids": storage_result.get("stored_ids", [])
            }
            
        except Exception as e:
            await self.db.monitor_runs.update_one(
                {"_id": run_id},
                {
                    "$set": {
                        "completed_at": datetime.now(timezone.utc),
                        "status": "failed",
                        "error_message": str(e)
                    }
                }
            )
            
            if self.circuit_breaker:
                self.circuit_breaker.record_failure(monitor_type, e)
            
            if self.dlq:
                try:
                    await self.dlq.add_to_dlq(
                        hit_data={
                            "brand_id": brand.get('_id'),
                            "source": monitor_type,
                            "error_context": str(e)
                        },
                        error=str(e),
                        error_type="monitor_execution_failure"
                    )
                except Exception as dlq_err:
                    logger.error(f"Failed to add to DLQ: {dlq_err}")
            
            raise
    
    async def run_scheduled_scan(self, max_concurrent: int = 5) -> Dict[str, Any]:
        """
        Run monitors for all active brands.
        Called by scheduler every N minutes.
        """
        brands = await self.db.brands.find({"active": True}).to_list(length=None)
        
        if not brands:
            return {
                "brands_scanned": 0,
                "successful_scans": 0,
                "failed_scans": 0,
                "results": [],
                "scan_completed_at": datetime.now(timezone.utc)
            }
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scan_with_limit(brand):
            async with semaphore:
                return await self.run_all_monitors(brand)
        
        tasks = [scan_with_limit(brand) for brand in brands]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_scans = sum(1 for r in results if not isinstance(r, Exception))
        failed_scans = len(results) - successful_scans
        
        return {
            "brands_scanned": len(brands),
            "successful_scans": successful_scans,
            "failed_scans": failed_scans,
            "results": [r for r in results if not isinstance(r, Exception)],
            "scan_completed_at": datetime.now(timezone.utc)
        }
    
    async def run_single_brand_scan(self, brand_id: str) -> Dict[str, Any]:
        """
        Run monitors for a single brand by ID.
        Useful for manual triggers or testing.
        """
        from bson import ObjectId
        brand = await self.db.brands.find_one({"_id": ObjectId(brand_id)})
        
        if not brand:
            raise ValueError(f"Brand with ID {brand_id} not found")
        
        if not brand.get('active', False):
            raise ValueError(f"Brand {brand.get('name')} is not active")
        
        return await self.run_all_monitors(brand)
    
    async def get_orchestrator_stats(self) -> Dict[str, Any]:
        """Get statistics about orchestrator operations"""
        total_runs = await self.db.monitor_runs.count_documents({})
        
        completed_runs = await self.db.monitor_runs.count_documents({"status": "completed"})
        failed_runs = await self.db.monitor_runs.count_documents({"status": "failed"})
        running_runs = await self.db.monitor_runs.count_documents({"status": "running"})
        
        storage_stats = await self.storage.get_stats()
        
        cb_stats = {}
        if self.circuit_breaker:
            cb_stats = self.circuit_breaker.get_stats()
        
        return {
            "total_runs": total_runs,
            "completed_runs": completed_runs,
            "failed_runs": failed_runs,
            "running_runs": running_runs,
            "success_rate": completed_runs / total_runs if total_runs > 0 else 0,
            "storage_stats": storage_stats,
            "circuit_breaker": cb_stats
        }
    
    async def close_all(self):
        """Close all monitor resources (HTTP sessions, etc.)"""
        for monitor in self.monitors:
            try:
                await monitor.close()
            except Exception as e:
                logger.error(f"Error closing {monitor.name}: {e}")
