"""Signer factory for unified KMS/local signing (Phase 1)."""

import logging
import warnings
from typing import Protocol

from web3 import Web3

logger = logging.getLogger(__name__)


class Signer(Protocol):
    """Protocol for transaction signers."""

    @property
    def address(self) -> str:
        """Get the signer's address."""
        ...

    def sign_tx(self, tx: dict) -> bytes:
        """Sign transaction and return raw bytes."""
        ...


def get_signer(web3: Web3) -> Signer:
    """Get signer based on configuration.

    Args:
        web3: Web3 instance for transaction operations

    Returns:
        Configured signer (KMS or Local)

    Raises:
        RuntimeError: If signer cannot be configured
    """
    from src.config.settings import settings

    from .kms import KmsSigner
    from .local import LocalPrivateKeySigner

    backend = settings.SIGNER_BACKEND.lower()

    if backend == "kms":
        # KMS signer for production
        key_id = settings.KMS_KEY_ID or settings.AWS_KMS_KEY_ID
        if not key_id:
            raise RuntimeError(
                "KMS signer selected but KMS_KEY_ID (or AWS_KMS_KEY_ID) not set"
            )
        logger.info(f"🔐 Initializing KMS signer with key: {key_id[:20]}...")
        return KmsSigner(
            key_id=key_id,
            region=settings.AWS_REGION,
            web3=web3,
        )

    elif backend == "local":
        # Local signer for development
        private_key = settings.PRIVATE_KEY or settings.TRADER_PRIVATE_KEY
        if not private_key:
            raise RuntimeError(
                "Local signer selected but PRIVATE_KEY (or TRADER_PRIVATE_KEY) not set"
            )

        # Warn if using local signer
        warnings.warn(
            "⚠️  Using LOCAL private key signer — DO NOT USE IN PRODUCTION",
            stacklevel=2,
        )
        logger.warning("🔓 Using local private key signer (development mode)")

        return LocalPrivateKeySigner(private_key=private_key, web3=web3)

    else:
        raise RuntimeError(
            f"Unsupported signer backend: {backend}. Must be 'kms' or 'local'"
        )
