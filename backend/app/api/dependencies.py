"""Shared dependencies for FastAPI routes"""
from typing import AsyncGenerator, Optional, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from fastapi import Depends
import os

from ..daemon.config import DaemonConfig
from ..monitors.orchestrator import MonitorOrchestrator
from ..monitors.storage import RawHitStorage
from ..monitors.detector import KeywordMatcher
from ..daemon.circuit_breaker import CircuitBreaker
from ..daemon.dlq import DeadLetterQueue


# Global state (initialized in main.py)
_db_client: Optional[AsyncIOMotorClient] = None
_orchestrator: Optional[MonitorOrchestrator] = None
_circuit_breaker: Optional[CircuitBreaker] = None
_dlq: Optional[DeadLetterQueue] = None
_config: Optional[DaemonConfig] = None
_enrichment_service: Optional[Any] = None


def set_db_client(client: AsyncIOMotorClient):
    """Set the global database client"""
    global _db_client
    _db_client = client


def set_orchestrator(orchestrator: MonitorOrchestrator):
    """Set the global orchestrator"""
    global _orchestrator
    _orchestrator = orchestrator


def set_circuit_breaker(circuit_breaker: CircuitBreaker):
    """Set the global circuit breaker"""
    global _circuit_breaker
    _circuit_breaker = circuit_breaker


def set_dlq(dlq: DeadLetterQueue):
    """Set the global DLQ"""
    global _dlq
    _dlq = dlq


def set_config(config: DaemonConfig):
    """Set the global config"""
    global _config
    _config = config


def set_enrichment_service(service):
    """Set the global enrichment service"""
    global _enrichment_service
    _enrichment_service = service


async def get_database() -> AsyncIOMotorDatabase:
    """Get database dependency"""
    if _db_client is None:
        raise RuntimeError("Database client not initialized")
    return _db_client.brand_intel


async def get_orchestrator() -> MonitorOrchestrator:
    """Get orchestrator dependency"""
    if _orchestrator is None:
        raise RuntimeError("Orchestrator not initialized")
    return _orchestrator


async def get_circuit_breaker() -> Optional[CircuitBreaker]:
    """Get circuit breaker dependency"""
    return _circuit_breaker


async def get_dlq() -> Optional[DeadLetterQueue]:
    """Get DLQ dependency"""
    return _dlq


async def get_config() -> DaemonConfig:
    """Get config dependency"""
    if _config is None:
        raise RuntimeError("Config not initialized")
    return _config


async def get_enrichment_service():
    """Get enrichment service dependency"""
    return _enrichment_service


async def get_storage(db: AsyncIOMotorDatabase = Depends(get_database)) -> RawHitStorage:
    """Get storage dependency"""
    return RawHitStorage(_db_client)


async def get_matcher() -> KeywordMatcher:
    """Get keyword matcher dependency"""
    return KeywordMatcher()

# Made with Bob
