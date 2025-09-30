"""Resilience utilities: circuit breaker & guarded async execution."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable
from typing import Any, Callable

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Simple circuit breaker to protect fragile dependencies."""

    def __init__(self, fail_threshold: int = 5, reset_after: float = 30.0) -> None:
        self.fail_threshold = fail_threshold
        self.reset_after = reset_after
        self.failures = 0
        self.opened_at: float | None = None

    def is_open(self) -> bool:
        if self.opened_at is None:
            return False
        if (time.time() - self.opened_at) >= self.reset_after:
            self.failures = 0
            self.opened_at = None
            return False
        return True

    def mark_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def mark_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.fail_threshold and self.opened_at is None:
            self.opened_at = time.time()


async def with_timeout(coro: Awaitable[Any], seconds: float) -> Any:
    """Await *coro* with a timeout."""
    return await asyncio.wait_for(coro, timeout=seconds)


async def with_retries(
    fn: Callable[[], Awaitable[Any]],
    *,
    retries: int = 3,
    backoff: float = 0.5,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Any:
    """Retry *fn* with exponential backoff."""
    last_exc: BaseException | None = None
    for attempt in range(retries + 1):
        try:
            return await fn()
        except exceptions as exc:  # noqa: PERF203 - explicit clarity
            last_exc = exc
            if attempt == retries:
                raise
            await asyncio.sleep(backoff * (2**attempt))
    if last_exc is not None:  # pragma: no cover - defensive
        raise last_exc
    raise RuntimeError("with_retries exhausted without executing fn")


async def guarded_call(
    breaker: CircuitBreaker,
    fn: Callable[[], Awaitable[Any]],
    *,
    timeout_s: float = 6.0,
    retries: int = 2,
) -> Any:
    """Execute *fn* respecting the circuit breaker and retry semantics."""
    if breaker.is_open():
        raise RuntimeError("circuit_open")

    operation = getattr(fn, "__name__", repr(fn))

    async def _with_timeout() -> Any:
        return await with_timeout(fn(), timeout_s)

    try:
        result = await with_retries(_with_timeout, retries=retries)
        breaker.mark_success()
        logger.debug("guarded_call success", extra={"operation": operation})
        return result
    except Exception as exc:  # noqa: BLE001
        breaker.mark_failure()
        logger.warning(
            "guarded_call failure",
            extra={"operation": operation, "error": str(exc)},
            exc_info=exc,
        )
        raise


__all__ = ["CircuitBreaker", "guarded_call", "with_retries", "with_timeout"]
