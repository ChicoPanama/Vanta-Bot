"""Signer factory for creating appropriate signer based on configuration."""

import logging
import os
from typing import Optional
from web3 import Web3

from .signers import LocalPrivateKeySigner, KmsSigner
from .signers.base import Signer

logger = logging.getLogger(__name__)


def create_signer(web3: Web3) -> Optional[Signer]:
    """Create signer based on environment configuration.
    
    Args:
        web3: Web3 instance
        
    Returns:
        Configured signer or None if no signer should be used
    """
    signer_backend = os.getenv("SIGNER_BACKEND", "local").lower()
    
    if signer_backend == "local":
        private_key = os.getenv("TRADER_PRIVATE_KEY")
        if not private_key:
            logger.warning("TRADER_PRIVATE_KEY not set - transactions will fail")
            return None
        
        try:
            return LocalPrivateKeySigner(private_key, web3)
        except Exception as e:
            logger.error(f"Failed to create local signer: {e}")
            raise
    
    elif signer_backend == "kms":
        key_id = os.getenv("AWS_KMS_KEY_ID")
        region = os.getenv("AWS_REGION", "us-east-1")
        
        if not key_id:
            logger.warning("AWS_KMS_KEY_ID not set - transactions will fail")
            return None
        
        try:
            return KmsSigner(key_id, region, web3)
        except Exception as e:
            logger.error(f"Failed to create KMS signer: {e}")
            raise
    
    else:
        logger.warning(f"Unknown signer backend: {signer_backend}")
        return None
