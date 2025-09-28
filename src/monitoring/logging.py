"""Structured logging with redaction for security."""

import logging
import json
import re
from typing import Dict, Any, Optional
from datetime import datetime


class SecurityRedactor:
    """Redacts sensitive information from log records."""
    
    def __init__(self):
        # Patterns for sensitive data
        self.patterns = [
            r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
            r'(?i)(token|key|secret|privkey|private_key)\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
            r'(?i)(api_key|apikey)\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
            r'(?i)(secret|secret_key)\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
            r'(?i)(auth|authorization)\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
        ]
        
        # Compile patterns for efficiency
        self.compiled_patterns = [re.compile(pattern) for pattern in self.patterns]
    
    def redact_string(self, text: str) -> str:
        """Redact sensitive information from string.
        
        Args:
            text: Input text
            
        Returns:
            Redacted text
        """
        if not isinstance(text, str):
            return text
        
        redacted = text
        
        for pattern in self.compiled_patterns:
            redacted = pattern.sub(r'\1=[REDACTED]', redacted)
        
        return redacted
    
    def redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive information from dictionary.
        
        Args:
            data: Input dictionary
            
        Returns:
            Redacted dictionary
        """
        if not isinstance(data, dict):
            return data
        
        redacted = {}
        
        for key, value in data.items():
            # Check if key contains sensitive terms
            if any(term in key.lower() for term in ['key', 'secret', 'token', 'password', 'privkey']):
                redacted[key] = '[REDACTED]'
            elif isinstance(value, str):
                redacted[key] = self.redact_string(value)
            elif isinstance(value, dict):
                redacted[key] = self.redact_dict(value)
            elif isinstance(value, list):
                redacted[key] = [self.redact_dict(item) if isinstance(item, dict) else self.redact_string(item) if isinstance(item, str) else item for item in value]
            else:
                redacted[key] = value
        
        return redacted


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter with redaction."""
    
    def __init__(self, redactor: Optional[SecurityRedactor] = None):
        super().__init__()
        self.redactor = redactor or SecurityRedactor()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON.
        
        Args:
            record: Log record
            
        Returns:
            JSON formatted log string
        """
        # Create structured log entry
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename', 'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated', 'thread', 'threadName', 'processName', 'process', 'getMessage']:
                log_entry[key] = value
        
        # Redact sensitive information
        redacted_entry = self.redactor.redact_dict(log_entry)
        
        return json.dumps(redacted_entry, default=str)


def setup_logging(log_level: str = "INFO", log_json: bool = False):
    """Setup application logging.
    
    Args:
        log_level: Logging level
        log_json: Whether to use JSON formatting
    """
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Set formatter
    if log_json:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('web3').setLevel(logging.INFO)
    
    # Log configuration
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={log_level}, json={log_json}")


def get_logger(name: str) -> logging.Logger:
    """Get logger with security redaction.
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger
    """
    return logging.getLogger(name)


# Global redactor instance
security_redactor = SecurityRedactor()
