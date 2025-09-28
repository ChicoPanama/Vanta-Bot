"""
Structured Logging Configuration
Centralized logging setup for the Vanta Bot with trace ID support
"""

import logging
import sys
import json
import uuid
import contextvars
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from loguru import logger

from src.config.settings import settings

# Context variable for trace ID
trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('trace_id', default='')


class StructuredFormatter:
    """Custom formatter for structured JSON logging"""
    
    def __init__(self, service_name: str = "vanta-bot"):
        self.service_name = service_name
    
    def format(self, record: Dict[str, Any]) -> str:
        """Format log record as structured JSON"""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record["level"].name,
            "service": self.service_name,
            "env": settings.ENVIRONMENT,
            "version": "2.0.0",
            "message": record["message"],
            "module": record["name"],
            "function": record["function"],
            "line": record["line"],
            "trace_id": trace_id_var.get(''),
        }
        
        # Add extra fields if present
        if record.get("extra"):
            log_entry.update(record["extra"])
        
        # Add exception info if present
        if record.get("exception"):
            log_entry["exception"] = {
                "type": record["exception"].type.__name__,
                "value": str(record["exception"].value),
                "traceback": record["exception"].traceback
            }
        
        return json.dumps(log_entry, default=str)


def setup_logging() -> None:
    """Setup structured logging configuration"""
    # Remove default loguru handler
    logger.remove()
    
    # Determine log level
    log_level = settings.LOG_LEVEL.upper()
    
    if settings.LOG_JSON:
        # JSON structured logging for production
        formatter = StructuredFormatter()
        logger.add(
            sys.stdout,
            format=formatter.format,
            level=log_level,
            serialize=False,  # We handle serialization in formatter
            backtrace=True,
            diagnose=settings.DEBUG,
        )
        
        # Also log to file in production
        if settings.is_production():
            logger.add(
                "logs/app.log",
                format=formatter.format,
                level=log_level,
                rotation="100 MB",
                retention="30 days",
                compression="zip",
                backtrace=True,
                diagnose=settings.DEBUG,
            )
    else:
        # Human-readable logging for development
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<yellow>[{extra[trace_id]}]</yellow> | "
            "<level>{message}</level>"
        )
        
        logger.add(
            sys.stdout,
            format=format_string,
            level=log_level,
            colorize=True,
            backtrace=True,
            diagnose=settings.DEBUG,
        )
        
        # Also log to file in development
        logger.add(
            "logs/app.log",
            format=format_string,
            level=log_level,
            rotation="10 MB",
            retention="7 days",
            backtrace=True,
            diagnose=settings.DEBUG,
        )
    
    # Configure standard library logging to use loguru
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            # Get corresponding Loguru level if it exists
            try:
                lvl = logger.level(record.levelname)
                level = lvl.name if lvl is not None else record.levelno
            except Exception:
                level = record.levelno
            
            # Find caller from where the logged message originated
            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1
            
            try:
                if hasattr(logger, "log"):
                    logger.log(level, record.getMessage())
            except Exception:
                # No-op fallback when loguru is stubbed in tests
                pass
    
    # Intercept standard library logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Set specific loggers to appropriate levels
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Log startup information
    logger.info("Logging system initialized", extra={
        "log_level": log_level,
        "json_format": settings.LOG_JSON,
        "environment": settings.ENVIRONMENT,
        "debug_mode": settings.DEBUG
    })


def get_logger(name: str) -> Any:
    """Get a logger instance with the given name"""
    return logger.bind(module=name, trace_id="")


def log_function_call(func_name: str, **kwargs) -> None:
    """Log function call with parameters (excluding sensitive data)"""
    # Filter out sensitive parameters
    safe_kwargs = {k: v for k, v in kwargs.items() 
                   if k.lower() not in ['password', 'token', 'key', 'secret', 'private_key']}
    
    logger.debug(f"Function call: {func_name}", extra={
        "function": func_name,
        "parameters": safe_kwargs
    })


def log_telegram_command(user_id: int, command: str, success: bool, duration_ms: float) -> None:
    """Log Telegram command execution"""
    logger.info("Telegram command executed", extra={
        "user_id_hash": hash(str(user_id)),  # Hash for privacy
        "command": command,
        "success": success,
        "duration_ms": duration_ms
    })


def log_trade_execution(
    user_id: int, 
    pair: str, 
    side: str, 
    amount: float, 
    mode: str,
    success: bool,
    tx_hash: Optional[str] = None
) -> None:
    """Log trade execution attempt"""
    logger.info("Trade execution", extra={
        "user_id_hash": hash(str(user_id)),
        "pair": pair,
        "side": side,
        "amount": amount,
        "mode": mode,
        "success": success,
        "tx_hash": tx_hash
    })


def log_copy_trade(
    follower_id: int,
    leader_address: str,
    pair: str,
    amount: float,
    success: bool,
    reason: Optional[str] = None
) -> None:
    """Log copy trade execution"""
    logger.info("Copy trade executed", extra={
        "follower_id_hash": hash(str(follower_id)),
        "leader_address": leader_address,
        "pair": pair,
        "amount": amount,
        "success": success,
        "reason": reason
    })


def log_system_health(
    component: str,
    status: str,
    metrics: Optional[Dict[str, Any]] = None
) -> None:
    """Log system health status"""
    extra = {
        "component": component,
        "status": status
    }
    if metrics:
        extra["metrics"] = metrics
    
    if status == "healthy":
        logger.info("System health check", extra=extra)
    else:
        logger.warning("System health issue", extra=extra)


def log_performance(
    operation: str,
    duration_ms: float,
    success: bool,
    **kwargs
) -> None:
    """Log performance metrics"""
    logger.info("Performance metric", extra={
        "operation": operation,
        "duration_ms": duration_ms,
        "success": success,
        **kwargs
    })


def set_trace_id(trace_id: str = None) -> str:
    """Set trace ID for current context. Returns the trace ID."""
    if trace_id is None:
        trace_id = str(uuid.uuid4())[:8]
    trace_id_var.set(trace_id)
    return trace_id


def get_trace_id() -> str:
    """Get current trace ID."""
    return trace_id_var.get('')


def log_with_context(logger_instance, level: str, message: str, **kwargs):
    """Log with additional context fields."""
    log_func = getattr(logger_instance, level.lower())
    extra = {k: v for k, v in kwargs.items() if k not in ['message', 'level']}
    extra['trace_id'] = get_trace_id()
    log_func(message, extra=extra)


# Initialize logging when module is imported
setup_logging()
