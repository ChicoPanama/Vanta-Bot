"""Startup reconciliation utilities (Phase 4)."""

import logging

from web3 import Web3

logger = logging.getLogger(__name__)


def reconcile_nonces(w3: Web3) -> int:
    """Reconcile local nonce state with on-chain state.

    Args:
        w3: Web3 instance

    Returns:
        Reconciled nonce value
    """
    try:
        from src.blockchain.signers.factory import get_signer
        from src.blockchain.tx.nonce_manager import NonceManager

        signer = get_signer()
        address = signer.get_address()
        nm = NonceManager(w3, address)

        nonce = nm.reconcile()
        logger.info(f"Reconciled nonce for {address[:8]}...: {nonce}")
        return nonce
    except Exception as e:
        logger.warning(f"Nonce reconciliation failed: {e}")
        return 0
