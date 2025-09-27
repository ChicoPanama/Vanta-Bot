"""
Task Supervisor with Graceful Shutdown
Provides supervised task management with automatic restart and graceful shutdown capabilities
"""

import asyncio
import random
import logging
import signal
from typing import Callable, Any, Optional

log = logging.getLogger(__name__)


class SupervisedTask:
    def __init__(self, coro_factory: Callable, name: str, base_delay: float = 1.0, max_delay: float = 30.0):
        self.coro_factory = coro_factory
        self.name = name
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.task: Optional[asyncio.Task] = None
        self.shutdown_event = asyncio.Event()
        
    async def run(self):
        backoff = self.base_delay
        while not self.shutdown_event.is_set():
            try:
                log.info("task.start %s", self.name)
                await self.coro_factory()
            except asyncio.CancelledError:
                log.info("task.cancel %s", self.name)
                raise
            except Exception as e:
                log.exception("task.crash %s: %s", self.name, e)
                
            if not self.shutdown_event.is_set():
                jitter = random.uniform(0, 1)
                delay = min(self.max_delay, backoff + jitter)
                log.info("task.restart %s in %.2fs", self.name, delay)
                
                try:
                    await asyncio.wait_for(self.shutdown_event.wait(), timeout=delay)
                    break  # Shutdown requested
                except asyncio.TimeoutError:
                    pass  # Continue with restart
                    
                backoff = min(self.max_delay, backoff * 2)
    
    def start(self):
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self.run())
        return self.task
    
    async def stop(self):
        self.shutdown_event.set()
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass


class TaskManager:
    def __init__(self):
        self.tasks: list[SupervisedTask] = []
        self._shutdown_event = asyncio.Event()
    
    def add_task(self, coro_factory: Callable, name: str, **kwargs):
        task = SupervisedTask(coro_factory, name, **kwargs)
        self.tasks.append(task)
        return task
    
    async def start_all(self):
        for task in self.tasks:
            task.start()
    
    async def shutdown_all(self):
        self._shutdown_event.set()
        log.info("Shutting down %d supervised tasks", len(self.tasks))
        
        # Stop all tasks concurrently
        stop_tasks = [task.stop() for task in self.tasks]
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        log.info("All supervised tasks stopped")
    
    def setup_signal_handlers(self):
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda s, f: asyncio.create_task(self.shutdown_all()))
