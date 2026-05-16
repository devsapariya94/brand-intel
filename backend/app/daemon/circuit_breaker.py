"""Circuit breaker pattern to prevent cascading failures"""
import time
import logging
from typing import Dict, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class CircuitBreakerState:
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.
    
    When a monitor fails repeatedly, the circuit opens and prevents
    further attempts for a timeout period. After timeout, it enters
    half-open state to test if the service recovered.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 300,
        success_threshold: int = 2
    ):
        """
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Time to wait before trying again (half-open)
            success_threshold: Successes needed in half-open to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.success_threshold = success_threshold
        
        # State per monitor
        self.states: Dict[str, str] = {}
        self.failure_counts: Dict[str, int] = {}
        self.success_counts: Dict[str, int] = {}
        self.opened_at: Dict[str, float] = {}
        self.last_failure_time: Dict[str, datetime] = {}
    
    def should_allow(self, monitor_name: str) -> bool:
        """
        Check if request should be allowed through circuit breaker.
        
        Returns:
            True if request should proceed, False if circuit is open
        """
        state = self.states.get(monitor_name, CircuitBreakerState.CLOSED)
        
        if state == CircuitBreakerState.CLOSED:
            return True
        
        if state == CircuitBreakerState.OPEN:
            # Check if timeout has passed
            opened_time = self.opened_at.get(monitor_name, 0)
            if time.time() - opened_time >= self.timeout_seconds:
                # Move to half-open state
                self.states[monitor_name] = CircuitBreakerState.HALF_OPEN
                self.success_counts[monitor_name] = 0
                logger.info(f"Circuit breaker for {monitor_name} entering HALF_OPEN state")
                return True
            
            logger.warning(f"Circuit breaker OPEN for {monitor_name}, rejecting request")
            return False
        
        if state == CircuitBreakerState.HALF_OPEN:
            # Allow request in half-open state to test
            return True
        
        return True
    
    def record_success(self, monitor_name: str):
        """Record successful operation"""
        state = self.states.get(monitor_name, CircuitBreakerState.CLOSED)
        
        if state == CircuitBreakerState.HALF_OPEN:
            self.success_counts[monitor_name] = self.success_counts.get(monitor_name, 0) + 1
            
            if self.success_counts[monitor_name] >= self.success_threshold:
                # Close circuit - service recovered
                self.states[monitor_name] = CircuitBreakerState.CLOSED
                self.failure_counts[monitor_name] = 0
                self.success_counts[monitor_name] = 0
                if monitor_name in self.opened_at:
                    del self.opened_at[monitor_name]
                logger.info(f"Circuit breaker for {monitor_name} CLOSED - service recovered")
        
        elif state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self.failure_counts[monitor_name] = 0
    
    def record_failure(self, monitor_name: str, error: Exception):
        """Record failed operation"""
        state = self.states.get(monitor_name, CircuitBreakerState.CLOSED)
        self.last_failure_time[monitor_name] = datetime.now(timezone.utc)
        
        if state == CircuitBreakerState.HALF_OPEN:
            # Failed in half-open, reopen circuit
            self.states[monitor_name] = CircuitBreakerState.OPEN
            self.opened_at[monitor_name] = time.time()
            self.success_counts[monitor_name] = 0
            logger.warning(f"Circuit breaker for {monitor_name} reopened after failure in HALF_OPEN: {error}")
        
        elif state == CircuitBreakerState.CLOSED:
            self.failure_counts[monitor_name] = self.failure_counts.get(monitor_name, 0) + 1
            
            if self.failure_counts[monitor_name] >= self.failure_threshold:
                # Open circuit
                self.states[monitor_name] = CircuitBreakerState.OPEN
                self.opened_at[monitor_name] = time.time()
                logger.error(
                    f"Circuit breaker OPENED for {monitor_name} after "
                    f"{self.failure_counts[monitor_name]} failures. Last error: {error}"
                )
    
    def get_state(self, monitor_name: str) -> str:
        """Get current state of circuit breaker for a monitor"""
        return self.states.get(monitor_name, CircuitBreakerState.CLOSED)
    
    def get_failure_count(self, monitor_name: str) -> int:
        """Get current failure count"""
        return self.failure_counts.get(monitor_name, 0)
    
    def get_stats(self) -> Dict[str, Dict]:
        """Get statistics for all monitors"""
        stats = {}
        for monitor_name in set(list(self.states.keys()) + list(self.failure_counts.keys())):
            stats[monitor_name] = {
                "state": self.get_state(monitor_name),
                "failure_count": self.get_failure_count(monitor_name),
                "last_failure": self.last_failure_time.get(monitor_name)
            }
        return stats
    
    def reset(self, monitor_name: str):
        """Manually reset circuit breaker for a monitor"""
        if monitor_name in self.states:
            del self.states[monitor_name]
        if monitor_name in self.failure_counts:
            del self.failure_counts[monitor_name]
        if monitor_name in self.success_counts:
            del self.success_counts[monitor_name]
        if monitor_name in self.opened_at:
            del self.opened_at[monitor_name]
        if monitor_name in self.last_failure_time:
            del self.last_failure_time[monitor_name]
        logger.info(f"Circuit breaker for {monitor_name} manually reset")
    
    def reset_all(self):
        """Reset all circuit breakers"""
        self.states.clear()
        self.failure_counts.clear()
        self.success_counts.clear()
        self.opened_at.clear()
        self.last_failure_time.clear()
        logger.info("All circuit breakers reset")

# Made with Bob
