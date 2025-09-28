"""Circuit breaker implementation for external service calls."""

import time
import logging
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class SimpleBreaker:
    """Simple circuit breaker for protecting external service calls."""
    
    def __init__(self, 
                 fail_threshold: int = 5, 
                 reset_after: int = 30,
                 name: str = "circuit_breaker"):
        self.fail_threshold = fail_threshold
        self.reset_after = reset_after
        self.name = name
        self.fail_count = 0
        self.open_until = 0
        self.last_failure_time = 0

    def call(self, fn: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection.
        
        Args:
            fn: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            RuntimeError: If circuit breaker is open
            Exception: Original exception from function
        """
        now = time.time()
        
        # Check if circuit is open
        if now < self.open_until:
            logger.warning(f"Circuit breaker {self.name} is OPEN, rejecting call")
            raise RuntimeError(f"Circuit breaker {self.name} is open until {self.open_until}")
        
        try:
            # Execute function
            result = fn(*args, **kwargs)
            
            # Success - reset failure count
            if self.fail_count > 0:
                logger.info(f"Circuit breaker {self.name} recovered, resetting failure count")
                self.fail_count = 0
            
            return result
            
        except Exception as e:
            # Failure - increment count and potentially open circuit
            self.fail_count += 1
            self.last_failure_time = now
            
            logger.warning(f"Circuit breaker {self.name} failure {self.fail_count}/{self.fail_threshold}: {e}")
            
            if self.fail_count >= self.fail_threshold:
                self.open_until = now + self.reset_after
                logger.error(f"Circuit breaker {self.name} OPEN until {self.open_until}")
            
            raise

    def is_open(self) -> bool:
        """Check if circuit breaker is currently open."""
        return time.time() < self.open_until

    def reset(self):
        """Manually reset the circuit breaker."""
        self.fail_count = 0
        self.open_until = 0
        self.last_failure_time = 0
        logger.info(f"Circuit breaker {self.name} manually reset")


class CircuitBreakerManager:
    """Manages multiple circuit breakers for different services."""
    
    def __init__(self):
        self.breakers: dict[str, SimpleBreaker] = {}

    def get_breaker(self, service_name: str, **kwargs) -> SimpleBreaker:
        """Get or create circuit breaker for service.
        
        Args:
            service_name: Name of the service
            **kwargs: Circuit breaker configuration
            
        Returns:
            Circuit breaker instance
        """
        if service_name not in self.breakers:
            self.breakers[service_name] = SimpleBreaker(name=service_name, **kwargs)
        
        return self.breakers[service_name]

    def reset_all(self):
        """Reset all circuit breakers."""
        for breaker in self.breakers.values():
            breaker.reset()
        logger.info("All circuit breakers reset")

    def get_status(self) -> dict:
        """Get status of all circuit breakers."""
        now = time.time()
        return {
            name: {
                "is_open": breaker.is_open(),
                "fail_count": breaker.fail_count,
                "open_until": breaker.open_until,
                "time_until_reset": max(0, breaker.open_until - now) if breaker.is_open() else 0
            }
            for name, breaker in self.breakers.items()
        }


def circuit_breaker(service_name: str, **breaker_kwargs):
    """Decorator to add circuit breaker protection to functions.
    
    Args:
        service_name: Name of the service being protected
        **breaker_kwargs: Circuit breaker configuration
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get global circuit breaker manager
            # This would be injected in a real implementation
            manager = CircuitBreakerManager()
            breaker = manager.get_breaker(service_name, **breaker_kwargs)
            
            return breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator


# Global circuit breaker manager instance
circuit_breaker_manager = CircuitBreakerManager()
