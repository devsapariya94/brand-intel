"""Retry logic with exponential backoff for monitor operations"""
import asyncio
import logging
import random
from functools import wraps
from typing import Callable, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_backoff: bool = True
    jitter: bool = True


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator for adding retry logic to async functions.
    Uses exponential backoff with jitter.
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                    
                except Exception as e:
                    last_exception = e
                    
                    if attempt == config.max_retries:
                        raise
                    
                    if config.exponential_backoff:
                        delay = min(
                            config.base_delay * (2 ** attempt),
                            config.max_delay
                        )
                    else:
                        delay = config.base_delay
                    
                    if config.jitter:
                        jitter_amount = delay * 0.2 * (random.random() - 0.5)
                        delay += jitter_amount
                    
                    logger.warning(
                        f"Retry attempt {attempt + 1}/{config.max_retries} "
                        f"after {delay:.2f}s for {func.__name__}: {str(e)}"
                    )
                    
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator
