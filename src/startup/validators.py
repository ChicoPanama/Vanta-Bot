"""Startup validators for fail-fast configuration checking (Phase 1)."""

import logging
import warnings

logger = logging.getLogger(__name__)


def validate_signer_config() -> None:
    """Validate signer configuration.

    Raises:
        RuntimeError: If KMS backend is missing required config
    """
    from src.config.settings import settings

    if settings.SIGNER_BACKEND == "kms":
        key_id = settings.KMS_KEY_ID or settings.AWS_KMS_KEY_ID
        if not key_id:
            raise RuntimeError(
                "KMS signer backend selected but KMS_KEY_ID (or AWS_KMS_KEY_ID) not set"
            )
        logger.info(f"✅ KMS signer configured with key: {key_id[:20]}...")

    elif settings.SIGNER_BACKEND == "local":
        warnings.warn(
            "⚠️  Using LOCAL private key signer — DO NOT USE IN PRODUCTION",
            stacklevel=2,
        )
        logger.warning("🔓 Local signer enabled (development mode)")

        private_key = settings.PRIVATE_KEY or settings.TRADER_PRIVATE_KEY
        if not private_key:
            raise RuntimeError(
                "Local signer backend selected but PRIVATE_KEY (or TRADER_PRIVATE_KEY) not set"
            )
    else:
        raise RuntimeError(
            f"Invalid SIGNER_BACKEND: {settings.SIGNER_BACKEND}. Must be 'kms' or 'local'"
        )


def validate_encryption_config() -> None:
    """Validate envelope encryption configuration.

    Raises:
        RuntimeError: If encryption config is invalid
    """
    from src.config.settings import settings

    if settings.ENCRYPTION_DEK_BYTES not in {16, 24, 32}:
        raise RuntimeError(
            f"Invalid ENCRYPTION_DEK_BYTES: {settings.ENCRYPTION_DEK_BYTES}. Must be 16, 24, or 32"
        )

    logger.info(
        f"✅ Envelope encryption configured: {settings.ENCRYPTION_DEK_BYTES * 8}-bit DEK"
    )


def run_all_validations() -> None:
    """Run all startup validations.

    Raises:
        RuntimeError: If any validation fails
    """
    logger.info("🔍 Running startup validations...")

    validate_signer_config()
    validate_encryption_config()

    logger.info("✅ All startup validations passed")
