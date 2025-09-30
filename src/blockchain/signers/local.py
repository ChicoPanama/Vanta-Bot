"""Local private key signer implementation."""

import logging
from typing import Any

from eth_account import Account
from web3 import Web3

logger = logging.getLogger(__name__)


class LocalPrivateKeySigner:
    """Local private key signer for development and testing."""

    def __init__(self, private_key: str, web3: Web3):
        """Initialize with private key.

        Args:
            private_key: Hex string private key (with or without 0x prefix)
            web3: Web3 instance for transaction sending
        """
        # Normalize private key
        if private_key.startswith("0x"):
            private_key = private_key[2:]
        private_key = private_key.lower()

        if len(private_key) != 64:
            raise ValueError("Private key must be 64 hex characters")

        self.private_key = private_key
        self.web3 = web3
        self.account = Account.from_key(private_key)
        self._address = self.account.address

    @property
    def address(self) -> str:
        """Get the signer's address."""
        return self._address

    async def sign_and_send(self, tx: dict[str, Any]) -> str:
        """Sign and send transaction."""
        try:
            # Ensure transaction has required fields
            if "from" not in tx:
                tx["from"] = self.address

            # Sign the transaction
            signed_tx = self.account.sign_transaction(tx)

            # Send the transaction
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)

            logger.info(f"Transaction sent: {tx_hash.hex()}")
            return tx_hash.hex()

        except Exception as e:
            logger.error(f"Failed to sign and send transaction: {e}")
            raise
