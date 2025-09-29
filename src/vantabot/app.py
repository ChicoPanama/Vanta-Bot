"""Vanta Bot application factory with dependency injection."""

from __future__ import annotations

import asyncio
import contextlib
import signal
from typing import Optional

from src.bot.application import create_bot_application
from src.config.settings import settings
from src.config.flags import flags
from src.config.validate import validate_all
from src.services.background import BackgroundServiceManager
from src.services.copy_trading.execution_mode import execution_manager
from src.utils.errors import handle_exception
from src.utils.logging import get_logger, set_trace_id, setup_logging
from src.utils.supervisor import TaskManager


class VantaBotApp:
    """Main application class that orchestrates all services."""
    
    def __init__(self):
        setup_logging()
        self.logger = get_logger(__name__)
        self._background_manager: Optional[BackgroundServiceManager] = None
        self._task_manager: Optional[TaskManager] = None
        
    async def start_health_server(self):
        """Start the FastAPI health app in-process via uvicorn and return a runner with cleanup()."""
        import uvicorn
        from src.monitoring.health_server import app as health_app

        config = uvicorn.Config(
            health_app,
            host="0.0.0.0",
            port=settings.HEALTH_PORT,
            log_level="info",
            loop="asyncio",
        )
        server = uvicorn.Server(config)

        task = asyncio.create_task(server.serve(), name="uvicorn.health")

        class _Runner:
            async def cleanup(self) -> None:
                server.should_exit = True
                with contextlib.suppress(Exception):
                    await task

        return _Runner()

    async def _run_application(self, stop_event: asyncio.Event) -> None:
        """Run the Telegram application until *stop_event* is set."""
        app = await create_bot_application()
        try:
            await app.initialize()
            await app.start()
            await app.updater.start_polling()
            await stop_event.wait()
        finally:
            with contextlib.suppress(Exception):
                await app.updater.stop()
                await app.stop()
                await app.shutdown()

    async def _run_development(self) -> None:
        """Run the bot in development mode with supervised background services."""
        trace_id = set_trace_id()
        self.logger.info("🔧 Development mode detected - starting basic services", extra={"trace_id": trace_id})

        self._background_manager = BackgroundServiceManager()
        await self._background_manager.start_all_services()
        self.logger.info("✅ Background services started successfully", extra={"trace_id": trace_id})

        stop_event = asyncio.Event()
        polling_task = asyncio.create_task(self._run_application(stop_event), name="telegram.polling")

        try:
            await asyncio.Future()  # run until cancelled (KeyboardInterrupt)
        except asyncio.CancelledError:
            self.logger.info("🔻 Shutdown signal received", extra={"trace_id": trace_id})
        finally:
            stop_event.set()
            polling_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await polling_task
            await self._background_manager.stop_all_services()
            self.logger.info("✅ Development shutdown complete", extra={"trace_id": trace_id})

    async def _periodic_redis_refresh(self) -> None:
        """Periodically refresh execution mode from Redis for cluster coordination."""
        from src.config.feeds_config import get_feeds_config
        import os
        
        # Get refresh interval from config (default 5s)
        feeds_config = get_feeds_config()
        execution_config = feeds_config.get_execution_mode_config()
        config_interval = execution_config.get('refresh_interval_seconds', 5)
        
        # Allow environment override for ops flexibility
        env_interval = os.getenv('EXEC_MODE_REFRESH_S')
        if env_interval:
            try:
                refresh_interval = int(env_interval)
                self.logger.info(f"🔄 Using environment override for Redis refresh: {refresh_interval}s")
            except ValueError:
                refresh_interval = config_interval
                self.logger.warning(f"Invalid EXEC_MODE_REFRESH_S value '{env_interval}', using config: {refresh_interval}s")
        else:
            refresh_interval = config_interval
            self.logger.info(f"🔄 Starting Redis refresh with {refresh_interval}s interval (from config)")
        
        while True:
            try:
                execution_manager.refresh_from_redis()
                await asyncio.sleep(refresh_interval)
            except asyncio.CancelledError:
                self.logger.info("🔄 Redis refresh task cancelled")
                break
            except Exception as e:
                self.logger.warning(f"Redis refresh failed: {e}")
                await asyncio.sleep(refresh_interval * 2)  # Wait longer on error

    async def _supervised_background_services(self, task_manager: TaskManager) -> None:
        self._background_manager = BackgroundServiceManager()
        task_manager.add_task(
            lambda: self._background_manager.start_all_services(),
            "background.services",
            base_delay=2.0,
            max_delay=30.0,
        )
        await task_manager.start_all()
        self.logger.info("✅ Production services started successfully")

        try:
            await asyncio.Future()  # wait until cancelled
        except asyncio.CancelledError:
            self.logger.info("🔻 Production shutdown requested")
        finally:
            await task_manager.shutdown_all()
            await self._background_manager.stop_all_services()
            self.logger.info("✅ Background services stopped")

    async def _run_production(self) -> None:
        """Run the bot with production supervisors and health server."""
        trace_id = set_trace_id()
        self.logger.info("🏭 Production mode detected - starting supervised services", extra={"trace_id": trace_id})

        self._task_manager = TaskManager()
        stop_event = asyncio.Event()

        loop = asyncio.get_running_loop()

        def _request_shutdown() -> None:
            stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(sig, _request_shutdown)

        # Start FastAPI health server via uvicorn (background)
        health_runner = await self.start_health_server()

        supervisor_task = asyncio.create_task(
            self._supervised_background_services(self._task_manager),
            name="background.supervisor",
        )
        
        # Periodic Redis refresh for cluster coordination
        redis_refresh_task = asyncio.create_task(
            self._periodic_redis_refresh(),
            name="redis.refresh",
        )

        try:
            await stop_event.wait()
        except asyncio.CancelledError:
            stop_event.set()
            self.logger.info("🔻 Production shutdown requested", extra={"trace_id": trace_id})
        finally:
            supervisor_task.cancel()
            redis_refresh_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await supervisor_task
            with contextlib.suppress(asyncio.CancelledError):
                await redis_refresh_task
            await health_runner.cleanup()
            self.logger.info("✅ Production shutdown complete", extra={"trace_id": trace_id})

    async def run(self) -> None:
        """Main application runner."""
        trace_id = set_trace_id()
        self.logger.info("🔐 Validating critical secrets and configuration...")
        validate_all()
        self.logger.info("✅ Configuration validation passed")

        self.logger.info("🚀 Starting Vanta Bot with Production Hardening...", extra={"trace_id": trace_id})
        self.logger.info(settings.runtime_summary())
        self.logger.info(flags.get_status_summary())

        if settings.is_production():
            await self._run_production()
        else:
            await self._run_development()


def create_app() -> VantaBotApp:
    """Factory function to create the Vanta Bot application."""
    return VantaBotApp()
