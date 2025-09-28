"""
Clean Logging Configuration for Testing
Simplified logging setup for CI/CD and testing environments
"""

import logging
import sys
import os
from typing import Any, Dict, Optional
from loguru import logger


class CleanFormatter:
    """Clean formatter for testing environments"""
    
    def __init__(self, service_name: str = "vanta-bot"):
        self.service_name = service_name
    
    def format(self, record: Dict[str, Any]) -> str:
        """Format log record for clean output"""
        # Simple format for testing
        if os.getenv("LOG_JSON", "false").lower() == "true":
            import json
            log_entry = {
                "timestamp": record["time"].isoformat(),
                "level": record["level"].name,
                "service": self.service_name,
                "message": record["message"],
                "module": record["name"],
                "function": record["function"],
                "line": record["line"],
            }
            return json.dumps(log_entry)
        else:
            # Simple text format for testing
            return f"{record['time']} | {record['level'].name} | {record['name']} | {record['message']}"


def setup_clean_logging(service_name: str = "vanta-bot", level: str = "INFO"):
    """Set up clean logging for testing"""
    
    # Remove default handler
    logger.remove()
    
    # Add console handler with clean formatter
    formatter = CleanFormatter(service_name)
    
    logger.add(
        sys.stdout,
        format=formatter.format,
        level=level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # Add file handler for test logs
    if os.getenv("ENVIRONMENT") == "test":
        logger.add(
            "logs/test.log",
            format=formatter.format,
            level=level,
            rotation="10 MB",
            retention="7 days"
        )
    
    return logger


def get_logger(name: str) -> Any:
    """Get logger instance with clean configuration"""
    return logger.bind(name=name)


# Set up clean logging by default
if os.getenv("ENVIRONMENT") == "test":
    setup_clean_logging(level="DEBUG")
else:
    setup_clean_logging(level="INFO")
