"""Monitor health checker for tracking system health"""
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

MONITOR_TYPES = ["pastebin", "github", "hibp", "reddit"]


class MonitorHealthChecker:
    """
    Tracks and reports health metrics for all monitors.
    """
    
    def __init__(self, db_client: AsyncIOMotorClient):
        self.db = db_client.brand_intel
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall health status of all monitors.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        
        recent_runs = await self.db.monitor_runs.find(
            {"started_at": {"$gte": cutoff}}
        ).to_list(length=None)
        
        health_by_monitor = {}
        
        for monitor_type in MONITOR_TYPES:
            monitor_runs = [r for r in recent_runs if r['monitor_type'] == monitor_type]
            
            if not monitor_runs:
                health_by_monitor[monitor_type] = {
                    "status": "unknown",
                    "message": "No recent runs"
                }
                continue
            
            total_runs = len(monitor_runs)
            successful_runs = len([r for r in monitor_runs if r['status'] == 'completed'])
            failed_runs = len([r for r in monitor_runs if r['status'] == 'failed'])
            success_rate = successful_runs / total_runs if total_runs > 0 else 0
            
            avg_execution_time = sum(
                r.get('execution_time_seconds', 0)
                for r in monitor_runs if r['status'] == 'completed'
            ) / successful_runs if successful_runs > 0 else 0
            
            total_hits = sum(r.get('hits_found', 0) for r in monitor_runs)
            
            if success_rate >= 0.95:
                status = "healthy"
            elif success_rate >= 0.8:
                status = "degraded"
            else:
                status = "unhealthy"
            
            health_by_monitor[monitor_type] = {
                "status": status,
                "success_rate": success_rate,
                "total_runs_24h": total_runs,
                "successful_runs": successful_runs,
                "failed_runs": failed_runs,
                "avg_execution_time": avg_execution_time,
                "total_hits_found": total_hits,
                "last_run": max(r['started_at'] for r in monitor_runs)
            }
        
        all_statuses = [m['status'] for m in health_by_monitor.values() if m['status'] != 'unknown']
        if not all_statuses:
            overall_status = "unknown"
        elif all(s == "healthy" for s in all_statuses):
            overall_status = "healthy"
        elif any(s == "unhealthy" for s in all_statuses):
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"
        
        return {
            "overall_status": overall_status,
            "monitors": health_by_monitor,
            "checked_at": datetime.now(timezone.utc)
        }
    
    async def get_monitor_history(
        self,
        monitor_type: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get historical run data for a specific monitor.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        runs = await self.db.monitor_runs.find(
            {
                "monitor_type": monitor_type,
                "started_at": {"$gte": cutoff}
            }
        ).sort("started_at", -1).to_list(length=None)
        
        return runs
    
    async def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get summary of errors in the last N hours.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        failed_runs = await self.db.monitor_runs.find(
            {
                "status": "failed",
                "started_at": {"$gte": cutoff}
            }
        ).to_list(length=None)
        
        errors_by_monitor = {}
        for run in failed_runs:
            monitor_type = run['monitor_type']
            if monitor_type not in errors_by_monitor:
                errors_by_monitor[monitor_type] = []
            
            errors_by_monitor[monitor_type].append({
                "error_message": run.get('error_message'),
                "occurred_at": run['started_at'],
                "brand_id": str(run.get('brand_id')) if run.get('brand_id') else None
            })
        
        return {
            "total_errors": len(failed_runs),
            "errors_by_monitor": errors_by_monitor,
            "time_range_hours": hours
        }
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for all monitors.
        """
        completed_runs = await self.db.monitor_runs.find(
            {"status": "completed"}
        ).to_list(length=None)
        
        if not completed_runs:
            return {
                "message": "No completed runs found"
            }
        
        metrics_by_monitor = {}
        
        for monitor_type in MONITOR_TYPES:
            monitor_runs = [r for r in completed_runs if r['monitor_type'] == monitor_type]
            
            if not monitor_runs:
                continue
            
            execution_times = [r.get('execution_time_seconds', 0) for r in monitor_runs]
            hits_found = [r.get('hits_found', 0) for r in monitor_runs]
            hits_stored = [r.get('hits_stored', 0) for r in monitor_runs]
            
            metrics_by_monitor[monitor_type] = {
                "avg_execution_time": sum(execution_times) / len(execution_times),
                "min_execution_time": min(execution_times),
                "max_execution_time": max(execution_times),
                "avg_hits_found": sum(hits_found) / len(hits_found),
                "total_hits_found": sum(hits_found),
                "total_hits_stored": sum(hits_stored),
                "deduplication_rate": 1 - (sum(hits_stored) / sum(hits_found)) if sum(hits_found) > 0 else 0
            }
        
        return {
            "metrics_by_monitor": metrics_by_monitor,
            "total_runs_analyzed": len(completed_runs)
        }
    
    async def check_stale_monitors(self, max_age_hours: int = 2) -> List[str]:
        """
        Check for monitors that haven't run recently.
        Returns list of stale monitor types.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        stale_monitors = []
        
        for monitor_type in MONITOR_TYPES:
            latest_run = await self.db.monitor_runs.find_one(
                {"monitor_type": monitor_type},
                sort=[("started_at", -1)]
            )
            
            if not latest_run or latest_run['started_at'] < cutoff:
                stale_monitors.append(monitor_type)
        
        return stale_monitors
