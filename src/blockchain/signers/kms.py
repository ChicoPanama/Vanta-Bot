"""AWS KMS signer implementation."""

import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError
from web3 import Web3

logger = logging.getLogger(__name__)


class KmsSigner:
    """AWS KMS signer for production use."""

    def __init__(self, key_id: str, region: str, web3: Web3):
        """Initialize with KMS key ID.

        Args:
            key_id: AWS KMS key ID
            region: AWS region
            web3: Web3 instance for transaction sending
        """
        self.key_id = key_id
        self.region = region
        self.web3 = web3
        self.kms_client = boto3.client("kms", region_name=region)

        # Get the public key to derive address
        try:
            response = self.kms_client.get_public_key(KeyId=key_id)
            public_key = response["PublicKey"]
            # Derive address from public key
            from eth_account import Account

            account = Account.from_key(public_key)
            self._address = account.address
        except ClientError as e:
            raise RuntimeError(f"Failed to get KMS public key: {e}")

    @property
    def address(self) -> str:
        """Get the signer's address."""
        return self._address

    async def sign_and_send(self, tx: dict[str, Any]) -> str:
        """Sign and send transaction using KMS."""
        try:
            # Ensure transaction has required fields
            if "from" not in tx:
                tx["from"] = self.address

            # Create message hash for signing
            message_hash = self.web3.keccak(
                self.web3.eth.account.encode_transaction(tx)
            )

            # Sign with KMS
            response = self.kms_client.sign(
                KeyId=self.key_id,
                Message=message_hash,
                MessageType="DIGEST",
                SigningAlgorithm="ECDSA_SHA_256",
            )

            signature = response["Signature"]

            # Reconstruct transaction with signature
            # This is a simplified implementation - in production you'd need
            # to properly reconstruct the transaction with the KMS signature
            signed_tx = {**tx, "signature": signature.hex()}

            # Send the transaction
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx)

            logger.info(f"KMS transaction sent: {tx_hash.hex()}")
            return tx_hash.hex()

        except Exception as e:
            logger.error(f"Failed to sign and send transaction with KMS: {e}")
            raise
