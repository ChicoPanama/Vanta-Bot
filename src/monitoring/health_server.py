"""Health and readiness server for monitoring."""

import logging
import time

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.config.settings import settings
from src.middleware.circuit_breakers import circuit_breaker_manager

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Vanta Bot Health", version="1.0.0")


@app.get("/live")
async def liveness():
    """Liveness probe - always returns OK if service is running."""
    return {"status": "ok", "timestamp": time.time()}


@app.get("/ready")
async def readiness():
    """Readiness probe - checks if service is ready to handle requests."""
    try:
        checks = await _perform_health_checks()

        # Check if all critical services are healthy
        all_healthy = all(checks.values())

        if all_healthy:
            return JSONResponse(
                content={"ready": True, "checks": checks, "timestamp": time.time()},
                status_code=200,
            )
        else:
            return JSONResponse(
                content={"ready": False, "checks": checks, "timestamp": time.time()},
                status_code=503,
            )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={"ready": False, "error": str(e), "timestamp": time.time()},
            status_code=503,
        )


@app.get("/health")
async def health():
    """Comprehensive health check with detailed status."""
    try:
        checks = await _perform_health_checks()
        circuit_status = circuit_breaker_manager.get_status()

        return {
            "status": "healthy" if all(checks.values()) else "unhealthy",
            "timestamp": time.time(),
            "checks": checks,
            "circuit_breakers": circuit_status,
            "version": "1.0.0",
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={"status": "unhealthy", "error": str(e), "timestamp": time.time()},
            status_code=503,
        )


async def _perform_health_checks() -> dict[str, bool]:
    """Perform all health checks.

    Returns:
        Dict mapping check name to result
    """
    checks = {}

    # Database check
    checks["database"] = await _check_database()

    # Redis check
    checks["redis"] = await _check_redis()

    # RPC check
    checks["rpc"] = await _check_rpc()

    # Circuit breakers check
    checks["circuit_breakers"] = await _check_circuit_breakers()

    return checks


async def _check_database() -> bool:
    """Check database connectivity."""
    try:
        # This would use the actual database connection
        # For now, return True as a placeholder
        return True
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        return False


async def _check_redis() -> bool:
    """Check Redis connectivity."""
    try:
        import redis

        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        return True
    except Exception as e:
        logger.error(f"Redis check failed: {e}")
        return False


async def _check_rpc() -> bool:
    """Check RPC connectivity."""
    try:
        from src.blockchain.base_client import base_client

        # Check if we can get the latest block
        base_client.w3.eth.get_block("latest")
        return True
    except Exception as e:
        logger.error(f"RPC check failed: {e}")
        return False


async def _check_circuit_breakers() -> bool:
    """Check circuit breaker status."""
    try:
        status = circuit_breaker_manager.get_status()
        # Check if any critical circuit breakers are open
        for name, breaker_status in status.items():
            if breaker_status["is_open"]:
                logger.warning(f"Circuit breaker {name} is open")
                return False
        return True
    except Exception as e:
        logger.error(f"Circuit breaker check failed: {e}")
        return False


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    try:
        from fastapi import Response
        from prometheus_client import CONTENT_TYPE_LATEST

        # This would expose actual Prometheus metrics
        # For now, return a simple response
        return Response(
            content="# Vanta Bot Metrics\n# This would contain actual metrics\n",
            media_type=CONTENT_TYPE_LATEST,
        )
    except Exception as e:
        logger.error(f"Metrics endpoint failed: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.HEALTH_PORT)
