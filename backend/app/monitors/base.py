"""Base monitor architecture for all data source monitors"""
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RawHit(BaseModel):
    """Standardized output from all monitors"""
    source: str
    source_url: str
    raw_content: str
    metadata: Dict[str, Any]
    detected_at: datetime


class MonitorConfig(BaseModel):
    """Configuration for each monitor"""
    enabled: bool = True
    rate_limit_per_minute: int = 60
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: int = 5


class BaseMonitor(ABC):
    """Abstract base class for all monitors"""
    
    def __init__(self, config: MonitorConfig):
        self.config = config
        self.name = self.__class__.__name__
        self._api_calls_count = 0
        self._last_run_time: Optional[datetime] = None
    
    @abstractmethod
    async def search(self, brand: Dict[str, Any]) -> List[RawHit]:
        """
        Search for brand mentions in the data source.
        
        Args:
            brand: Brand configuration dict from MongoDB
            
        Returns:
            List of RawHit objects
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the monitor's data source is accessible"""
        pass
    
    @abstractmethod
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Return current rate limit status"""
        pass
    
    async def run(self, brand: Dict[str, Any]) -> List[RawHit]:
        """
        Main entry point with error handling and logging.
        """
        try:
            if not await self.is_available():
                logger.warning(f"{self.name} is not available, skipping")
                return []
            
            hits = await self.search(brand)
            self._last_run_time = datetime.now(timezone.utc)
            return hits
            
        except Exception as e:
            logger.error(f"Error in {self.name}: {str(e)}", exc_info=True)
            raise
    
    async def close(self):
        """Override in subclasses to close resources like HTTP sessions"""
        pass
    
    def increment_api_calls(self):
        """Increment API call counter"""
        self._api_calls_count += 1
    
    def get_api_calls_count(self) -> int:
        """Get total API calls made"""
        return self._api_calls_count
    
    def get_last_run_time(self) -> Optional[datetime]:
        """Get last successful run time"""
        return self._last_run_time
