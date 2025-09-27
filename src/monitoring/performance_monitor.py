"""
Performance Monitoring for Vanta Bot
Handles metrics collection, health checks, and alerting
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

import asyncpg
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class Metric:
    name: str
    value: float
    metric_type: str  # 'counter', 'gauge', 'histogram'
    labels: Dict[str, str]
    timestamp: datetime

@dataclass
class HealthCheck:
    service_name: str
    status: HealthStatus
    details: Dict[str, Any]
    checked_at: datetime

class PerformanceMonitor:
    """Performance monitoring and health check system"""
    
    def __init__(self, db_pool: asyncpg.Pool, redis_client: redis.Redis, config):
        self.db_pool = db_pool
        self.redis = redis_client
        self.config = config
        
        # Metrics storage
        self.metrics_buffer = []
        self.health_checks = {}
        
        # Monitoring state
        self.is_running = False
        
        # Service dependencies
        self.services = {}
        
    async def start_monitoring(self):
        """Start performance monitoring"""
        if self.is_running:
            logger.warning("Performance monitor is already running")
            return
            
        self.is_running = True
        logger.info("Starting performance monitoring...")
        
        try:
            # Start metrics collection
            metrics_task = asyncio.create_task(self._collect_metrics())
            
            # Start health checks
            health_task = asyncio.create_task(self._run_health_checks())
            
            # Start metrics persistence
            persistence_task = asyncio.create_task(self._persist_metrics())
            
            # Wait for all tasks
            await asyncio.gather(metrics_task, health_task, persistence_task)
            
        except Exception as e:
            logger.error(f"Error in performance monitoring: {e}")
            self.is_running = False
            raise
    
    async def stop_monitoring(self):
        """Stop performance monitoring"""
        self.is_running = False
        logger.info("Stopped performance monitoring")
    
    async def _collect_metrics(self):
        """Collect system and application metrics"""
        logger.info("Starting metrics collection...")
        
        while self.is_running:
            try:
                # Collect copy trading metrics
                await self._collect_copy_trading_metrics()
                
                # Collect system metrics
                await self._collect_system_metrics()
                
                # Collect AI service metrics
                await self._collect_ai_metrics()
                
                # Wait before next collection
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(10)
    
    async def _collect_copy_trading_metrics(self):
        """Collect copy trading specific metrics"""
        try:
            # Get copy trading statistics
            async with self.db_pool.acquire() as conn:
                # Active copytraders
                active_copytraders = await conn.fetchval("""
                    SELECT COUNT(*) FROM copytrader_profiles WHERE is_enabled = true
                """)
                
                # Active follows
                active_follows = await conn.fetchval("""
                    SELECT COUNT(*) FROM leader_follows WHERE is_active = true
                """)
                
                # Copy positions in last hour
                recent_positions = await conn.fetchval("""
                    SELECT COUNT(*) FROM copy_positions 
                    WHERE created_at > NOW() - INTERVAL '1 hour'
                """)
                
                # Failed copy trades in last hour
                failed_trades = await conn.fetchval("""
                    SELECT COUNT(*) FROM copy_positions 
                    WHERE status = 'FAILED' AND created_at > NOW() - INTERVAL '1 hour'
                """)
            
            # Store metrics
            await self._store_metric('copy_trades_active_copytraders', active_copytraders, 'gauge', {'service': 'copy_executor'})
            await self._store_metric('copy_trades_active_follows', active_follows, 'gauge', {'service': 'copy_executor'})
            await self._store_metric('copy_trades_recent_positions', recent_positions, 'counter', {'service': 'copy_executor'})
            await self._store_metric('copy_trades_failed_trades', failed_trades, 'counter', {'service': 'copy_executor'})
            
        except Exception as e:
            logger.error(f"Error collecting copy trading metrics: {e}")
    
    async def _collect_system_metrics(self):
        """Collect system metrics"""
        try:
            # Database connection metrics
            db_connections = await self._check_database_health()
            await self._store_metric('database_connections', db_connections, 'gauge', {'service': 'database'})
            
            # Redis connection metrics
            redis_connections = await self._check_redis_health()
            await self._store_metric('redis_connections', redis_connections, 'gauge', {'service': 'redis'})
            
            # Event monitoring metrics
            await self._collect_event_monitoring_metrics()
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    async def _collect_ai_metrics(self):
        """Collect AI service metrics"""
        try:
            async with self.db_pool.acquire() as conn:
                # AI analyses performed in last hour
                ai_analyses = await conn.fetchval("""
                    SELECT COUNT(*) FROM trader_analytics 
                    WHERE updated_at > NOW() - INTERVAL '1 hour'
                """)
                
                # Market regime changes in last hour
                regime_changes = await conn.fetchval("""
                    SELECT COUNT(*) FROM performance_metrics 
                    WHERE metric_name = 'market_regime_changes' 
                    AND timestamp > NOW() - INTERVAL '1 hour'
                """)
            
            await self._store_metric('ai_analyses_performed', ai_analyses, 'counter', {'service': 'trader_analyzer'})
            await self._store_metric('market_regime_changes', regime_changes, 'counter', {'service': 'market_intelligence'})
            
        except Exception as e:
            logger.error(f"Error collecting AI metrics: {e}")
    
    async def _collect_event_monitoring_metrics(self):
        """Collect event monitoring metrics"""
        try:
            async with self.db_pool.acquire() as conn:
                # Events indexed in last hour
                events_indexed = await conn.fetchval("""
                    SELECT COUNT(*) FROM trade_events 
                    WHERE created_at > NOW() - INTERVAL '1 hour'
                """)
                
                # Unique traders with activity in last hour
                active_traders = await conn.fetchval("""
                    SELECT COUNT(DISTINCT address) FROM trade_events 
                    WHERE created_at > NOW() - INTERVAL '1 hour'
                """)
            
            await self._store_metric('events_indexed', events_indexed, 'counter', {'service': 'event_indexer'})
            await self._store_metric('active_traders', active_traders, 'gauge', {'service': 'event_indexer'})
            
        except Exception as e:
            logger.error(f"Error collecting event monitoring metrics: {e}")
    
    async def _store_metric(self, name: str, value: float, metric_type: str, labels: Dict[str, str]):
        """Store metric in buffer"""
        metric = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            labels=labels,
            timestamp=datetime.utcnow()
        )
        
        self.metrics_buffer.append(metric)
    
    async def _persist_metrics(self):
        """Persist metrics to database"""
        logger.info("Starting metrics persistence...")
        
        while self.is_running:
            try:
                if self.metrics_buffer:
                    # Persist metrics to database
                    await self._write_metrics_to_db()
                    
                    # Clear buffer
                    self.metrics_buffer.clear()
                
                # Wait before next persistence
                await asyncio.sleep(60)  # Persist every minute
                
            except Exception as e:
                logger.error(f"Error persisting metrics: {e}")
                await asyncio.sleep(30)
    
    async def _write_metrics_to_db(self):
        """Write metrics to database"""
        try:
            async with self.db_pool.acquire() as conn:
                # Batch insert metrics
                await conn.executemany("""
                    INSERT INTO performance_metrics (metric_name, metric_value, metric_type, labels, timestamp)
                    VALUES ($1, $2, $3, $4, $5)
                """, [
                    (
                        metric.name,
                        metric.value,
                        metric.metric_type,
                        metric.labels,
                        metric.timestamp
                    ) for metric in self.metrics_buffer
                ])
                
                logger.debug(f"Persisted {len(self.metrics_buffer)} metrics to database")
                
        except Exception as e:
            logger.error(f"Error writing metrics to database: {e}")
    
    async def _run_health_checks(self):
        """Run health checks on all services"""
        logger.info("Starting health checks...")
        
        while self.is_running:
            try:
                # Check database health
                db_health = await self._check_database_health_detailed()
                await self._update_health_check('database', db_health)
                
                # Check Redis health
                redis_health = await self._check_redis_health_detailed()
                await self._update_health_check('redis', redis_health)
                
                # Check blockchain connectivity
                blockchain_health = await self._check_blockchain_health()
                await self._update_health_check('blockchain', blockchain_health)
                
                # Check copy trading service
                copy_trading_health = await self._check_copy_trading_health()
                await self._update_health_check('copy_trading', copy_trading_health)
                
                # Check AI services
                ai_health = await self._check_ai_services_health()
                await self._update_health_check('ai_services', ai_health)
                
                # Wait before next health check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error running health checks: {e}")
                await asyncio.sleep(30)
    
    async def _check_database_health(self) -> int:
        """Check database connectivity"""
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return 1 if result == 1 else 0
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            return 0
    
    async def _check_database_health_detailed(self) -> HealthCheck:
        """Detailed database health check"""
        try:
            async with self.db_pool.acquire() as conn:
                # Test basic connectivity
                start_time = datetime.utcnow()
                result = await conn.fetchval("SELECT 1")
                response_time = (datetime.utcnow() - start_time).total_seconds()
                
                # Check database size
                db_size = await conn.fetchval("""
                    SELECT pg_size_pretty(pg_database_size(current_database()))
                """)
                
                # Check active connections
                active_connections = await conn.fetchval("""
                    SELECT count(*) FROM pg_stat_activity WHERE state = 'active'
                """)
                
                status = HealthStatus.HEALTHY
                if response_time > 1.0:
                    status = HealthStatus.DEGRADED
                if response_time > 5.0 or result != 1:
                    status = HealthStatus.UNHEALTHY
                
                return HealthCheck(
                    service_name='database',
                    status=status,
                    details={
                        'response_time_ms': response_time * 1000,
                        'database_size': db_size,
                        'active_connections': active_connections,
                        'connectivity': result == 1
                    },
                    checked_at=datetime.utcnow()
                )
                
        except Exception as e:
            return HealthCheck(
                service_name='database',
                status=HealthStatus.UNHEALTHY,
                details={'error': str(e)},
                checked_at=datetime.utcnow()
            )
    
    async def _check_redis_health(self) -> int:
        """Check Redis connectivity"""
        try:
            await self.redis.ping()
            return 1
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            return 0
    
    async def _check_redis_health_detailed(self) -> HealthCheck:
        """Detailed Redis health check"""
        try:
            # Test basic connectivity
            start_time = datetime.utcnow()
            await self.redis.ping()
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Get Redis info
            info = await self.redis.info()
            
            status = HealthStatus.HEALTHY
            if response_time > 0.1:
                status = HealthStatus.DEGRADED
            if response_time > 0.5:
                status = HealthStatus.UNHEALTHY
            
            return HealthCheck(
                service_name='redis',
                status=status,
                details={
                    'response_time_ms': response_time * 1000,
                    'used_memory': info.get('used_memory_human', 'unknown'),
                    'connected_clients': info.get('connected_clients', 0),
                    'uptime_seconds': info.get('uptime_in_seconds', 0)
                },
                checked_at=datetime.utcnow()
            )
            
        except Exception as e:
            return HealthCheck(
                service_name='redis',
                status=HealthStatus.UNHEALTHY,
                details={'error': str(e)},
                checked_at=datetime.utcnow()
            )
    
    async def _check_blockchain_health(self) -> HealthCheck:
        """Check blockchain connectivity"""
        try:
            # This would check Web3 connectivity to Base chain
            # For now, simulate the check
            
            status = HealthStatus.HEALTHY
            details = {
                'network': 'base',
                'latest_block': 12345678,
                'sync_status': 'synced'
            }
            
            return HealthCheck(
                service_name='blockchain',
                status=status,
                details=details,
                checked_at=datetime.utcnow()
            )
            
        except Exception as e:
            return HealthCheck(
                service_name='blockchain',
                status=HealthStatus.UNHEALTHY,
                details={'error': str(e)},
                checked_at=datetime.utcnow()
            )
    
    async def _check_copy_trading_health(self) -> HealthCheck:
        """Check copy trading service health"""
        try:
            async with self.db_pool.acquire() as conn:
                # Check recent copy trading activity
                recent_trades = await conn.fetchval("""
                    SELECT COUNT(*) FROM copy_positions 
                    WHERE created_at > NOW() - INTERVAL '1 hour'
                """)
                
                # Check failed trades ratio
                failed_trades = await conn.fetchval("""
                    SELECT COUNT(*) FROM copy_positions 
                    WHERE status = 'FAILED' AND created_at > NOW() - INTERVAL '1 hour'
                """)
                
                # Calculate failure rate
                failure_rate = (failed_trades / max(recent_trades, 1)) * 100
                
                status = HealthStatus.HEALTHY
                if failure_rate > 10:
                    status = HealthStatus.DEGRADED
                if failure_rate > 25:
                    status = HealthStatus.UNHEALTHY
                
                return HealthCheck(
                    service_name='copy_trading',
                    status=status,
                    details={
                        'recent_trades': recent_trades,
                        'failed_trades': failed_trades,
                        'failure_rate_percent': failure_rate,
                        'active_copytraders': await conn.fetchval("SELECT COUNT(*) FROM copytrader_profiles WHERE is_enabled = true")
                    },
                    checked_at=datetime.utcnow()
                )
                
        except Exception as e:
            return HealthCheck(
                service_name='copy_trading',
                status=HealthStatus.UNHEALTHY,
                details={'error': str(e)},
                checked_at=datetime.utcnow()
            )
    
    async def _check_ai_services_health(self) -> HealthCheck:
        """Check AI services health"""
        try:
            async with self.db_pool.acquire() as conn:
                # Check recent AI analyses
                recent_analyses = await conn.fetchval("""
                    SELECT COUNT(*) FROM trader_analytics 
                    WHERE updated_at > NOW() - INTERVAL '1 hour'
                """)
                
                # Check market intelligence activity
                market_updates = await conn.fetchval("""
                    SELECT COUNT(*) FROM performance_metrics 
                    WHERE metric_name = 'market_regime_changes' 
                    AND timestamp > NOW() - INTERVAL '1 hour'
                """)
                
                status = HealthStatus.HEALTHY
                if recent_analyses == 0 and market_updates == 0:
                    status = HealthStatus.DEGRADED  # No recent AI activity
                
                return HealthCheck(
                    service_name='ai_services',
                    status=status,
                    details={
                        'recent_analyses': recent_analyses,
                        'market_updates': market_updates,
                        'total_traders_analyzed': await conn.fetchval("SELECT COUNT(DISTINCT address) FROM trader_analytics")
                    },
                    checked_at=datetime.utcnow()
                )
                
        except Exception as e:
            return HealthCheck(
                service_name='ai_services',
                status=HealthStatus.UNHEALTHY,
                details={'error': str(e)},
                checked_at=datetime.utcnow()
            )
    
    async def _update_health_check(self, service_name: str, health_check: HealthCheck):
        """Update health check in memory and database"""
        try:
            # Store in memory
            self.health_checks[service_name] = health_check
            
            # Store in database
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO health_checks (service_name, status, details, checked_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (service_name) DO UPDATE SET
                        status = EXCLUDED.status,
                        details = EXCLUDED.details,
                        checked_at = EXCLUDED.checked_at
                """, 
                    health_check.service_name,
                    health_check.status.value,
                    health_check.details,
                    health_check.checked_at
                )
            
            # Alert if unhealthy
            if health_check.status == HealthStatus.UNHEALTHY:
                await self._send_health_alert(health_check)
                
        except Exception as e:
            logger.error(f"Error updating health check: {e}")
    
    async def _send_health_alert(self, health_check: HealthCheck):
        """Send health alert for unhealthy service"""
        try:
            # This would integrate with your alerting system (Slack, email, etc.)
            logger.error(f"HEALTH ALERT: {health_check.service_name} is {health_check.status.value}")
            logger.error(f"Details: {health_check.details}")
            
            # Store alert in database for tracking
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO performance_metrics (metric_name, metric_value, metric_type, labels, timestamp)
                    VALUES ($1, $2, $3, $4, $5)
                """, 
                    'health_alert',
                    1,
                    'counter',
                    {'service': health_check.service_name, 'status': health_check.status.value},
                    datetime.utcnow()
                )
                
        except Exception as e:
            logger.error(f"Error sending health alert: {e}")
    
    # Public API methods
    async def get_health_status(self) -> Dict[str, HealthCheck]:
        """Get current health status of all services"""
        return self.health_checks.copy()
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        try:
            async with self.db_pool.acquire() as conn:
                # Get recent metrics
                recent_metrics = await conn.fetch("""
                    SELECT metric_name, AVG(metric_value) as avg_value, MAX(metric_value) as max_value
                    FROM performance_metrics
                    WHERE timestamp > NOW() - INTERVAL '1 hour'
                    GROUP BY metric_name
                    ORDER BY metric_name
                """)
                
                return {
                    'metrics': [dict(row) for row in recent_metrics],
                    'last_updated': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting metrics summary: {e}")
            return {'metrics': [], 'last_updated': datetime.utcnow().isoformat()}
    
    async def get_service_status(self, service_name: str) -> Optional[HealthCheck]:
        """Get status of a specific service"""
        return self.health_checks.get(service_name)
    
    def register_service(self, name: str, service):
        """Register a service for monitoring"""
        self.services[name] = service
    
    async def trigger_health_check(self, service_name: str) -> Optional[HealthCheck]:
        """Manually trigger health check for a service"""
        if service_name == 'database':
            return await self._check_database_health_detailed()
        elif service_name == 'redis':
            return await self._check_redis_health_detailed()
        elif service_name == 'blockchain':
            return await self._check_blockchain_health()
        elif service_name == 'copy_trading':
            return await self._check_copy_trading_health()
        elif service_name == 'ai_services':
            return await self._check_ai_services_health()
        else:
            return None
