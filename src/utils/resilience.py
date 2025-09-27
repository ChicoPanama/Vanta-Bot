from __future__ import annotations
import asyncio
import time
from typing import Callable, Type, Tuple, Any, Optional

class CircuitBreaker:
    def __init__(self, fail_threshold: int = 5, reset_after: float = 30.0):
        self.fail_threshold = fail_threshold
        self.reset_after = reset_after
        self.failures = 0
        self.opened_at: Optional[float] = None

    def is_open(self) -> bool:
        if self.opened_at is None:
            return False
        if (time.time() - self.opened_at) >= self.reset_after:
            # half-open
            self.failures = 0
            self.opened_at = None
            return False
        return True

    def mark_success(self):
        self.failures = 0
        self.opened_at = None

    def mark_failure(self):
        self.failures += 1
        if self.failures >= self.fail_threshold and self.opened_at is None:
            self.opened_at = time.time()

async def with_timeout(coro, seconds: float):
    return await asyncio.wait_for(coro, timeout=seconds)

async def with_retries(
    fn: Callable[[], Any],
    retries: int = 3,
    backoff: float = 0.5,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
):
    last = None
    for i in range(retries + 1):
        try:
            return await fn()
        except exceptions as e:
            last = e
            if i == retries:
                raise
            await asyncio.sleep(backoff * (2 ** i))
    raise last  # pragma: no cover

async def guarded_call(
    breaker: CircuitBreaker,
    fn: Callable[[], Any],
    timeout_s: float = 6.0,
    retries: int = 2,
):
    if breaker.is_open():
        raise RuntimeError("circuit_open")

    try:
        res = await with_retries(lambda: with_timeout(fn(), timeout_s), retries=retries)
        breaker.mark_success()
        return res
    except Exception as e:
        breaker.mark_failure()
        logger.warning(f"Circuit breaker failure in {func.__name__}: {e}")
        raise
