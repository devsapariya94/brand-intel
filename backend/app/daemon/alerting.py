"""Alerting system for critical failures and events"""
import logging
import aiohttp
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)


class AlertManager:
    """
    Manages alerts for critical failures and events.
    Supports Slack webhooks and can be extended for email.
    """
    
    def __init__(
        self,
        db_client: AsyncIOMotorClient,
        slack_webhook_url: Optional[str] = None,
        alert_email: Optional[str] = None,
        failure_threshold: int = 3
    ):
        self.db = db_client.brand_intel
        self.slack_webhook_url = slack_webhook_url
        self.alert_email = alert_email
        self.failure_threshold = failure_threshold
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self):
        """Initialize HTTP session for alerts"""
        if self.slack_webhook_url:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def alert_monitor_down(
        self,
        monitor_name: str,
        error: str,
        failure_count: int
    ):
        """
        Alert when a monitor is down or failing repeatedly.
        
        Args:
            monitor_name: Name of the failing monitor
            error: Error message
            failure_count: Number of consecutive failures
        """
        # Check if already alerted recently (prevent spam)
        recent_alert = await self._check_recent_alert(
            alert_type="monitor_down",
            monitor_name=monitor_name,
            hours=1
        )
        
        if recent_alert:
            logger.debug(f"Skipping alert for {monitor_name} - already alerted recently")
            return
        
        # Only alert if threshold reached
        if failure_count < self.failure_threshold:
            return
        
        message = (
            f"🚨 *Monitor Alert: {monitor_name}*\n"
            f"Status: DOWN\n"
            f"Consecutive Failures: {failure_count}\n"
            f"Error: {error}\n"
            f"Time: {datetime.now(timezone.utc).isoformat()}"
        )
        
        await self._send_alert(message, alert_type="monitor_down", monitor_name=monitor_name)
        logger.error(f"Alert sent: Monitor {monitor_name} is down after {failure_count} failures")
    
    async def alert_monitor_recovered(self, monitor_name: str):
        """Alert when a monitor recovers after being down"""
        message = (
            f"✅ *Monitor Recovered: {monitor_name}*\n"
            f"Status: UP\n"
            f"Time: {datetime.now(timezone.utc).isoformat()}"
        )
        
        await self._send_alert(message, alert_type="monitor_recovered", monitor_name=monitor_name)
        logger.info(f"Alert sent: Monitor {monitor_name} recovered")
    
    async def alert_high_error_rate(
        self,
        error_rate: float,
        time_window_hours: int = 1
    ):
        """Alert when overall error rate is high"""
        recent_alert = await self._check_recent_alert(
            alert_type="high_error_rate",
            hours=2
        )
        
        if recent_alert:
            return
        
        message = (
            f"⚠️ *High Error Rate Detected*\n"
            f"Error Rate: {error_rate:.1%}\n"
            f"Time Window: {time_window_hours} hour(s)\n"
            f"Time: {datetime.now(timezone.utc).isoformat()}"
        )
        
        await self._send_alert(message, alert_type="high_error_rate")
        logger.warning(f"Alert sent: High error rate {error_rate:.1%}")
    
    async def alert_no_scans(self, hours_since_last_scan: int):
        """Alert when no scans have run for a long time"""
        recent_alert = await self._check_recent_alert(
            alert_type="no_scans",
            hours=4
        )
        
        if recent_alert:
            return
        
        message = (
            f"🔴 *No Scans Running*\n"
            f"Last scan: {hours_since_last_scan} hours ago\n"
            f"Time: {datetime.now(timezone.utc).isoformat()}\n"
            f"Action: Check daemon status"
        )
        
        await self._send_alert(message, alert_type="no_scans")
        logger.critical(f"Alert sent: No scans for {hours_since_last_scan} hours")
    
    async def alert_database_error(self, error: str):
        """Alert on database connection or operation errors"""
        recent_alert = await self._check_recent_alert(
            alert_type="database_error",
            hours=1
        )
        
        if recent_alert:
            return
        
        message = (
            f"💥 *Database Error*\n"
            f"Error: {error}\n"
            f"Time: {datetime.now(timezone.utc).isoformat()}\n"
            f"Action: Check MongoDB connection"
        )
        
        await self._send_alert(message, alert_type="database_error")
        logger.critical(f"Alert sent: Database error - {error}")
    
    async def alert_dlq_overflow(self, dlq_count: int, threshold: int = 100):
        """Alert when dead letter queue has too many items"""
        if dlq_count < threshold:
            return
        
        recent_alert = await self._check_recent_alert(
            alert_type="dlq_overflow",
            hours=6
        )
        
        if recent_alert:
            return
        
        message = (
            f"📬 *Dead Letter Queue Alert*\n"
            f"Items in DLQ: {dlq_count}\n"
            f"Threshold: {threshold}\n"
            f"Time: {datetime.now(timezone.utc).isoformat()}\n"
            f"Action: Review and process failed items"
        )
        
        await self._send_alert(message, alert_type="dlq_overflow")
        logger.warning(f"Alert sent: DLQ overflow with {dlq_count} items")
    
    async def alert_threat_detected(
        self,
        hit_id: str,
        brand_name: str,
        source: str,
        source_url: str,
        severity: str,
        confidence: float,
        threat_types: list,
        reasoning: str,
        matched_keywords: list,
    ):
        recent = await self._check_recent_alert(
            alert_type="threat_detected",
            identifier=hit_id,
            hours=24
        )
        if recent:
            return
        
        emoji_map = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}
        emoji = emoji_map.get(severity.upper() if hasattr(severity, 'upper') else str(severity), "⚪")
        severity_str = severity.value if hasattr(severity, 'value') else str(severity)
        
        threats_formatted = "\n".join(f"  • {t}" for t in threat_types) if threat_types else "  • unspecified"
        keywords_formatted = ", ".join(matched_keywords) if matched_keywords else "none"
        source_link = f"<{source_url}|{source}>" if source_url else source
        
        message = (
            f"{emoji} *Threat Detected: {brand_name}*\n\n"
            f"*Severity:* {severity_str}  |  *Confidence:* {confidence:.0%}  |  *Source:* {source_link}\n\n"
            f"*Threat Types:*\n{threats_formatted}\n\n"
            f"*Matched Keywords:* {keywords_formatted}\n\n"
            f"*Analysis:*\n{reasoning[:500]}\n\n"
            f"_{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_"
        )
        
        await self._send_alert(
            message,
            alert_type="threat_detected",
            extra_data={
                "hit_id": hit_id,
                "alert_identifier": hit_id,
                "brand_name": brand_name,
                "severity": severity_str,
                "confidence": confidence,
                "source": source,
            }
        )
        logger.info(f"Threat alert sent: {brand_name} ({severity_str}, {confidence:.0%}) — hit={hit_id}")
    
    async def _send_alert(
        self,
        message: str,
        alert_type: str,
        monitor_name: Optional[str] = None,
        extra_data: Optional[dict] = None,
    ):
        """Send alert via configured channels"""
        if self.slack_webhook_url and self.session:
            try:
                await self._send_slack_alert(message)
            except Exception as e:
                logger.error(f"Failed to send Slack alert: {e}")
        
        await self._record_alert(alert_type, message, monitor_name, extra_data)
    
    async def _send_slack_alert(self, message: str):
        """Send alert to Slack webhook"""
        if not self.session or not self.slack_webhook_url:
            return
        
        payload = {
            "text": message,
            "username": "Brand Intel Monitor",
            "icon_emoji": ":robot_face:"
        }
        
        async with self.session.post(
            self.slack_webhook_url,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status != 200:
                logger.error(f"Slack webhook returned status {response.status}")
    
    async def _record_alert(
        self,
        alert_type: str,
        message: str,
        monitor_name: Optional[str] = None,
        extra_data: Optional[dict] = None,
    ):
        """Record alert in database"""
        try:
            doc = {
                "alert_type": alert_type,
                "message": message,
                "created_at": datetime.now(timezone.utc)
            }
            if monitor_name:
                doc["monitor_name"] = monitor_name
            if extra_data:
                doc.update(extra_data)
            await self.db.alerts.insert_one(doc)
        except Exception as e:
            logger.error(f"Failed to record alert in database: {e}")
    
    async def _check_recent_alert(
        self,
        alert_type: str,
        monitor_name: Optional[str] = None,
        identifier: Optional[str] = None,
        hours: int = 1
    ) -> bool:
        """
        Check if similar alert was sent recently.
        
        Returns:
            True if recent alert exists (skip sending), False otherwise
        """
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            query = {
                "alert_type": alert_type,
                "created_at": {"$gte": cutoff}
            }
            
            if monitor_name:
                query["monitor_name"] = monitor_name
            if identifier:
                query["alert_identifier"] = identifier
            
            recent = await self.db.alerts.find_one(query)
            return recent is not None
        except Exception as e:
            logger.error(f"Failed to check recent alerts: {e}")
            return False
    
    async def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        cursor = self.db.alerts.find(
            {"created_at": {"$gte": cutoff}}
        ).sort("created_at", -1)
        
        return await cursor.to_list(length=100)
    
    async def clear_old_alerts(self, days: int = 30):
        """Clear alerts older than specified days"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.db.alerts.delete_many(
            {"created_at": {"$lt": cutoff}}
        )
        logger.info(f"Cleared {result.deleted_count} old alerts")

# Made with Bob
