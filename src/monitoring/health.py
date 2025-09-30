"""
Health Check Endpoints
HTTP health check endpoints for monitoring and observability
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import psutil
import redis
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from src.config.settings import settings
from src.services.copy_trading.execution_mode import execution_manager
from src.utils.logging import get_logger, log_system_health

logger = get_logger(__name__)

# Global health check state
_health_state = {"startup_time": time.time(), "last_check": None, "checks": {}}


async def _get_oracle_status() -> dict:
    """Get oracle status for operational visibility."""
    try:
        oracle_status = {
            "execution_mode": execution_manager.get_health_metrics(),
            "oracle_providers": {},
        }

        # Test Pyth oracle
        try:
            from src.services.oracle_providers.pyth import PythOracle

            pyth = PythOracle()
            oracle_status["oracle_providers"]["pyth"] = {
                "status": "available",
                "endpoint": pyth.api_url,
                "symbols": list(pyth.symbol_map.keys()),
            }
        except Exception as e:
            oracle_status["oracle_providers"]["pyth"] = {
                "status": "error",
                "error": str(e),
            }

        # Test Chainlink oracle
        try:
            from web3 import Web3

            from src.services.oracle_providers.chainlink import ChainlinkOracle

            # Add request timeout to avoid health endpoint hangs on RPC issues
            w3 = Web3(
                Web3.HTTPProvider(settings.BASE_RPC_URL, request_kwargs={"timeout": 10})
            )
            # Skip startup validation inside health to keep endpoint responsive
            chainlink = ChainlinkOracle(w3, validate_on_init=False)
            oracle_status["oracle_providers"]["chainlink"] = {
                "status": "available",
                "feeds": list(chainlink.aggregators.keys()),
                "feed_count": len(chainlink.aggregators),
            }
        except Exception as e:
            oracle_status["oracle_providers"]["chainlink"] = {
                "status": "error",
                "error": str(e),
            }

        return oracle_status

    except Exception as e:
        return {"status": "error", "error": str(e)}


class HealthChecker:
    """Health check service for monitoring system components"""

    def __init__(self):
        self.redis_client = None
        self.db_engine = None
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize database and Redis clients for health checks"""
        try:
            # Initialize Redis client
            if settings.REDIS_URL:
                self.redis_client = redis.from_url(settings.REDIS_URL)

            # Initialize database engine
            if settings.DATABASE_URL:
                self.db_engine = create_engine(settings.DATABASE_URL)
        except Exception as e:
            logger.warning(f"Failed to initialize health check clients: {e}")

    async def check_redis(self) -> dict[str, Any]:
        """Check Redis connectivity and performance"""
        if not self.redis_client:
            return {
                "status": "disabled",
                "message": "Redis not configured",
                "response_time_ms": 0,
            }

        start_time = time.time()
        try:
            # Test basic connectivity
            self.redis_client.ping()

            # Test set/get operation
            test_key = f"health_check_{int(time.time())}"
            self.redis_client.set(test_key, "test_value", ex=10)
            value = self.redis_client.get(test_key)
            self.redis_client.delete(test_key)

            if value != b"test_value":
                raise Exception("Redis set/get test failed")

            response_time = (time.time() - start_time) * 1000

            return {
                "status": "healthy",
                "message": "Redis is responding correctly",
                "response_time_ms": round(response_time, 2),
            }

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return {
                "status": "unhealthy",
                "message": f"Redis check failed: {str(e)}",
                "response_time_ms": round(response_time, 2),
            }

    async def check_database(self) -> dict[str, Any]:
        """Check database connectivity and performance"""
        if not self.db_engine:
            return {
                "status": "disabled",
                "message": "Database not configured",
                "response_time_ms": 0,
            }

        start_time = time.time()
        try:
            with self.db_engine.connect() as conn:
                # Test basic connectivity
                result = conn.execute(text("SELECT 1"))
                result.fetchone()

                # Test table existence (if using SQLite, check if tables exist)
                if "sqlite" in settings.DATABASE_URL:
                    result = conn.execute(
                        text("SELECT name FROM sqlite_master WHERE type='table'")
                    )
                    tables = result.fetchall()
                    table_count = len(tables)
                else:
                    # For PostgreSQL, check if we can query information_schema
                    result = conn.execute(
                        text(
                            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
                        )
                    )
                    table_count = result.fetchone()[0]

                response_time = (time.time() - start_time) * 1000

                return {
                    "status": "healthy",
                    "message": f"Database is responding correctly ({table_count} tables)",
                    "response_time_ms": round(response_time, 2),
                    "table_count": table_count,
                }

        except SQLAlchemyError as e:
            response_time = (time.time() - start_time) * 1000
            return {
                "status": "unhealthy",
                "message": f"Database check failed: {str(e)}",
                "response_time_ms": round(response_time, 2),
            }

    async def check_system_resources(self) -> dict[str, Any]:
        """Check system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()

            # Disk usage
            disk = psutil.disk_usage("/")

            # Process info
            process = psutil.Process()
            process_memory = process.memory_info()

            # Determine health status based on thresholds
            status = "healthy"
            issues = []

            if cpu_percent > 80:
                status = "degraded"
                issues.append(f"High CPU usage: {cpu_percent}%")

            if memory.percent > 85:
                status = "degraded"
                issues.append(f"High memory usage: {memory.percent}%")

            if disk.percent > 90:
                status = "degraded"
                issues.append(f"High disk usage: {disk.percent}%")

            return {
                "status": status,
                "message": "System resources checked",
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "process_memory_mb": round(process_memory.rss / (1024**2), 2),
                "issues": issues,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"System resource check failed: {str(e)}",
            }

    async def check_avantis_connectivity(self) -> dict[str, Any]:
        """Check Avantis protocol connectivity"""
        try:
            import aiohttp

            start_time = time.time()
            # FIX: Add timeout to prevent hanging connections
            # REASON: ClientSession without timeout can hang indefinitely
            # REVIEW: Line 190 from code review - aiohttp.ClientSession without timeout
            timeout = aiohttp.ClientTimeout(total=10, connect=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Test Base RPC connectivity
                payload = {
                    "jsonrpc": "2.0",
                    "method": "eth_blockNumber",
                    "params": [],
                    "id": 1,
                }

                async with session.post(
                    settings.BASE_RPC_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "result" in data:
                            block_number = int(data["result"], 16)
                            response_time = (time.time() - start_time) * 1000

                            return {
                                "status": "healthy",
                                "message": f"Base RPC is responding (block: {block_number})",
                                "response_time_ms": round(response_time, 2),
                                "latest_block": block_number,
                            }
                        else:
                            return {
                                "status": "unhealthy",
                                "message": "Base RPC returned invalid response",
                                "response_time_ms": round(
                                    (time.time() - start_time) * 1000, 2
                                ),
                            }
                    else:
                        return {
                            "status": "unhealthy",
                            "message": f"Base RPC returned status {response.status}",
                            "response_time_ms": round(
                                (time.time() - start_time) * 1000, 2
                            ),
                        }

        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Avantis connectivity check failed: {str(e)}",
            }

    async def run_all_checks(self) -> dict[str, Any]:
        """Run all health checks"""
        checks = {}

        # Run checks in parallel
        check_tasks = [
            ("redis", self.check_redis()),
            ("database", self.check_database()),
            ("system", self.check_system_resources()),
            ("avantis", self.check_avantis_connectivity()),
        ]

        for check_name, check_task in check_tasks:
            try:
                result = await check_task
                checks[check_name] = result
                log_system_health(check_name, result["status"], result)
            except Exception as e:
                checks[check_name] = {
                    "status": "unhealthy",
                    "message": f"Check failed with exception: {str(e)}",
                }
                log_system_health(check_name, "unhealthy", {"error": str(e)})

        # Determine overall health
        overall_status = "healthy"
        unhealthy_checks = [
            name for name, result in checks.items() if result["status"] == "unhealthy"
        ]
        degraded_checks = [
            name for name, result in checks.items() if result["status"] == "degraded"
        ]

        if unhealthy_checks:
            overall_status = "unhealthy"
        elif degraded_checks:
            overall_status = "degraded"

        return {
            "status": overall_status,
            "checks": checks,
            "unhealthy_checks": unhealthy_checks,
            "degraded_checks": degraded_checks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": time.time() - _health_state["startup_time"],
        }


# Global health checker instance
health_checker = HealthChecker()


def create_health_app() -> FastAPI:
    """Create FastAPI app for health check endpoints"""
    app = FastAPI(
        title="Vanta Bot Health Check",
        description="Health check endpoints for monitoring",
        version="2.0.0",
    )

    @app.get("/healthz")
    async def health_check():
        """Basic health check endpoint (liveness probe)"""
        try:
            # Quick check - just verify the service is running
            return JSONResponse(
                status_code=200,
                content={
                    "status": "healthy",
                    "message": "Service is running",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "uptime_seconds": time.time() - _health_state["startup_time"],
                },
            )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=503, detail="Service unhealthy")

    @app.get("/readyz")
    async def readiness_check():
        """Readiness check endpoint"""
        try:
            # Run basic checks to ensure service is ready
            checks = await health_checker.run_all_checks()

            if checks["status"] == "unhealthy":
                raise HTTPException(status_code=503, detail=checks)

            return JSONResponse(status_code=200, content=checks)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            raise HTTPException(status_code=503, detail="Service not ready")

    @app.get("/health")
    async def detailed_health_check():
        """Detailed health check endpoint"""
        try:
            checks = await health_checker.run_all_checks()

            # Include additional system information
            checks["system_info"] = {
                "environment": settings.ENVIRONMENT,
                "debug_mode": settings.DEBUG,
                "log_level": settings.LOG_LEVEL,
                "copy_execution_mode": settings.COPY_EXECUTION_MODE,
                "emergency_stop": settings.EMERGENCY_STOP,
            }

            # Include oracle status for operational visibility
            checks["oracle_status"] = await _get_oracle_status()

            # Update global state
            _health_state["last_check"] = time.time()
            _health_state["checks"] = checks

            return JSONResponse(
                status_code=200 if checks["status"] != "unhealthy" else 503,
                content=checks,
            )
        except Exception as e:
            logger.error(f"Detailed health check failed: {e}")
            raise HTTPException(status_code=503, detail="Health check failed")

    @app.get("/metrics")
    async def metrics():
        """Basic metrics endpoint"""
        try:
            # System metrics
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Process metrics
            process = psutil.Process()
            process_memory = process.memory_info()

            metrics_data = {
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_bytes": memory.available,
                    "disk_percent": disk.percent,
                    "disk_free_bytes": disk.free,
                },
                "process": {
                    "memory_rss_bytes": process_memory.rss,
                    "memory_vms_bytes": process_memory.vms,
                    "cpu_percent": process.cpu_percent(),
                    "num_threads": process.num_threads(),
                },
                "application": {
                    "uptime_seconds": time.time() - _health_state["startup_time"],
                    "environment": settings.ENVIRONMENT,
                    "copy_execution_mode": settings.COPY_EXECUTION_MODE,
                },
            }

            return JSONResponse(content=metrics_data)

        except Exception as e:
            logger.error(f"Metrics collection failed: {e}")
            raise HTTPException(status_code=500, detail="Metrics collection failed")

    return app


# Background task for periodic health checks
async def start_health_monitoring():
    """Start background health monitoring task"""

    async def health_monitor():
        while True:
            try:
                checks = await health_checker.run_all_checks()
                _health_state["last_check"] = time.time()
                _health_state["checks"] = checks

                # Log any unhealthy checks
                for check_name, result in checks["checks"].items():
                    if result["status"] == "unhealthy":
                        logger.warning(
                            f"Health check failed: {check_name} - {result['message']}"
                        )

                # Wait 60 seconds before next check
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(60)

    @app.get("/oracle/status")
    async def oracle_status():
        """Lightweight oracle status endpoint for dashboards."""
        try:
            oracle_status = await _get_oracle_status()
            return JSONResponse(content=oracle_status)
        except Exception as e:
            logger.error(f"Oracle status endpoint failed: {e}")
            raise HTTPException(status_code=500, detail="Oracle status failed")

    # Start the monitoring task
    asyncio.create_task(health_monitor())
    logger.info("Health monitoring started")


def get_health_state() -> dict[str, Any]:
    """Get current health state for external access"""
    return _health_state.copy()
