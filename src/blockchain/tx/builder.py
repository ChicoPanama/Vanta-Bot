"""Transaction builder for EIP-1559 transactions."""

import logging
from typing import Any

from eth_account import Account
from eth_account.signers.local import LocalAccount

logger = logging.getLogger(__name__)


class TxBuilder:
    """Builds and signs EIP-1559 transactions."""

    def __init__(self, web3_client, chain_id: int):
        self.web3 = web3_client
        self.chain_id = chain_id

    def build(
        self,
        from_addr: str,
        to: str,
        data: bytes,
        value: int,
        gas: int,
        nonce: int,
        max_fee: int,
        max_priority: int,
    ) -> dict[str, Any]:
        """Build EIP-1559 transaction.

        Args:
            from_addr: Sender address
            to: Recipient address
            data: Transaction data
            value: ETH value in wei
            gas: Gas limit
            nonce: Transaction nonce
            max_fee: Maximum fee per gas in wei
            max_priority: Maximum priority fee per gas in wei

        Returns:
            Transaction dictionary
        """
        try:
            tx = {
                "chainId": self.chain_id,
                "from": from_addr,
                "to": to,
                "data": data,
                "value": value,
                "gas": gas,
                "maxFeePerGas": max_fee,
                "maxPriorityFeePerGas": max_priority,
                "nonce": nonce,
                "type": 2,  # EIP-1559 transaction type
            }

            logger.debug(f"Built transaction: {tx}")
            return tx

        except Exception as e:
            logger.error(f"Failed to build transaction: {e}")
            raise

    def sign(self, tx: dict[str, Any], private_key_hex: str) -> bytes:
        """Sign transaction with private key.

        Args:
            tx: Transaction dictionary
            private_key_hex: Private key in hex format

        Returns:
            Raw signed transaction bytes
        """
        try:
            account: LocalAccount = Account.from_key(bytes.fromhex(private_key_hex))
            signed = account.sign_transaction(tx)

            logger.debug(f"Signed transaction for {account.address}")
            return signed.rawTransaction

        except Exception as e:
            logger.error(f"Failed to sign transaction: {e}")
            raise

    def estimate_gas(self, tx_params: dict[str, Any]) -> int:
        """Estimate gas for transaction.

        Args:
            tx_params: Transaction parameters

        Returns:
            Estimated gas limit
        """
        try:
            # Remove fields that aren't needed for estimation
            estimate_params = {
                "from": tx_params.get("from"),
                "to": tx_params.get("to"),
                "data": tx_params.get("data", b""),
                "value": tx_params.get("value", 0),
            }

            gas_estimate = self.web3.eth.estimate_gas(estimate_params)

            # Add 20% buffer for safety
            gas_with_buffer = int(gas_estimate * 1.2)

            logger.debug(
                f"Estimated gas: {gas_estimate}, with buffer: {gas_with_buffer}"
            )
            return gas_with_buffer

        except Exception as e:
            logger.error(f"Failed to estimate gas: {e}")
            # Return conservative fallback
            fallback_gas = 100000
            logger.warning(f"Using fallback gas limit: {fallback_gas}")
            return fallback_gas
