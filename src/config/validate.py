"""
Startup validation module for critical secrets and configuration.

This module provides validation functions to ensure that all critical
secrets and configuration are properly set before the application starts.
"""

import os
import re
from typing import List, Optional

from cryptography.fernet import Fernet


def validate_required_secrets() -> None:
    """
    Validate that all required secrets are present and properly formatted.
    
    Raises:
        RuntimeError: If any required secrets are missing or malformed.
    """
    if os.getenv("REQUIRE_CRITICAL_SECRETS", "true").lower() == "true":
        required_secrets = [
            "ENCRYPTION_KEY",
            "TRADER_PRIVATE_KEY", 
            "TELEGRAM_BOT_TOKEN",
            "DATABASE_URL"
        ]
        
        missing_secrets = []
        for secret_name in required_secrets:
            if not os.getenv(secret_name):
                missing_secrets.append(secret_name)
        
        if missing_secrets:
            raise RuntimeError(
                f"Missing required secrets: {', '.join(missing_secrets)}. "
                "Set REQUIRE_CRITICAL_SECRETS=false to disable this check."
            )


def validate_encryption_key() -> None:
    """
    Validate that the encryption key is properly formatted.
    
    Raises:
        RuntimeError: If the encryption key is malformed.
    """
    key = os.getenv("ENCRYPTION_KEY")
    if key:
        try:
            Fernet(key)
        except Exception as e:
            raise RuntimeError(
                "Invalid ENCRYPTION_KEY format (must be urlsafe base64 32-byte). "
                "Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            ) from e


def validate_database_url() -> None:
    """
    Validate that the database URL is properly formatted.
    
    Raises:
        RuntimeError: If the database URL is malformed.
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Basic validation for PostgreSQL URL format
        if not re.match(r'^postgresql://[^:]+:[^@]+@[^:]+:\d+/[^/]+$', database_url):
            raise RuntimeError(
                "Invalid DATABASE_URL format. Expected format: "
                "postgresql://user:password@host:port/database"
            )


def validate_telegram_token() -> None:
    """
    Validate that the Telegram bot token is properly formatted.
    
    Raises:
        RuntimeError: If the Telegram token is malformed.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if token:
        # Telegram bot tokens typically follow pattern: number:alphanumeric_string
        if not re.match(r'^\d+:[A-Za-z0-9_-]{35}$', token):
            raise RuntimeError(
                "Invalid TELEGRAM_BOT_TOKEN format. Expected format: "
                "number:alphanumeric_string (35 characters)"
            )


def validate_private_key() -> None:
    """
    Validate that the trader private key is properly formatted.
    
    Raises:
        RuntimeError: If the private key is malformed.
    """
    private_key = os.getenv("TRADER_PRIVATE_KEY")
    if private_key:
        # Remove 0x prefix if present
        if private_key.startswith('0x'):
            private_key = private_key[2:]
        
        # Ethereum private keys are 64 hex characters
        if not re.match(r'^[a-fA-F0-9]{64}$', private_key):
            raise RuntimeError(
                "Invalid TRADER_PRIVATE_KEY format. Expected 64-character hex string "
                "(optionally prefixed with '0x')"
            )


def validate_environment_config() -> None:
    """
    Validate environment-specific configuration.
    
    Raises:
        RuntimeError: If environment configuration is invalid.
    """
    environment = os.getenv("ENVIRONMENT", "production")
    
    if environment == "production":
        # In production, ensure JSON logging is enabled
        log_json = os.getenv("LOG_JSON", "true").lower()
        if log_json != "true":
            raise RuntimeError(
                "LOG_JSON must be 'true' in production environment for proper log aggregation"
            )
        
        # In production, ensure we're not in development mode
        log_level = os.getenv("LOG_LEVEL", "INFO")
        if log_level.upper() == "DEBUG":
            raise RuntimeError(
                "LOG_LEVEL should not be 'DEBUG' in production environment"
            )


def validate_all() -> None:
    """
    Run all validation checks.
    
    This function should be called once during application startup,
    before wiring any services.
    
    Raises:
        RuntimeError: If any validation check fails.
    """
    try:
        validate_required_secrets()
        validate_encryption_key()
        validate_database_url()
        validate_telegram_token()
        validate_private_key()
        validate_environment_config()
    except Exception as e:
        # Log the error (if logging is available)
        print(f"Startup validation failed: {e}", flush=True)
        raise


if __name__ == "__main__":
    # Allow running this module directly for testing
    validate_all()
    print("All validation checks passed!")
