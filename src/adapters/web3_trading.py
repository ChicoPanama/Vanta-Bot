"""
Web3 trading adapter - handles direct contract interactions.

This module provides low-level contract calls with manual parameter packing,
bypassing SDK scaling issues entirely.
"""

import json
import logging
from typing import Optional

from eth_account import Account
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from ..core.models import ContractStatus, TradeInput, TradeResult, WalletInfo

logger = logging.getLogger(__name__)


class Web3TradingAdapter:
    """Web3 adapter for direct contract trading operations."""

    def __init__(self, rpc_url: str, private_key: str, trading_address: str):
        """
        Initialize the Web3 trading adapter.

        Args:
            rpc_url: RPC endpoint URL
            private_key: Private key for signing transactions
            trading_address: Trading contract address
        """
        self.rpc_url = rpc_url
        self.trading_address = Web3.to_checksum_address(trading_address)

        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to RPC: {rpc_url}")

        # Initialize account
        self.account = Account.from_key(private_key)
        self.wallet_address = self.account.address

        # Load trading ABI
        with open("config/abis/current/Trading.json") as f:
            trading_data = json.load(f)
        self.trading_abi = trading_data["abi"]

        # Initialize contract
        self.trading_contract = self.w3.eth.contract(
            address=self.trading_address, abi=self.trading_abi
        )

        logger.info("Web3 Trading Adapter initialized")
        logger.info(f"  RPC: {rpc_url}")
        logger.info(f"  Contract: {self.trading_address}")
        logger.info(f"  Wallet: {self.wallet_address}")

    def get_contract_status(self) -> ContractStatus:
        """
        Get current contract status including pause state.

        Returns:
            ContractStatus with current contract information
        """
        try:
            # Check if contract is paused
            is_paused = self.trading_contract.functions.paused().call()

            # Get operator address
            operator = self.trading_contract.functions.operator().call()

            # Get max slippage (might fail if paused)
            max_slippage = None
            try:
                max_slippage = self.trading_contract.functions._MAX_SLIPPAGE().call()
            except Exception as e:
                logger.warning(f"Could not get max slippage: {e}")

            # Get pair infos address
            pair_infos = self.trading_contract.functions.pairInfos().call()

            return ContractStatus(
                is_paused=is_paused,
                operator=operator,
                max_slippage=max_slippage or 0,
                pair_infos_address=pair_infos,
                last_updated=self.w3.eth.get_block("latest")["timestamp"],
            )

        except Exception as e:
            logger.error(f"Failed to get contract status: {e}")
            raise

    def get_wallet_info(self) -> WalletInfo:
        """
        Get current wallet information including balances.

        Returns:
            WalletInfo with current wallet state
        """
        try:
            # Get ETH balance
            eth_balance_wei = self.w3.eth.get_balance(self.wallet_address)
            eth_balance = self.w3.from_wei(eth_balance_wei, "ether")

            # Get USDC balance (assuming USDC contract at known address)
            usdc_address = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
            usdc_balance = self._get_erc20_balance(usdc_address)

            return WalletInfo(
                address=self.wallet_address,
                eth_balance=eth_balance,
                usdc_balance=usdc_balance,
                is_connected=True,
            )

        except Exception as e:
            logger.error(f"Failed to get wallet info: {e}")
            raise

    def _get_erc20_balance(self, token_address: str) -> float:
        """Get ERC20 token balance."""
        try:
            # Simple ERC20 balanceOf call
            token_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=[
                    {
                        "constant": True,
                        "inputs": [{"name": "_owner", "type": "address"}],
                        "name": "balanceOf",
                        "outputs": [{"name": "balance", "type": "uint256"}],
                        "type": "function",
                    }
                ],
            )

            balance = token_contract.functions.balanceOf(self.wallet_address).call()
            # USDC has 6 decimals
            return balance / (10**6)

        except Exception as e:
            logger.error(f"Failed to get ERC20 balance for {token_address}: {e}")
            return 0.0

    def staticcall_trade(
        self, trade: TradeInput, order_type: int, slippage: int
    ) -> tuple[bool, Optional[str]]:
        """
        Perform a static call to validate trade parameters.

        Args:
            trade: Trade input parameters
            order_type: Order type (0 for market, 1 for limit)
            slippage: Slippage in 1e10 scale

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Build transaction data
            tx_data = self.trading_contract.functions.openTrade(
                trade, order_type, slippage
            )._encode_transaction_data()

            # Perform static call
            self.w3.eth.call(
                {
                    "to": self.trading_address,
                    "data": tx_data,
                    "from": self.wallet_address,
                }
            )

            logger.info("✅ Staticcall validation passed - trade should succeed")
            return True, None

        except Exception as e:
            error_msg = self._decode_error(e)
            logger.error(f"❌ Staticcall validation failed: {error_msg}")
            return False, error_msg

    def send_trade(
        self,
        trade: TradeInput,
        order_type: int,
        slippage: int,
        gas_price: Optional[int] = None,
    ) -> TradeResult:
        """
        Send a trade transaction to the blockchain.

        Args:
            trade: Trade input parameters
            order_type: Order type (0 for market, 1 for limit)
            slippage: Slippage in 1e10 scale
            gas_price: Optional gas price override

        Returns:
            TradeResult with transaction details or error information
        """
        try:
            # Get current gas price if not provided
            if gas_price is None:
                gas_price = self.w3.eth.gas_price

            # Build transaction
            transaction = self.trading_contract.functions.openTrade(
                trade, order_type, slippage
            ).build_transaction(
                {
                    "from": self.wallet_address,
                    "gas": 500000,  # Conservative gas limit
                    "gasPrice": gas_price,
                    "nonce": self.w3.eth.get_transaction_count(self.wallet_address),
                }
            )

            # Sign and send transaction
            signed_txn = self.w3.eth.account.sign_transaction(
                transaction, self.account.key
            )
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

            # Wait for transaction receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt.status == 1:
                logger.info("🎉 TRADE EXECUTED SUCCESSFULLY!")
                logger.info(f"   Transaction Hash: {tx_hash.hex()}")
                logger.info(f"   BaseScan URL: https://basescan.org/tx/{tx_hash.hex()}")
                logger.info(f"   Block Number: {receipt.blockNumber}")
                logger.info(f"   Gas Used: {receipt.gasUsed}")

                return TradeResult(
                    success=True,
                    transaction_hash=tx_hash.hex(),
                    error_message=None,
                    gas_used=receipt.gasUsed,
                    block_number=receipt.blockNumber,
                )
            else:
                error_msg = "Transaction failed"
                logger.error(f"❌ Transaction failed: {error_msg}")

                return TradeResult(
                    success=False,
                    transaction_hash=tx_hash.hex(),
                    error_message=error_msg,
                    gas_used=receipt.gasUsed,
                    block_number=receipt.blockNumber,
                )

        except Exception as e:
            error_msg = self._decode_error(e)
            logger.error(f"❌ Trade execution failed: {error_msg}")

            return TradeResult(
                success=False,
                transaction_hash=None,
                error_message=error_msg,
                gas_used=None,
                block_number=None,
            )

    def _decode_error(self, error: Exception) -> str:
        """
        Decode contract errors to human-readable messages.

        Args:
            error: Exception from contract call

        Returns:
            Human-readable error message
        """
        error_str = str(error)

        # Common error mappings
        if "INVALID_SLIPPAGE" in error_str:
            return "Invalid slippage - value exceeds contract limits or format is incorrect"
        elif "BELOW_MIN_POS" in error_str:
            return "Position size below minimum allowed"
        elif "ABOVE_MAX_POS" in error_str:
            return "Position size above maximum allowed"
        elif "INVALID_LEVERAGE" in error_str:
            return "Invalid leverage - exceeds maximum allowed"
        elif "PAUSED" in error_str or "paused" in error_str.lower():
            return "Trading is currently paused"
        elif "INSUFFICIENT_BALANCE" in error_str:
            return "Insufficient balance for trade"
        else:
            return f"Contract error: {error_str}"

    def get_contract_limits(self) -> dict[str, int]:
        """
        Get contract trading limits.

        Returns:
            Dictionary with contract limits
        """
        try:
            limits = {}

            # Try to get max slippage
            try:
                limits["max_slippage"] = (
                    self.trading_contract.functions._MAX_SLIPPAGE().call()
                )
            except:
                limits["max_slippage"] = 500_000_000  # 5% default

            # Try to get pair count
            try:
                limits["max_pairs"] = self.trading_contract.functions.pairCount().call()
            except:
                limits["max_pairs"] = 100  # Conservative default

            # Default limits for other parameters
            limits["min_position_size"] = 1_000_000  # $1 USDC in 6dp
            limits["max_position_size"] = 100_000_000_000  # $100k USDC in 6dp
            limits["max_leverage"] = 500_000_000_000  # 50x in 1e10 scale

            return limits

        except Exception as e:
            logger.error(f"Failed to get contract limits: {e}")
            # Return conservative defaults
            return {
                "min_position_size": 1_000_000,
                "max_position_size": 100_000_000_000,
                "max_leverage": 500_000_000_000,
                "max_slippage": 500_000_000,
                "max_pairs": 100,
            }
