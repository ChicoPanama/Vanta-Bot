"""
Metrics Service
Collects and manages application metrics
"""

import time
from typing import Dict, Any, Optional, List
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: datetime
    value: float
    labels: Dict[str, str]


class MetricsService:
    """Service for collecting and managing metrics"""
    
    def __init__(self):
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self.last_reset = datetime.utcnow()
    
    def increment_counter(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric"""
        key = self._build_key(name, labels)
        self.counters[key] += value
        logger.debug(f"Counter {key} incremented by {value}")
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric value"""
        key = self._build_key(name, labels)
        self.gauges[key] = value
        logger.debug(f"Gauge {key} set to {value}")
    
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Observe a histogram metric"""
        key = self._build_key(name, labels)
        self.histograms[key].append(value)
        logger.debug(f"Histogram {key} observed value {value}")
    
    def time_operation(self, name: str, labels: Optional[Dict[str, str]] = None):
        """Context manager for timing operations"""
        return Timer(self, name, labels)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all current metrics"""
        return {
            'counters': dict(self.counters),
            'gauges': dict(self.gauges),
            'histograms': {
                name: {
                    'count': len(values),
                    'sum': sum(values),
                    'min': min(values) if values else 0,
                    'max': max(values) if values else 0,
                    'avg': sum(values) / len(values) if values else 0
                }
                for name, values in self.histograms.items()
            },
            'uptime_seconds': (datetime.utcnow() - self.last_reset).total_seconds()
        }
    
    def reset_metrics(self) -> None:
        """Reset all metrics"""
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()
        self.timers.clear()
        self.last_reset = datetime.utcnow()
        logger.info("Metrics reset")
    
    def _build_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Build metric key with labels"""
        if not labels:
            return name
        
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


class Timer:
    """Context manager for timing operations"""
    
    def __init__(self, metrics_service: MetricsService, name: str, labels: Optional[Dict[str, str]] = None):
        self.metrics_service = metrics_service
        self.name = name
        self.labels = labels
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.metrics_service.observe_histogram(f"{self.name}_duration", duration, self.labels)


# Global metrics service instance
metrics_service = MetricsService()


def track_metric(name: str, metric_type: str = "counter", labels: Optional[Dict[str, str]] = None):
    """Decorator for tracking function metrics"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Increment call counter
            metrics_service.increment_counter(f"{name}_calls", labels=labels)
            
            # Track timing
            with metrics_service.time_operation(f"{name}_execution", labels=labels):
                try:
                    result = func(*args, **kwargs)
                    metrics_service.increment_counter(f"{name}_success", labels=labels)
                    return result
                except Exception as e:
                    metrics_service.increment_counter(f"{name}_errors", labels=labels)
                    raise
        
        return wrapper
    return decorator


# Common metric names
class MetricNames:
    """Common metric name constants"""
    
    # Trading metrics
    TRADES_EXECUTED = "trades_executed"
    TRADES_FAILED = "trades_failed"
    POSITIONS_OPENED = "positions_opened"
    POSITIONS_CLOSED = "positions_closed"
    
    # User metrics
    USERS_ACTIVE = "users_active"
    USERS_TOTAL = "users_total"
    COMMANDS_EXECUTED = "commands_executed"
    
    # Performance metrics
    RESPONSE_TIME = "response_time"
    DATABASE_QUERIES = "database_queries"
    CACHE_HITS = "cache_hits"
    CACHE_MISSES = "cache_misses"
    
    # Error metrics
    ERRORS_TOTAL = "errors_total"
    VALIDATION_ERRORS = "validation_errors"
    RATE_LIMIT_HITS = "rate_limit_hits"
