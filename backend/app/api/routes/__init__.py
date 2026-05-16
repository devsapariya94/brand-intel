"""API routes"""
from .brands import router as brands_router
from .monitors import router as monitors_router
from .hits import router as hits_router
from .health import router as health_router
from .enrichment import router as enrichment_router
from .admin import router as admin_router

__all__ = [
    "brands_router",
    "monitors_router",
    "hits_router",
    "health_router",
    "enrichment_router",
    "admin_router",
]

# Made with Bob
