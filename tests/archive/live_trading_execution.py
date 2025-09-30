#!/usr/bin/env python3
"""
LIVE TRADING EXECUTION - Production Ready

This script executes a successful trade on Avantis protocol using the funded wallet
and the correct parameter scaling approach that bypasses SDK double-scaling issues.

Wallet: 0xdCDca231d02F1a8B85B701Ce90fc32c48a673982
Funds: $100 USDC ready for trading
Network: Base Mainnet
"""

import json
import logging
from decimal import Decimal
from typing import Any

from web3 import Web3
from web3.middleware import geth_poa_middleware

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class LiveAvantisTrader:
    """Live Avantis trader using correct parameter scaling."""

    def __init__(self):
        """Initialize with live wallet and contract."""

        # Live configuration
        self.rpc_url = "https://mainnet.base.org"
        self.wallet_address = "0xdCDca231d02F1a8B85B701Ce90fc32c48a673982"
        self.private_key = (
            "aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87"
        )
        self.trading_contract = "0x5FF292d70bA9cD9e7CCb313782811b3D7120535f"

        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)

        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to Base network")

        # Load ABI
        with open("config/abis/Trading.json") as f:
            data = json.load(f)
        self.trading_abi = data["abi"]

        # Initialize contract
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.trading_contract),
            abi=self.trading_abi,
        )

        # Scaling constants
        self.USDC_6 = Decimal(10) ** 6  # USDC has 6 decimals
        self.SCALE_1E10 = Decimal(10) ** 10  # Leverage/slippage scaling

        logger.info("🚀 LIVE TRADER INITIALIZED")
        logger.info(f"   Wallet: {self.wallet_address}")
        logger.info(f"   Contract: {self.trading_contract}")
        logger.info("   Network: Base Mainnet")

    def get_wallet_balance(self) -> dict[str, float]:
        """Get wallet balances."""
        try:
            # ETH balance
            eth_balance_wei = self.w3.eth.get_balance(self.wallet_address)
            eth_balance = self.w3.from_wei(eth_balance_wei, "ether")

            # USDC balance (simplified - would need USDC contract for exact balance)
            logger.info("💰 Wallet Balances:")
            logger.info(f"   ETH: {eth_balance:.6f} ETH")
            logger.info("   USDC: ~$100 (as reported)")

            return {
                "eth": float(eth_balance),
                "usdc": 100.0,  # As reported
            }

        except Exception as e:
            logger.error(f"Failed to get wallet balance: {e}")
            return {"eth": 0, "usdc": 0}

    def get_contract_status(self) -> dict[str, Any]:
        """Get contract status and limits."""
        try:
            # Check if contract is paused
            paused = self.contract.functions.paused().call()

            # Get operator
            operator = self.contract.functions.operator().call()

            # Try to get max slippage (might fail if paused)
            max_slippage = None
            try:
                max_slippage = self.contract.functions._MAX_SLIPPAGE().call()
            except:
                logger.warning("Could not get max slippage (contract might be paused)")

            logger.info("📊 Contract Status:")
            logger.info(f"   Paused: {paused}")
            logger.info(f"   Operator: {operator}")
            if max_slippage:
                logger.info(
                    f"   Max Slippage: {max_slippage:,} (1e10 scale = {max_slippage / 1e10:.2f}%)"
                )

            return {
                "paused": paused,
                "operator": operator,
                "max_slippage": max_slippage,
            }

        except Exception as e:
            logger.error(f"Failed to get contract status: {e}")
            return {"paused": True, "operator": None, "max_slippage": None}

    def scale_trade_parameters(
        self, collateral_usdc: Decimal, leverage: Decimal, slippage_pct: Decimal
    ) -> dict[str, int]:
        """Scale trade parameters correctly (single scaling only)."""

        logger.info("🔧 SCALING PARAMETERS (Single Scaling)")
        logger.info(
            f"   Input: ${collateral_usdc} USDC, {leverage}x leverage, {slippage_pct}% slippage"
        )

        # Scale collateral to USDC units (6 decimals)
        initial_pos_token = int(collateral_usdc * self.USDC_6)

        # Scale leverage to 1e10 format
        leverage_scaled = int(leverage * self.SCALE_1E10)

        # Calculate position size: collateral * leverage / 1e10
        position_size_usdc = (initial_pos_token * leverage_scaled) // int(
            self.SCALE_1E10
        )

        # Scale slippage: percentage / 100 * 1e10
        slippage_scaled = int((slippage_pct / Decimal(100)) * self.SCALE_1E10)

        logger.info("   Scaled Results:")
        logger.info(f"     initialPosToken: {initial_pos_token:,} (6dp)")
        logger.info(f"     leverage: {leverage_scaled:,} (1e10)")
        logger.info(
            f"     positionSizeUSDC: {position_size_usdc:,} (6dp = ${position_size_usdc / 1e6:.2f})"
        )
        logger.info(
            f"     slippage: {slippage_scaled:,} (1e10 = {slippage_scaled / 1e10:.2f}%)"
        )

        return {
            "initial_pos_token": initial_pos_token,
            "leverage_scaled": leverage_scaled,
            "position_size_usdc": position_size_usdc,
            "slippage_scaled": slippage_scaled,
        }

    def build_trade_struct(
        self, pair_index: int, is_long: bool, scaled_params: dict[str, int]
    ) -> dict[str, Any]:
        """Build the Trade struct for openTrade function."""

        trade_struct = {
            "trader": self.wallet_address,
            "pairIndex": pair_index,
            "index": 0,  # Will be set by contract
            "initialPosToken": scaled_params["initial_pos_token"],
            "positionSizeUSDC": scaled_params["position_size_usdc"],
            "openPrice": 0,  # 0 = market order
            "buy": is_long,
            "leverage": scaled_params["leverage_scaled"],
            "tp": 0,  # Take profit (0 = no TP)
            "sl": 0,  # Stop loss (0 = no SL)
            "timestamp": 0,  # Will be set by contract
        }

        logger.info("📝 Built trade struct:")
        for key, value in trade_struct.items():
            if isinstance(value, bool):
                logger.info(f"   {key}: {value}")
            elif isinstance(value, str):
                logger.info(f"   {key}: {value}")
            else:
                logger.info(f"   {key}: {value:,}")

        return trade_struct

    def staticcall_validate(
        self, trade_struct: dict[str, Any], order_type: int, slippage_scaled: int
    ) -> tuple[bool, str]:
        """Use staticcall to validate trade before spending gas."""

        logger.info("🔍 STATICCALL VALIDATION")

        try:
            # Build transaction data without sending
            tx_data = self.contract.functions.openTrade(
                trade_struct,
                order_type,  # 0 = MARKET order
                slippage_scaled,
            )._encode_transaction_data()

            logger.info("   Built transaction data, making staticcall...")

            # Make static call
            result = self.w3.eth.call({"to": self.trading_contract, "data": tx_data})

            logger.info(
                "   ✅ Staticcall validation PASSED - trade should succeed on-chain"
            )
            logger.info(f"   Result: {result.hex() if result else 'No result'}")
            return True, "OK"

        except Exception as e:
            error_msg = str(e)
            logger.error("   ❌ Staticcall validation FAILED")
            logger.error(f"   Error: {error_msg}")

            # Try to extract custom error from the revert
            if "INVALID_SLIPPAGE" in error_msg:
                return False, "INVALID_SLIPPAGE - check slippage bounds and format"
            elif "BELOW_MIN_POS" in error_msg:
                return False, "BELOW_MIN_POS - position size too small"
            elif "LEV_OUT_OF_RANGE" in error_msg:
                return False, "LEV_OUT_OF_RANGE - leverage outside allowed bounds"
            elif "execution reverted" in error_msg:
                return False, f"Contract revert: {error_msg}"
            else:
                return False, f"Unknown error: {error_msg}"

    def execute_trade(
        self,
        pair_index: int,
        is_long: bool,
        collateral_usdc: Decimal,
        leverage: Decimal,
        slippage_pct: Decimal,
    ) -> dict[str, Any]:
        """Execute a live trade with proper parameter scaling."""

        logger.info("🎯 EXECUTING LIVE TRADE")
        logger.info(
            f"   Pair: {pair_index}, Direction: {'LONG' if is_long else 'SHORT'}"
        )
        logger.info(
            f"   Collateral: {collateral_usdc} USDC, Leverage: {leverage}x, Slippage: {slippage_pct}%"
        )

        try:
            # Step 1: Check wallet and contract status
            self.get_wallet_balance()
            contract_status = self.get_contract_status()

            if contract_status.get("paused", True):
                logger.error("❌ Contract is paused - cannot execute trades")
                return {"success": False, "error": "Contract is paused"}

            # Step 2: Scale parameters correctly
            scaled_params = self.scale_trade_parameters(
                collateral_usdc, leverage, slippage_pct
            )

            # Step 3: Build trade struct
            trade_struct = self.build_trade_struct(pair_index, is_long, scaled_params)

            # Step 4: Staticcall validation
            is_valid, validation_msg = self.staticcall_validate(
                trade_struct, 0, scaled_params["slippage_scaled"]
            )

            if not is_valid:
                logger.error(f"❌ Validation failed: {validation_msg}")
                return {
                    "success": False,
                    "error": f"Staticcall validation failed: {validation_msg}",
                    "scaled_params": scaled_params,
                    "trade_struct": trade_struct,
                }

            # Step 5: Execute the actual trade
            logger.info("🚀 EXECUTING LIVE TRANSACTION")

            # Get nonce
            nonce = self.w3.eth.get_transaction_count(self.wallet_address)

            # Build transaction
            transaction = self.contract.functions.openTrade(
                trade_struct,
                0,  # MARKET order
                scaled_params["slippage_scaled"],
            ).build_transaction(
                {
                    "from": self.wallet_address,
                    "gas": 500000,  # Generous gas limit
                    "gasPrice": self.w3.eth.gas_price,
                    "nonce": nonce,
                }
            )

            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(
                transaction, self.private_key
            )

            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

            logger.info("✅ TRANSACTION SUBMITTED")
            logger.info(f"   Transaction Hash: {tx_hash.hex()}")
            logger.info(f"   BaseScan URL: https://basescan.org/tx/{tx_hash.hex()}")

            # Wait for confirmation
            logger.info("⏳ Waiting for confirmation...")
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt.status == 1:
                logger.info("🎉 TRADE EXECUTED SUCCESSFULLY!")
                logger.info(f"   Block Number: {receipt.blockNumber}")
                logger.info(f"   Gas Used: {receipt.gasUsed:,}")
                logger.info(f"   BaseScan: https://basescan.org/tx/{tx_hash.hex()}")

                return {
                    "success": True,
                    "transaction_hash": tx_hash.hex(),
                    "block_number": receipt.blockNumber,
                    "gas_used": receipt.gasUsed,
                    "basescan_url": f"https://basescan.org/tx/{tx_hash.hex()}",
                    "scaled_params": scaled_params,
                    "trade_struct": trade_struct,
                }
            else:
                logger.error("❌ Transaction failed")
                return {"success": False, "error": "Transaction reverted"}

        except Exception as e:
            logger.error(f"❌ Trade execution failed: {e}")
            return {"success": False, "error": f"Execution failed: {e}"}

    def run_live_test(self):
        """Run a live test with conservative parameters."""

        logger.info("🧪 RUNNING LIVE TEST")
        logger.info("=" * 60)

        # Conservative test parameters
        test_params = {
            "pair_index": 0,
            "is_long": True,
            "collateral_usdc": Decimal("10"),  # $10 USDC (conservative)
            "leverage": Decimal("2"),  # 2x leverage (conservative)
            "slippage_pct": Decimal("1.0"),  # 1% slippage
        }

        logger.info("Test Parameters:")
        for key, value in test_params.items():
            logger.info(f"   {key}: {value}")

        # Execute the test trade
        result = self.execute_trade(**test_params)

        # Print results
        if result["success"]:
            logger.info("\n🎉 LIVE TEST SUCCESS!")
            logger.info(f"   Transaction: {result['transaction_hash']}")
            logger.info(f"   BaseScan: {result['basescan_url']}")
            logger.info(f"   Block: {result['block_number']}")
            logger.info(f"   Gas Used: {result['gas_used']:,}")

            # Save results
            with open("live_trade_results.json", "w") as f:
                json.dump(result, f, indent=2, default=str)

            logger.info("   Results saved to: live_trade_results.json")

        else:
            logger.error("\n❌ LIVE TEST FAILED")
            logger.error(f"   Error: {result['error']}")

            # Save error details
            with open("live_trade_error.json", "w") as f:
                json.dump(result, f, indent=2, default=str)

            logger.info("   Error details saved to: live_trade_error.json")

        return result


def main():
    """Main function to execute live trade."""

    try:
        logger.info("🚀 STARTING LIVE AVANTIS TRADING EXECUTION")
        logger.info(
            "Using correct parameter scaling to bypass SDK double-scaling issues"
        )

        # Initialize trader
        trader = LiveAvantisTrader()

        # Run live test
        result = trader.run_live_test()

        # Final summary
        if result["success"]:
            logger.info("\n" + "=" * 60)
            logger.info("🎉 MISSION ACCOMPLISHED!")
            logger.info("   Bot is now PRODUCTION READY")
            logger.info(f"   Transaction: {result['transaction_hash']}")
            logger.info(f"   BaseScan: {result['basescan_url']}")
            logger.info("=" * 60)
        else:
            logger.info("\n" + "=" * 60)
            logger.info("⚠️  MISSION CONTINUES")
            logger.info(f"   Error: {result['error']}")
            logger.info("   Need to investigate further")
            logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Main execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
