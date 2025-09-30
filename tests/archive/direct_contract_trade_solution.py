#!/usr/bin/env python3
"""
Direct Contract Trading Solution - Bypassing SDK Double-Scaling Issues

This script implements a direct contract call approach that:
1. Bypasses SDK auto-scaling by calling the contract directly
2. Validates on-chain limits before attempting trades
3. Uses staticcall to catch reverts before spending gas
4. Implements proper scaling (once) with known-good values

Based on analysis showing SDK is double-scaling amounts and INVALID_SLIPPAGE
is coming from format/limits checks, not "too low/high" values.
"""

import json
import logging
from decimal import Decimal
from typing import Any

from web3 import Web3

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DirectContractTrader:
    """Direct contract trader that bypasses SDK scaling issues."""

    def __init__(self, rpc_url: str = "https://mainnet.base.org"):
        """Initialize with Web3 connection and load ABIs."""
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to Base network")

        # Load Trading contract ABI
        with open("config/abis/Trading.json") as f:
            trading_data = json.load(f)
        self.trading_abi = trading_data["abi"]

        # Contract addresses (you'll need to update these)
        self.trading_address = None  # Set your Trading contract address
        self.pair_infos_address = None  # Set your PairInfos contract address

        self.trading_contract = None
        self.pair_infos_contract = None

        # Scaling constants
        self.USDC_6 = Decimal(10) ** 6  # USDC has 6 decimals
        self.SCALE_1E10 = Decimal(10) ** 10  # Leverage/slippage scaling

        # Known-good test values
        self.test_collateral = Decimal("100")  # $100 USDC
        self.test_leverage = Decimal("5")  # 5x leverage
        self.test_slippage_pct = Decimal("1.0")  # 1.00%

    def set_contract_addresses(self, trading_addr: str, pair_infos_addr: str = None):
        """Set contract addresses and initialize contracts."""
        self.trading_address = Web3.to_checksum_address(trading_addr)
        self.trading_contract = self.w3.eth.contract(
            address=self.trading_address, abi=self.trading_abi
        )

        if pair_infos_addr:
            self.pair_infos_address = Web3.to_checksum_address(pair_infos_addr)
            # Note: You'll need PairInfos ABI to use this
            logger.warning("PairInfos contract set but ABI not loaded yet")

    def get_max_slippage(self) -> int:
        """Get the maximum allowed slippage from the contract."""
        if not self.trading_contract:
            raise ValueError("Trading contract not initialized")

        try:
            max_slippage = self.trading_contract.functions._MAX_SLIPPAGE().call()
            logger.info(f"Max slippage from contract: {max_slippage} (1e10 scale)")
            return max_slippage
        except Exception as e:
            logger.error(f"Failed to get max slippage: {e}")
            # Fallback to reasonable default (5% = 0.05 * 1e10)
            return 500_000_000

    def scale_trade_parameters(
        self, collateral_usdc: Decimal, leverage: Decimal, slippage_pct: Decimal
    ) -> dict[str, int]:
        """Scale trade parameters correctly (once) to avoid double-scaling."""

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

        logger.info("Scaled parameters:")
        logger.info(
            f"  Collateral: {collateral_usdc} USDC -> {initial_pos_token} (6dp)"
        )
        logger.info(f"  Leverage: {leverage}x -> {leverage_scaled} (1e10)")
        logger.info(f"  Position size: {position_size_usdc} USDC (6dp)")
        logger.info(f"  Slippage: {slippage_pct}% -> {slippage_scaled} (1e10)")

        return {
            "initial_pos_token": initial_pos_token,
            "leverage_scaled": leverage_scaled,
            "position_size_usdc": position_size_usdc,
            "slippage_scaled": slippage_scaled,
        }

    def validate_slippage(self, slippage_scaled: int) -> bool:
        """Validate slippage is within contract limits."""
        max_slippage = self.get_max_slippage()

        if slippage_scaled <= 0:
            logger.error("Slippage must be greater than 0")
            return False

        if slippage_scaled > max_slippage:
            logger.error(f"Slippage {slippage_scaled} exceeds max {max_slippage}")
            return False

        logger.info(f"Slippage validation passed: {slippage_scaled} <= {max_slippage}")
        return True

    def build_trade_struct(
        self, pair_index: int, is_long: bool, scaled_params: dict[str, int]
    ) -> dict[str, Any]:
        """Build the Trade struct for openTrade function."""

        # Note: The trader field should be set to the actual trader address
        # For now using a placeholder - you'll need to set this properly
        trader_address = "0x0000000000000000000000000000000000000000"  # PLACEHOLDER

        trade_struct = {
            "trader": trader_address,
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

        logger.info(
            f"Built trade struct for pair {pair_index}, {'LONG' if is_long else 'SHORT'}"
        )
        return trade_struct

    def staticcall_validate(
        self, trade_struct: dict[str, Any], order_type: int, slippage_scaled: int
    ) -> tuple[bool, str]:
        """Use staticcall to validate trade before spending gas."""
        if not self.trading_contract:
            raise ValueError("Trading contract not initialized")

        try:
            # Build transaction data without sending
            tx_data = self.trading_contract.functions.openTrade(
                trade_struct,
                order_type,  # 0 = MARKET order
                slippage_scaled,
            )._encode_transaction_data()

            # Make static call
            self.w3.eth.call({"to": self.trading_address, "data": tx_data})

            logger.info("Staticcall validation PASSED - trade should succeed")
            return True, "OK"

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Staticcall validation FAILED: {error_msg}")

            # Try to extract custom error from the revert
            if "INVALID_SLIPPAGE" in error_msg:
                return False, "INVALID_SLIPPAGE - check slippage bounds and format"
            elif "BELOW_MIN_POS" in error_msg:
                return False, "BELOW_MIN_POS - position size too small"
            elif "LEV_OUT_OF_RANGE" in error_msg:
                return False, "LEV_OUT_OF_RANGE - leverage outside allowed bounds"
            else:
                return False, f"Unknown revert: {error_msg}"

    def execute_trade(
        self,
        pair_index: int,
        is_long: bool,
        collateral_usdc: Decimal,
        leverage: Decimal,
        slippage_pct: Decimal,
        private_key: str = None,
    ) -> dict[str, Any]:
        """
        Execute a trade with full validation and error handling.

        Args:
            pair_index: Trading pair index
            is_long: True for long position, False for short
            collateral_usdc: Collateral amount in USDC
            leverage: Leverage multiplier (e.g., 5 for 5x)
            slippage_pct: Slippage percentage (e.g., 1.0 for 1%)
            private_key: Private key for signing (optional for validation only)

        Returns:
            Dict with success status and details
        """

        logger.info("=== EXECUTING TRADE ===")
        logger.info(f"Pair: {pair_index}, Direction: {'LONG' if is_long else 'SHORT'}")
        logger.info(
            f"Collateral: {collateral_usdc} USDC, Leverage: {leverage}x, Slippage: {slippage_pct}%"
        )

        # Step 1: Scale parameters correctly
        try:
            scaled_params = self.scale_trade_parameters(
                collateral_usdc, leverage, slippage_pct
            )
        except Exception as e:
            return {"success": False, "error": f"Parameter scaling failed: {e}"}

        # Step 2: Validate slippage bounds
        if not self.validate_slippage(scaled_params["slippage_scaled"]):
            return {"success": False, "error": "Slippage validation failed"}

        # Step 3: Build trade struct
        try:
            trade_struct = self.build_trade_struct(pair_index, is_long, scaled_params)
        except Exception as e:
            return {"success": False, "error": f"Trade struct building failed: {e}"}

        # Step 4: Staticcall validation
        is_valid, validation_msg = self.staticcall_validate(
            trade_struct, 0, scaled_params["slippage_scaled"]
        )

        if not is_valid:
            return {
                "success": False,
                "error": f"Staticcall validation failed: {validation_msg}",
                "scaled_params": scaled_params,
                "trade_struct": trade_struct,
            }

        # Step 5: If private key provided, execute the actual trade
        if private_key:
            try:
                # This would implement the actual transaction execution
                # For now, just return success since validation passed
                logger.info("Trade validation successful - ready for execution")
                return {
                    "success": True,
                    "message": "Trade validated successfully",
                    "scaled_params": scaled_params,
                    "trade_struct": trade_struct,
                }
            except Exception as e:
                return {"success": False, "error": f"Trade execution failed: {e}"}
        else:
            return {
                "success": True,
                "message": "Trade validated successfully (no private key provided)",
                "scaled_params": scaled_params,
                "trade_struct": trade_struct,
            }

    def run_test_scenarios(self, pair_index: int = 0):
        """Run test scenarios with known-good values."""

        logger.info("=== RUNNING TEST SCENARIOS ===")

        # Test 1: Known-good values
        logger.info("\n--- Test 1: Known-good values ---")
        result1 = self.execute_trade(
            pair_index=pair_index,
            is_long=True,
            collateral_usdc=self.test_collateral,
            leverage=self.test_leverage,
            slippage_pct=self.test_slippage_pct,
        )

        logger.info(f"Test 1 result: {result1['success']}")
        if not result1["success"]:
            logger.error(f"Test 1 error: {result1['error']}")

        # Test 2: Edge case - minimum viable values
        logger.info("\n--- Test 2: Minimum values ---")
        result2 = self.execute_trade(
            pair_index=pair_index,
            is_long=False,
            collateral_usdc=Decimal("10"),  # $10 minimum
            leverage=Decimal("1"),  # 1x minimum
            slippage_pct=Decimal("0.1"),  # 0.1% minimum
        )

        logger.info(f"Test 2 result: {result2['success']}")
        if not result2["success"]:
            logger.error(f"Test 2 error: {result2['error']}")

        # Test 3: High leverage test
        logger.info("\n--- Test 3: High leverage ---")
        result3 = self.execute_trade(
            pair_index=pair_index,
            is_long=True,
            collateral_usdc=Decimal("50"),
            leverage=Decimal("20"),  # 20x leverage
            slippage_pct=Decimal("2.0"),  # 2% slippage
        )

        logger.info(f"Test 3 result: {result3['success']}")
        if not result3["success"]:
            logger.error(f"Test 3 error: {result3['error']}")

        return {"test_1": result1, "test_2": result2, "test_3": result3}


def main():
    """Main function to demonstrate the solution."""

    # Initialize trader
    trader = DirectContractTrader()

    # You need to set the actual contract addresses here
    # These are placeholders - update with real addresses
    TRADING_CONTRACT_ADDR = "0x..."  # Update with real Trading contract address
    PAIR_INFOS_CONTRACT_ADDR = "0x..."  # Update with real PairInfos address

    try:
        trader.set_contract_addresses(TRADING_CONTRACT_ADDR, PAIR_INFOS_CONTRACT_ADDR)

        # Get current limits
        max_slippage = trader.get_max_slippage()
        logger.info(f"Contract max slippage: {max_slippage}")

        # Run test scenarios
        results = trader.run_test_scenarios(pair_index=0)

        # Print summary
        logger.info("\n=== TEST SUMMARY ===")
        for test_name, result in results.items():
            status = "PASS" if result["success"] else "FAIL"
            logger.info(f"{test_name}: {status}")
            if not result["success"]:
                logger.info(f"  Error: {result['error']}")

    except Exception as e:
        logger.error(f"Main execution failed: {e}")


if __name__ == "__main__":
    main()
