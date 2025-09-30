"""Prometheus metrics for monitoring."""

import logging

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

logger = logging.getLogger(__name__)

# Create custom registry
registry = CollectorRegistry()

# Transaction metrics
tx_send_total = Counter(
    "tx_send_total",
    "Total transactions sent",
    ["status", "wallet_id"],
    registry=registry,
)

tx_send_errors_total = Counter(
    "tx_send_errors_total",
    "Total transaction send errors",
    ["error_type", "wallet_id"],
    registry=registry,
)

tx_confirmation_seconds = Histogram(
    "tx_confirmation_seconds",
    "Transaction confirmation time",
    ["wallet_id"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
    registry=registry,
)

# Wallet metrics
wallet_decrypt_errors_total = Counter(
    "wallet_decrypt_errors_total",
    "Total wallet decryption errors",
    ["wallet_id", "encryption_version"],
    registry=registry,
)

wallet_encrypt_total = Counter(
    "wallet_encrypt_total",
    "Total wallet encryption operations",
    ["encryption_version"],
    registry=registry,
)

# Oracle metrics
oracle_price_requests_total = Counter(
    "oracle_price_requests_total",
    "Total oracle price requests",
    ["market", "source"],
    registry=registry,
)

oracle_price_errors_total = Counter(
    "oracle_price_errors_total",
    "Total oracle price errors",
    ["market", "error_type"],
    registry=registry,
)

oracle_deviation_bps = Gauge(
    "oracle_deviation_bps",
    "Price deviation in basis points",
    ["market"],
    registry=registry,
)

oracle_freshness_seconds = Gauge(
    "oracle_freshness_seconds",
    "Price freshness in seconds",
    ["market"],
    registry=registry,
)

# Bot metrics
bot_commands_total = Counter(
    "bot_commands_total",
    "Total bot commands processed",
    ["command", "user_id"],
    registry=registry,
)

bot_command_errors_total = Counter(
    "bot_command_errors_total",
    "Total bot command errors",
    ["command", "error_type"],
    registry=registry,
)

bot_rate_limit_drops_total = Counter(
    "bot_rate_limit_drops_total",
    "Total rate limit drops",
    ["user_id"],
    registry=registry,
)

# Health metrics
health_check_total = Counter(
    "health_check_total",
    "Total health checks",
    ["check_name", "status"],
    registry=registry,
)

circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open)",
    ["breaker_name"],
    registry=registry,
)

# Database metrics
db_operations_total = Counter(
    "db_operations_total",
    "Total database operations",
    ["operation", "table"],
    registry=registry,
)

db_operation_duration_seconds = Histogram(
    "db_operation_duration_seconds",
    "Database operation duration",
    ["operation", "table"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
    registry=registry,
)

# Redis metrics
redis_operations_total = Counter(
    "redis_operations_total",
    "Total Redis operations",
    ["operation", "status"],
    registry=registry,
)

redis_operation_duration_seconds = Histogram(
    "redis_operation_duration_seconds",
    "Redis operation duration",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
    registry=registry,
)

# Application info
app_info = Info("app_info", "Application information", registry=registry)

# Set application info
app_info.info({"version": "1.0.0", "name": "vanta-bot", "environment": "production"})


class MetricsCollector:
    """Collects and exposes application metrics."""

    def __init__(self):
        self.registry = registry

    def record_tx_send(self, status: str, wallet_id: str):
        """Record transaction send."""
        tx_send_total.labels(status=status, wallet_id=wallet_id).inc()

    def record_tx_error(self, error_type: str, wallet_id: str):
        """Record transaction error."""
        tx_send_errors_total.labels(error_type=error_type, wallet_id=wallet_id).inc()

    def record_tx_confirmation(self, wallet_id: str, duration: float):
        """Record transaction confirmation time."""
        tx_confirmation_seconds.labels(wallet_id=wallet_id).observe(duration)

    def record_wallet_decrypt_error(self, wallet_id: str, encryption_version: str):
        """Record wallet decryption error."""
        wallet_decrypt_errors_total.labels(
            wallet_id=wallet_id, encryption_version=encryption_version
        ).inc()

    def record_wallet_encrypt(self, encryption_version: str):
        """Record wallet encryption."""
        wallet_encrypt_total.labels(encryption_version=encryption_version).inc()

    def record_oracle_request(self, market: str, source: str):
        """Record oracle price request."""
        oracle_price_requests_total.labels(market=market, source=source).inc()

    def record_oracle_error(self, market: str, error_type: str):
        """Record oracle error."""
        oracle_price_errors_total.labels(market=market, error_type=error_type).inc()

    def record_oracle_deviation(self, market: str, deviation_bps: int):
        """Record oracle price deviation."""
        oracle_deviation_bps.labels(market=market).set(deviation_bps)

    def record_oracle_freshness(self, market: str, freshness_seconds: int):
        """Record oracle price freshness."""
        oracle_freshness_seconds.labels(market=market).set(freshness_seconds)

    def record_bot_command(self, command: str, user_id: str):
        """Record bot command."""
        bot_commands_total.labels(command=command, user_id=user_id).inc()

    def record_bot_error(self, command: str, error_type: str):
        """Record bot command error."""
        bot_command_errors_total.labels(command=command, error_type=error_type).inc()

    def record_rate_limit_drop(self, user_id: str):
        """Record rate limit drop."""
        bot_rate_limit_drops_total.labels(user_id=user_id).inc()

    def record_health_check(self, check_name: str, status: str):
        """Record health check."""
        health_check_total.labels(check_name=check_name, status=status).inc()

    def record_circuit_breaker_state(self, breaker_name: str, is_open: bool):
        """Record circuit breaker state."""
        circuit_breaker_state.labels(breaker_name=breaker_name).set(1 if is_open else 0)

    def record_db_operation(self, operation: str, table: str, duration: float = None):
        """Record database operation."""
        db_operations_total.labels(operation=operation, table=table).inc()
        if duration is not None:
            db_operation_duration_seconds.labels(
                operation=operation, table=table
            ).observe(duration)

    def record_redis_operation(
        self, operation: str, status: str, duration: float = None
    ):
        """Record Redis operation."""
        redis_operations_total.labels(operation=operation, status=status).inc()
        if duration is not None:
            redis_operation_duration_seconds.labels(operation=operation).observe(
                duration
            )

    def get_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        return generate_latest(registry)


# Global metrics collector
metrics_collector = MetricsCollector()
