"""
Avantis Trader SDK Client Factory and Wrapper

This module provides a thin factory/wrapper around the Avantis Trader SDK's TraderClient
for easy integration with the Vanta Bot.
"""

import logging
import os
from typing import Optional, Union

from avantis_trader_sdk import TraderClient
from web3 import Web3

logger = logging.getLogger(__name__)


class AvantisSDKClient:
    """
    Factory and wrapper for Avantis Trader SDK TraderClient

    Handles initialization, signer setup, and common operations like USDC allowance.
    """

    def __init__(self, rpc_url: Optional[str] = None):
        """
        Initialize the SDK client

        Args:
            rpc_url: Base RPC URL (defaults to BASE_RPC_URL from env)
        """
        self.rpc_url = rpc_url or os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
        self._client: Optional[TraderClient] = None
        self._w3: Optional[Web3] = None

    def get_client(self) -> TraderClient:
        """
        Get or create the TraderClient instance

        Returns:
            TraderClient: Initialized SDK client
        """
        if self._client is None:
            try:
                self._client = TraderClient(self.rpc_url)
                logger.info(
                    f"✅ Avantis TraderClient initialized with RPC: {self.rpc_url}"
                )

                # Set up signer if configured
                self._setup_signer()

            except Exception as e:
                logger.error(f"❌ Failed to initialize TraderClient: {e}")
                raise

        return self._client

    def _setup_signer(self):
        """Set up the trader signer (private key or AWS KMS)"""
        private_key = os.getenv("TRADER_PRIVATE_KEY")
        aws_kms_key_id = os.getenv("AWS_KMS_KEY_ID")
        aws_region = os.getenv("AWS_REGION")

        if private_key:
            try:
                # Remove 0x prefix if present
                if private_key.startswith("0x"):
                    private_key = private_key[2:]

                self._client.set_local_signer(private_key)
                logger.info("✅ Local signer configured with private key")

            except Exception as e:
                logger.error(f"❌ Failed to set local signer: {e}")
                raise

        elif aws_kms_key_id:
            try:
                region = aws_region or "us-east-1"
                self._client.set_aws_kms_signer(aws_kms_key_id, region)
                logger.info(
                    f"✅ AWS KMS signer configured: {aws_kms_key_id} in {region}"
                )

            except Exception as e:
                logger.error(f"❌ Failed to set AWS KMS signer: {e}")
                raise
        else:
            logger.warning(
                "⚠️ No trader signer configured - trading operations will not work"
            )

    def get_signer_address(self) -> Optional[str]:
        """
        Get the signer address if configured

        Returns:
            Optional[str]: Signer address or None if not configured
        """
        try:
            client = self.get_client()
            return client.get_trader_address()
        except Exception as e:
            logger.error(f"❌ Error getting signer address: {e}")
            return None

    def get_web3(self) -> Web3:
        """
        Get or create Web3 instance

        Returns:
            Web3: Web3 instance connected to Base
        """
        if self._w3 is None:
            self._w3 = Web3(Web3.HTTPProvider(self.rpc_url))

            if not self._w3.is_connected():
                raise ConnectionError(f"Failed to connect to Base RPC: {self.rpc_url}")

        return self._w3

    async def ensure_usdc_allowance(
        self, min_usdc: Union[int, float], trader_addr: str
    ) -> bool:
        """
        Ensure USDC allowance for trading is sufficient

        Args:
            min_usdc: Minimum USDC amount needed
            trader_addr: Trader address to check allowance for

        Returns:
            bool: True if allowance is sufficient or was successfully increased
        """
        try:
            client = self.get_client()

            # Check current allowance
            current_allowance = await client.get_usdc_allowance_for_trading(trader_addr)
            logger.info(
                f"Current USDC allowance for {trader_addr}: {current_allowance}"
            )

            if current_allowance >= min_usdc:
                logger.info("✅ USDC allowance is sufficient")
                return True

            # Increase allowance
            logger.info(
                f"⚠️ Increasing USDC allowance from {current_allowance} to {min_usdc}"
            )
            tx_hash = await client.approve_usdc_for_trading(min_usdc)

            if tx_hash:
                logger.info(f"✅ USDC approval transaction sent: {tx_hash}")

                # Re-check allowance after a short delay
                import asyncio

                await asyncio.sleep(2)  # Give transaction time to be mined

                new_allowance = await client.get_usdc_allowance_for_trading(trader_addr)
                logger.info(f"New USDC allowance: {new_allowance}")
                return new_allowance >= min_usdc
            else:
                logger.error("❌ Failed to send USDC approval transaction")
                return False

        except Exception as e:
            logger.error(f"❌ Error ensuring USDC allowance: {e}")
            return False

    def get_balance(self, address: str) -> float:
        """
        Get ETH balance for an address

        Args:
            address: Wallet address

        Returns:
            float: Balance in ETH
        """
        try:
            w3 = self.get_web3()
            balance_wei = w3.eth.get_balance(address)
            return w3.from_wei(balance_wei, "ether")
        except Exception as e:
            logger.error(f"❌ Error getting balance for {address}: {e}")
            return 0.0

    def get_chain_id(self) -> int:
        """
        Get the chain ID

        Returns:
            int: Chain ID (8453 for Base mainnet)
        """
        try:
            w3 = self.get_web3()
            return w3.eth.chain_id
        except Exception as e:
            logger.error(f"❌ Error getting chain ID: {e}")
            return 8453  # Default to Base mainnet


# Global SDK client instance
_sdk_client: Optional[AvantisSDKClient] = None


def get_sdk_client() -> AvantisSDKClient:
    """
    Get the global SDK client instance

    Returns:
        AvantisSDKClient: Global SDK client
    """
    global _sdk_client

    if _sdk_client is None:
        _sdk_client = AvantisSDKClient()

    return _sdk_client


def initialize_sdk_client(rpc_url: Optional[str] = None) -> AvantisSDKClient:
    """
    Initialize the global SDK client

    Args:
        rpc_url: Base RPC URL (optional)

    Returns:
        AvantisSDKClient: Initialized SDK client
    """
    global _sdk_client

    _sdk_client = AvantisSDKClient(rpc_url)
    return _sdk_client
