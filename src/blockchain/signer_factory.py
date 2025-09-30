"""DEPRECATED: Legacy signer factory.

⚠️  DEPRECATION WARNING: This module is deprecated and should not be used.
Use src.blockchain.signers.factory.get_signer() instead.

This file is kept temporarily for backwards compatibility but will be removed
in a future version. All imports should use:

    from src.blockchain.signers.factory import get_signer

Reason for deprecation:
- Duplicate factory causes confusion
- Settings-based factory in signers.factory is the canonical implementation
- This legacy version uses direct env vars instead of settings

Migration:
1. Replace: from src.blockchain.signer_factory import create_signer
   With:    from src.blockchain.signers.factory import get_signer
2. Update calls from create_signer(w3) to get_signer(w3)
3. Remove any remaining references to this module
"""

import logging
import warnings
from typing import Optional

from web3 import Web3

logger = logging.getLogger(__name__)

# Issue deprecation warning at module import time
warnings.warn(
    "signer_factory is deprecated. Use src.blockchain.signers.factory.get_signer() instead.",
    DeprecationWarning,
    stacklevel=2,
)


def create_signer(web3: Web3) -> Optional["Signer"]:  # type: ignore
    """DEPRECATED: Create signer based on environment configuration.

    ⚠️  This function is deprecated. Use get_signer() from signers.factory instead.

    Args:
        web3: Web3 instance

    Returns:
        Configured signer

    Raises:
        DeprecationWarning: Always warns about deprecation
        ImportError: To force migration to new factory
    """
    logger.error(
        "create_signer() from signer_factory.py is deprecated. "
        "Use get_signer() from src.blockchain.signers.factory instead."
    )
    raise ImportError(
        "Legacy signer_factory is deprecated. "
        "Import from src.blockchain.signers.factory instead:\n"
        "  from src.blockchain.signers.factory import get_signer"
    )
