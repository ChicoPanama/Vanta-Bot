import logging
from typing import Optional

from cryptography.fernet import Fernet

from src.blockchain.base_client import base_client
from src.config.settings import settings
from src.security.key_vault import WalletEncryption

logger = logging.getLogger(__name__)


class WalletManager:
    """Wallet manager with envelope encryption support."""

    def __init__(self):
        self.base_client = base_client
        self._wallet_encryption: Optional[WalletEncryption] = None
        self._legacy_cipher_suite: Optional[Fernet] = None

        # Initialize based on feature flag
        if settings.KEY_ENVELOPE_ENABLED:
            try:
                key_vault = settings.build_key_vault()
                self._wallet_encryption = WalletEncryption(key_vault)
                logger.info("Initialized wallet manager with envelope encryption")
            except Exception as e:
                logger.error(f"Failed to initialize envelope encryption: {e}")
                raise
        else:
            # Legacy mode
            if not settings.ENCRYPTION_KEY:
                raise ValueError("ENCRYPTION_KEY required for legacy mode")
            self._legacy_cipher_suite = Fernet(settings.ENCRYPTION_KEY.encode())
            logger.info("Initialized wallet manager with legacy encryption")

    def create_wallet(self, user_id: str) -> dict:
        """Create new wallet with envelope encryption."""
        wallet = self.base_client.create_wallet()

        if self._wallet_encryption:
            # New envelope encryption
            (
                wrapped_dek,
                encrypted_privkey,
            ) = self._wallet_encryption.create_encrypted_wallet(wallet["private_key"])
            return {
                "address": wallet["address"],
                "private_key": wallet["private_key"],  # Only for immediate use
                "wrapped_dek": wrapped_dek,
                "encrypted_privkey": encrypted_privkey,
                "encryption_version": "v2",
            }
        else:
            # Legacy encryption
            encrypted_private_key = self._encrypt_private_key_legacy(
                wallet["private_key"]
            )
            return {
                "address": wallet["address"],
                "private_key": wallet["private_key"],  # Only for immediate use
                "encrypted_private_key": encrypted_private_key,
                "encryption_version": "v1",
            }

    def get_private_key(self, wallet_data: dict) -> str:
        """Get private key from wallet data (handles both v1 and v2 encryption)."""
        if wallet_data.get("encryption_version") == "v2" and self._wallet_encryption:
            return self._wallet_encryption.decrypt_wallet(
                wallet_data["wrapped_dek"], wallet_data["encrypted_privkey"]
            )
        elif (
            wallet_data.get("encryption_version") == "v1" and self._legacy_cipher_suite
        ):
            return self._decrypt_private_key_legacy(
                wallet_data["encrypted_private_key"]
            )
        else:
            raise ValueError("Unsupported encryption version or missing cipher suite")

    def _encrypt_private_key_legacy(self, private_key: str) -> str:
        """Legacy private key encryption."""
        return self._legacy_cipher_suite.encrypt(private_key.encode()).decode()

    def _decrypt_private_key_legacy(self, encrypted_private_key: str) -> str:
        """Legacy private key decryption."""
        return self._legacy_cipher_suite.decrypt(
            encrypted_private_key.encode()
        ).decode()

    def get_wallet_info(self, address: str):
        """Get wallet balance information"""
        eth_balance = self.base_client.get_balance(address)
        usdc_balance = self.base_client.get_usdc_balance(address)

        return {
            "address": address,
            "eth_balance": eth_balance,
            "usdc_balance": usdc_balance,
        }


# Global instance
wallet_manager = WalletManager()
