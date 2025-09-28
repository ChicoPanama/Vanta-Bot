"""Vanta Bot entrypoint with robust async startup orchestration."""

from __future__ import annotations

import asyncio
import contextlib
import signal
import sys
from typing import Optional

from src.bot.application import create_bot_application
from src.config.settings import settings
from src.config.flags import flags
from src.config.validate import validate_all
from src.monitoring.health_server import HealthChecker, start_health_server
from src.services.background import BackgroundServiceManager
from src.utils.errors import handle_exception
from src.utils.logging import get_logger, set_trace_id, setup_logging
from src.utils.supervisor import TaskManager

setup_logging()
logger = get_logger(__name__)


async def _run_application(stop_event: asyncio.Event) -> None:
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


async def _run_development() -> None:
    """Run the bot in development mode with supervised background services."""
    trace_id = set_trace_id()
    logger.info("🔧 Development mode detected - starting basic services", extra={"trace_id": trace_id})

    background_manager = BackgroundServiceManager()
    await background_manager.start_all_services()
    logger.info("✅ Background services started successfully", extra={"trace_id": trace_id})

    stop_event = asyncio.Event()
    polling_task = asyncio.create_task(_run_application(stop_event), name="telegram.polling")

    try:
        await asyncio.Future()  # run until cancelled (KeyboardInterrupt)
    except asyncio.CancelledError:
        logger.info("🔻 Shutdown signal received", extra={"trace_id": trace_id})
    finally:
        stop_event.set()
        polling_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await polling_task
        await background_manager.stop_all_services()
        logger.info("✅ Development shutdown complete", extra={"trace_id": trace_id})


async def _supervised_background_services(task_manager: TaskManager) -> None:
    background_manager = BackgroundServiceManager()
    task_manager.add_task(
        lambda: background_manager.start_all_services(),
        "background.services",
        base_delay=2.0,
        max_delay=30.0,
    )
    await task_manager.start_all()
    logger.info("✅ Production services started successfully")

    try:
        await asyncio.Future()  # wait until cancelled
    except asyncio.CancelledError:
        logger.info("🔻 Production shutdown requested")
    finally:
        await task_manager.shutdown_all()
        await background_manager.stop_all_services()
        logger.info("✅ Background services stopped")


async def _run_production() -> None:
    """Run the bot with production supervisors and health server."""
    trace_id = set_trace_id()
    logger.info("🏭 Production mode detected - starting supervised services", extra={"trace_id": trace_id})

    task_manager = TaskManager()
    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()

    def _request_shutdown() -> None:
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, _request_shutdown)

    health_checker = HealthChecker()
    health_runner = await start_health_server(health_checker)

    supervisor_task = asyncio.create_task(
        _supervised_background_services(task_manager),
        name="background.supervisor",
    )

    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        stop_event.set()
        logger.info("🔻 Production shutdown requested", extra={"trace_id": trace_id})
    finally:
        supervisor_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await supervisor_task
        await health_runner.cleanup()
        logger.info("✅ Production shutdown complete", extra={"trace_id": trace_id})


async def _async_main() -> None:
    trace_id = set_trace_id()
    logger.info("🔐 Validating critical secrets and configuration...")
    validate_all()
    logger.info("✅ Configuration validation passed")

    logger.info("🚀 Starting Vanta Bot with Production Hardening...", extra={"trace_id": trace_id})
    logger.info(settings.runtime_summary())
    logger.info(flags.get_status_summary())

    if settings.is_production():
        await _run_production()
    else:
        await _run_development()


def main() -> None:
    """Program entry point."""
    try:
        asyncio.run(_async_main())
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown requested by user")
    except Exception as exc:  # noqa: BLE001
        error = handle_exception(exc, {"operation": "main"})
        logger.error(f"❌ Failed to start bot: {error.message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
