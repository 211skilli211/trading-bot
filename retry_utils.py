#!/usr/bin/env python3
"""
Retry Utilities with Exponential Backoff
For resilient API calls to exchanges
"""

import time
import random
import logging
from functools import wraps
from typing import Callable, TypeVar, Optional, Tuple, List
from requests.exceptions import RequestException, Timeout, ConnectionError

T = TypeVar('T')
logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Tuple[type, ...] = (RequestException, Timeout, ConnectionError)
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate delay with exponential backoff and optional jitter.
    
    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration
        
    Returns:
        Delay in seconds
    """
    # Exponential backoff: base_delay * (base ^ attempt)
    delay = config.base_delay * (config.exponential_base ** attempt)
    
    # Cap at max_delay
    delay = min(delay, config.max_delay)
    
    # Add jitter (±25%) to prevent thundering herd
    if config.jitter:
        jitter_factor = random.uniform(0.75, 1.25)
        delay *= jitter_factor
    
    return delay


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator for adding retry logic to functions.
    
    Args:
        config: Retry configuration (uses default if None)
        
    Example:
        @with_retry(RetryConfig(max_retries=5))
        def fetch_prices():
            return requests.get(url)
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(config.max_retries):
                try:
                    result = func(*args, **kwargs)
                    
                    # Log successful retry
                    if attempt > 0:
                        logger.info(f"{func.__name__} succeeded on attempt {attempt + 1}")
                    
                    return result
                    
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt < config.max_retries - 1:
                        delay = calculate_delay(attempt, config)
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{config.max_retries}): {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {config.max_retries} attempts: {e}"
                        )
                        raise
            
            # Should never reach here, but just in case
            raise last_exception or RuntimeError("Retry loop exited unexpectedly")
        
        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascade failures.
    
    States:
    - CLOSED: Normal operation
    - OPEN: Failing fast (too many errors)
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.half_open_calls = 0
    
    def can_execute(self) -> bool:
        """Check if execution should proceed."""
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            # Check if recovery timeout has passed
            if self.last_failure_time and \
               (time.time() - self.last_failure_time) >= self.recovery_timeout:
                logger.info("Circuit breaker entering HALF_OPEN state")
                self.state = "HALF_OPEN"
                self.half_open_calls = 0
                return True
            
            logger.warning("Circuit breaker is OPEN - failing fast")
            return False
        
        if self.state == "HALF_OPEN":
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False
        
        return True
    
    def record_success(self):
        """Record a successful execution."""
        if self.state == "HALF_OPEN":
            logger.info("Circuit breaker closing - service recovered")
            self.state = "CLOSED"
            self.failure_count = 0
            self.half_open_calls = 0
        elif self.state == "CLOSED":
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Record a failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == "HALF_OPEN":
            logger.warning("Circuit breaker reopening - service still failing")
            self.state = "OPEN"
        elif self.state == "CLOSED" and self.failure_count >= self.failure_threshold:
            logger.error(f"Circuit breaker opening after {self.failure_count} failures")
            self.state = "OPEN"
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Use as decorator."""
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            if not self.can_execute():
                raise RuntimeError(f"Circuit breaker is {self.state}")
            
            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise
        
        return wrapper


# Pre-configured retry settings for different scenarios
RETRY_FAST = RetryConfig(max_retries=3, base_delay=0.5, max_delay=5.0)
RETRY_STANDARD = RetryConfig(max_retries=3, base_delay=1.0, max_delay=30.0)
RETRY_SLOW = RetryConfig(max_retries=5, base_delay=2.0, max_delay=60.0)
RETRY_NETWORK = RetryConfig(
    max_retries=5,
    base_delay=1.0,
    max_delay=60.0,
    retryable_exceptions=(RequestException, Timeout, ConnectionError, OSError)
)


# Example usage
if __name__ == "__main__":
    print("Retry Utils Test")
    print("=" * 60)
    
    # Test delay calculation
    config = RetryConfig(base_delay=1.0, exponential_base=2.0)
    print("\nDelay calculations:")
    for i in range(5):
        delay = calculate_delay(i, config)
        print(f"  Attempt {i+1}: {delay:.2f}s")
    
    # Test with jitter
    config_jitter = RetryConfig(base_delay=1.0, jitter=True)
    print("\nWith jitter (10 samples):")
    for _ in range(10):
        print(f"  {calculate_delay(1, config_jitter):.2f}s", end=" ")
    print()
    
    # Test circuit breaker
    print("\nCircuit breaker test:")
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)
    
    for i in range(5):
        can_exec = cb.can_execute()
        print(f"  Call {i+1}: state={cb.state}, can_execute={can_exec}")
        
        if i < 3:  # Simulate failures
            cb.record_failure()
        else:
            cb.record_success()
    
    print("\n" + "=" * 60)
