#!/usr/bin/env python3
"""
Brand Intel Monitoring Daemon

Entry point for the background monitoring service that continuously
tracks data for registered brands.

Usage:
    python daemon.py

Environment Variables:
    MONGODB_URI - MongoDB connection string
    SCAN_INTERVAL_MINUTES - Scan frequency (default: 15)
    MAX_CONCURRENT_BRANDS - Concurrent brand scans (default: 10)
    SLACK_WEBHOOK_URL - Slack webhook for alerts (optional)
    LOG_LEVEL - Logging level (default: INFO)
    
    See app/daemon/config.py for full list of configuration options.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.daemon.scheduler import MonitoringDaemon
from app.daemon.config import DaemonConfig


def setup_logging(config: DaemonConfig):
    """Configure logging"""
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format=config.log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('daemon.log')
        ]
    )
    
    # Set specific loggers
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    logging.getLogger('motor').setLevel(logging.WARNING)
    logging.getLogger('pymongo').setLevel(logging.WARNING)


async def main():
    """Main entry point"""
    # Load configuration
    config = DaemonConfig.from_env()
    
    # Setup logging
    setup_logging(config)
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Brand Intel Monitoring Daemon")
    logger.info("=" * 60)
    logger.info(f"MongoDB URI: {config.mongodb_uri}")
    logger.info(f"Scan Interval: {config.scan_interval_minutes} minutes")
    logger.info(f"Max Concurrent Brands: {config.max_concurrent_brands}")
    logger.info(f"Circuit Breaker: {'Enabled' if config.circuit_breaker_enabled else 'Disabled'}")
    logger.info(f"Alerting: {'Configured' if config.slack_webhook_url else 'Not Configured'}")
    logger.info(f"DLQ: {'Enabled' if config.dlq_enabled else 'Disabled'}")
    logger.info("=" * 60)
    
    # Create and run daemon
    daemon = MonitoringDaemon(config)
    
    try:
        await daemon.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
        sys.exit(0)

# Made with Bob
