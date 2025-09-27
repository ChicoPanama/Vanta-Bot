"""
Health & Readiness Endpoints
Production-ready health monitoring for Vanta Bot
"""

import asyncio
import time
from aiohttp import web, ClientSession
from typing import Dict, Any, Optional
import logging
import os
import json

from src.config.settings import settings
from src.utils.logging import get_logger, set_trace_id

log = get_logger(__name__)


class HealthChecker:
    def __init__(self, db_connection=None, redis_connection=None, price_feed_manager=None):
        self.db = db_connection
        self.redis = redis_connection
        self.price_feed_manager = price_feed_manager
        self.start_time = time.time()
        
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        try:
            if not self.db:
                return {
                    'status': 'not_configured',
                    'message': 'Database connection not configured',
                    'timestamp': time.time()
                }
            
            start = time.time()
            # Simple query to test DB
            await self.db.execute("SELECT 1")
            duration = time.time() - start
            
            return {
                'status': 'healthy',
                'response_time_ms': round(duration * 1000, 2),
                'timestamp': time.time()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': time.time()
            }
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity."""
        try:
            if not self.redis:
                return {
                    'status': 'not_configured',
                    'message': 'Redis connection not configured',
                    'timestamp': time.time()
                }
            
            start = time.time()
            await self.redis.ping()
            duration = time.time() - start
            
            return {
                'status': 'healthy',
                'response_time_ms': round(duration * 1000, 2),
                'timestamp': time.time()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': time.time()
            }
    
    async def check_price_feeds(self) -> Dict[str, Any]:
        """Check price feed health and freshness."""
        try:
            if not self.price_feed_manager:
                return {
                    'status': 'not_configured',
                    'message': 'Price feed manager not configured',
                    'timestamp': time.time()
                }
            
            feed_health = self.price_feed_manager.get_feed_health()
            
            # Check if any feeds are stale
            stale_feeds = [
                asset for asset, health in feed_health.items() 
                if health['is_stale']
            ]
            
            status = 'healthy' if not stale_feeds else 'degraded'
            
            return {
                'status': status,
                'feeds': feed_health,
                'stale_feeds': stale_feeds,
                'timestamp': time.time()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': time.time()
            }
    
    async def check_blockchain_connection(self) -> Dict[str, Any]:
        """Check Base network connectivity."""
        try:
            from src.blockchain.avantis_client import AvantisClient
            
            start = time.time()
            client = AvantisClient()
            current_block = await client.get_latest_block_number()
            duration = time.time() - start
            
            return {
                'status': 'healthy',
                'current_block': current_block,
                'response_time_ms': round(duration * 1000, 2),
                'timestamp': time.time()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': time.time()
            }
    
    async def check_telegram_bot(self) -> Dict[str, Any]:
        """Check Telegram bot connectivity."""
        try:
            import aiohttp
            
            # Test Telegram API connectivity
            start = time.time()
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getMe"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    duration = time.time() - start
                    
                    if response.status == 200:
                        data = await response.json()
                        bot_info = data.get('result', {})
                        
                        return {
                            'status': 'healthy',
                            'bot_username': bot_info.get('username'),
                            'bot_id': bot_info.get('id'),
                            'response_time_ms': round(duration * 1000, 2),
                            'timestamp': time.time()
                        }
                    else:
                        return {
                            'status': 'unhealthy',
                            'error': f'HTTP {response.status}',
                            'response_time_ms': round(duration * 1000, 2),
                            'timestamp': time.time()
                        }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': time.time()
            }


async def health_handler(request) -> web.Response:
    """Basic health check - always returns OK if service is running."""
    trace_id = set_trace_id()
    
    return web.json_response({
        'status': 'healthy',
        'service': 'vanta-bot',
        'version': '2.0.0',
        'environment': settings.ENVIRONMENT,
        'uptime_seconds': time.time() - request.app['health_checker'].start_time,
        'timestamp': time.time(),
        'trace_id': trace_id
    })


async def readiness_handler(request) -> web.Response:
    """Detailed readiness check - validates all dependencies."""
    trace_id = set_trace_id()
    health_checker = request.app['health_checker']
    
    # Run all health checks concurrently
    checks = await asyncio.gather(
        health_checker.check_database(),
        health_checker.check_redis(),
        health_checker.check_price_feeds(),
        health_checker.check_blockchain_connection(),
        health_checker.check_telegram_bot(),
        return_exceptions=True
    )
    
    db_health, redis_health, feeds_health, blockchain_health, telegram_health = checks
    
    # Determine overall status
    statuses = [
        db_health.get('status', 'unhealthy'),
        redis_health.get('status', 'unhealthy'),
        feeds_health.get('status', 'unhealthy'),
        blockchain_health.get('status', 'unhealthy'),
        telegram_health.get('status', 'unhealthy')
    ]
    
    overall_status = 'healthy'
    if 'unhealthy' in statuses:
        overall_status = 'unhealthy'
    elif 'degraded' in statuses:
        overall_status = 'degraded'
    
    response_data = {
        'status': overall_status,
        'service': 'vanta-bot',
        'version': '2.0.0',
        'environment': settings.ENVIRONMENT,
        'timestamp': time.time(),
        'trace_id': trace_id,
        'checks': {
            'database': db_health,
            'redis': redis_health,
            'price_feeds': feeds_health,
            'blockchain': blockchain_health,
            'telegram': telegram_health
        }
    }
    
    # Return appropriate HTTP status code
    status_code = 200 if overall_status == 'healthy' else 503
    
    return web.json_response(response_data, status=status_code)


async def metrics_handler(request) -> web.Response:
    """Basic metrics endpoint for monitoring."""
    trace_id = set_trace_id()
    
    # Basic system metrics
    import psutil
    
    metrics = {
        'timestamp': time.time(),
        'trace_id': trace_id,
        'system': {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'uptime_seconds': time.time() - request.app['health_checker'].start_time
        },
        'service': {
            'name': 'vanta-bot',
            'version': '2.0.0',
            'environment': settings.ENVIRONMENT,
            'execution_mode': settings.COPY_EXECUTION_MODE
        }
    }
    
    return web.json_response(metrics)


def create_health_app(health_checker: HealthChecker) -> web.Application:
    """Create health check application."""
    app = web.Application()
    app['health_checker'] = health_checker
    
    # Add CORS headers for all responses
    async def add_cors_headers(request, handler):
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    app.middlewares.append(add_cors_headers)
    
    # Routes
    app.router.add_get('/healthz', health_handler)
    app.router.add_get('/readyz', readiness_handler)
    app.router.add_get('/health', health_handler)  # Alternative endpoint
    app.router.add_get('/metrics', metrics_handler)
    
    return app


async def start_health_server(health_checker: HealthChecker, port: int = None):
    """Start health check server."""
    port = port or int(os.getenv('HEALTH_PORT', '8080'))
    app = create_health_app(health_checker)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    log.info("Health server started on port %d", port)
    return runner
