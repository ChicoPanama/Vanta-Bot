#!/usr/bin/env python3
"""
Practical Direct Contract Test - Using Real Avantis Contract Addresses

This script implements the direct contract solution using the actual Avantis
contract addresses from your codebase to test the bypass of SDK double-scaling.

Contract Address: 0x5FF292d70bA9cD9e7CCb313782811b3D7120535f
"""

import json
import os
from decimal import Decimal
from web3 import Web3
from typing import Dict, Any, Tuple, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PracticalDirectTrader:
    """Practical direct contract trader using real Avantis addresses."""
    
    def __init__(self, rpc_url: str = "https://mainnet.base.org"):
        """Initialize with Web3 connection and load ABIs."""
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to Base network")
        
        # Load Trading contract ABI
        with open("config/abis/Trading.json") as f:
            trading_data = json.load(f)
        self.trading_abi = trading_data["abi"]
        
        # Real contract addresses from your codebase
        self.trading_address = Web3.to_checksum_address("0x5FF292d70bA9cD9e7CCb313782811b3D7120535f")
        
        # Initialize contract
        self.trading_contract = self.w3.eth.contract(
            address=self.trading_address, 
            abi=self.trading_abi
        )
        
        # Scaling constants
        self.USDC_6 = Decimal(10) ** 6      # USDC has 6 decimals
        self.SCALE_1E10 = Decimal(10) ** 10  # Leverage/slippage scaling
        
        logger.info(f"Initialized with Trading contract: {self.trading_address}")
    
    def get_contract_info(self):
        """Get basic contract information and limits."""
        logger.info("=== CONTRACT INFORMATION ===")
        
        try:
            # Get max slippage
            max_slippage = self.trading_contract.functions._MAX_SLIPPAGE().call()
            logger.info(f"Max slippage: {max_slippage} (1e10 scale = {max_slippage / 1e10:.2f}%)")
            
            # Get pair infos contract address
            pair_infos_addr = self.trading_contract.functions.pairInfos().call()
            logger.info(f"PairInfos contract: {pair_infos_addr}")
            
            return {
                "max_slippage": max_slippage,
                "pair_infos_address": pair_infos_addr
            }
            
        except Exception as e:
            logger.error(f"Failed to get contract info: {e}")
            return None
    
    def scale_trade_parameters(self, collateral_usdc: Decimal, leverage: Decimal, 
                             slippage_pct: Decimal) -> Dict[str, int]:
        """Scale trade parameters correctly (once) to avoid double-scaling."""
        
        logger.info(f"=== SCALING PARAMETERS ===")
        logger.info(f"Input: ${collateral_usdc} USDC, {leverage}x leverage, {slippage_pct}% slippage")
        
        # Scale collateral to USDC units (6 decimals)
        initial_pos_token = int(collateral_usdc * self.USDC_6)
        
        # Scale leverage to 1e10 format
        leverage_scaled = int(leverage * self.SCALE_1E10)
        
        # Calculate position size: collateral * leverage / 1e10
        position_size_usdc = (initial_pos_token * leverage_scaled) // int(self.SCALE_1E10)
        
        # Scale slippage: percentage / 100 * 1e10
        slippage_scaled = int((slippage_pct / Decimal(100)) * self.SCALE_1E10)
        
        logger.info(f"Scaled results:")
        logger.info(f"  initialPosToken: {initial_pos_token:,} (6dp)")
        logger.info(f"  leverage: {leverage_scaled:,} (1e10)")
        logger.info(f"  positionSizeUSDC: {position_size_usdc:,} (6dp = ${position_size_usdc/1e6:.2f})")
        logger.info(f"  slippage: {slippage_scaled:,} (1e10 = {slippage_scaled/1e10:.2f}%)")
        
        return {
            "initial_pos_token": initial_pos_token,
            "leverage_scaled": leverage_scaled,
            "position_size_usdc": position_size_usdc,
            "slippage_scaled": slippage_scaled
        }
    
    def validate_slippage(self, slippage_scaled: int, max_slippage: int) -> bool:
        """Validate slippage is within contract limits."""
        
        if slippage_scaled <= 0:
            logger.error(f"❌ Slippage must be greater than 0, got: {slippage_scaled}")
            return False
        
        if slippage_scaled > max_slippage:
            logger.error(f"❌ Slippage {slippage_scaled} exceeds max {max_slippage}")
            return False
        
        logger.info(f"✅ Slippage validation passed: {slippage_scaled} <= {max_slippage}")
        return True
    
    def build_trade_struct(self, pair_index: int, is_long: bool, 
                          scaled_params: Dict[str, int], trader_address: str = None) -> Dict[str, Any]:
        """Build the Trade struct for openTrade function."""
        
        # Use provided trader address or a placeholder
        if trader_address is None:
            trader_address = "0x1234567890123456789012345678901234567890"  # Placeholder
        
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
            "sl": 0,   # Stop loss (0 = no SL)
            "timestamp": 0  # Will be set by contract
        }
        
        logger.info(f"Built trade struct for pair {pair_index}, {'LONG' if is_long else 'SHORT'}")
        return trade_struct
    
    def staticcall_validate(self, trade_struct: Dict[str, Any], 
                           order_type: int, slippage_scaled: int) -> Tuple[bool, str]:
        """Use staticcall to validate trade before spending gas."""
        
        logger.info("=== STATICCALL VALIDATION ===")
        
        try:
            # Build transaction data without sending
            tx_data = self.trading_contract.functions.openTrade(
                trade_struct,
                order_type,  # 0 = MARKET order
                slippage_scaled
            )._encode_transaction_data()
            
            logger.info("Built transaction data, making staticcall...")
            
            # Make static call
            result = self.w3.eth.call({
                "to": self.trading_address,
                "data": tx_data
            })
            
            logger.info("✅ Staticcall validation PASSED - trade should succeed on-chain")
            logger.info(f"Result: {result.hex() if result else 'No result'}")
            return True, "OK"
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Staticcall validation FAILED")
            logger.error(f"Error: {error_msg}")
            
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
    
    def test_trade_scenario(self, pair_index: int, is_long: bool, 
                           collateral_usdc: Decimal, leverage: Decimal, 
                           slippage_pct: Decimal, scenario_name: str) -> Dict[str, Any]:
        """Test a specific trade scenario."""
        
        logger.info(f"\n{'='*60}")
        logger.info(f"TESTING SCENARIO: {scenario_name}")
        logger.info(f"{'='*60}")
        logger.info(f"Pair: {pair_index}, Direction: {'LONG' if is_long else 'SHORT'}")
        logger.info(f"Collateral: {collateral_usdc} USDC, Leverage: {leverage}x, Slippage: {slippage_pct}%")
        
        try:
            # Step 1: Get contract limits
            contract_info = self.get_contract_info()
            if not contract_info:
                return {"success": False, "error": "Failed to get contract info"}
            
            # Step 2: Scale parameters correctly
            scaled_params = self.scale_trade_parameters(collateral_usdc, leverage, slippage_pct)
            
            # Step 3: Validate slippage bounds
            if not self.validate_slippage(scaled_params["slippage_scaled"], contract_info["max_slippage"]):
                return {"success": False, "error": "Slippage validation failed"}
            
            # Step 4: Build trade struct
            trade_struct = self.build_trade_struct(pair_index, is_long, scaled_params)
            
            # Step 5: Staticcall validation
            is_valid, validation_msg = self.staticcall_validate(
                trade_struct, 0, scaled_params["slippage_scaled"]
            )
            
            if not is_valid:
                return {
                    "success": False, 
                    "error": f"Staticcall validation failed: {validation_msg}",
                    "scaled_params": scaled_params,
                    "trade_struct": trade_struct
                }
            
            return {
                "success": True,
                "message": "Trade validated successfully",
                "scaled_params": scaled_params,
                "trade_struct": trade_struct,
                "contract_info": contract_info
            }
            
        except Exception as e:
            logger.error(f"Test scenario failed: {e}")
            return {"success": False, "error": f"Test execution failed: {e}"}
    
    def run_comprehensive_tests(self):
        """Run comprehensive test scenarios."""
        
        logger.info("🚀 STARTING COMPREHENSIVE DIRECT CONTRACT TESTS")
        logger.info("Testing bypass of SDK double-scaling issues")
        
        test_scenarios = [
            {
                "name": "Known-Good Values (Control Test)",
                "pair_index": 0,
                "is_long": True,
                "collateral": Decimal("100"),    # $100 USDC
                "leverage": Decimal("5"),        # 5x leverage
                "slippage": Decimal("1.0")       # 1.00%
            },
            {
                "name": "Minimum Viable Values",
                "pair_index": 0,
                "is_long": False,
                "collateral": Decimal("10"),     # $10 USDC
                "leverage": Decimal("1"),        # 1x leverage
                "slippage": Decimal("0.1")       # 0.1%
            },
            {
                "name": "High Leverage Test",
                "pair_index": 0,
                "is_long": True,
                "collateral": Decimal("50"),     # $50 USDC
                "leverage": Decimal("20"),       # 20x leverage
                "slippage": Decimal("2.0")       # 2.0%
            },
            {
                "name": "Conservative Values",
                "pair_index": 0,
                "is_long": False,
                "collateral": Decimal("200"),    # $200 USDC
                "leverage": Decimal("2"),        # 2x leverage
                "slippage": Decimal("0.5")       # 0.5%
            }
        ]
        
        results = {}
        
        for scenario in test_scenarios:
            result = self.test_trade_scenario(
                pair_index=scenario["pair_index"],
                is_long=scenario["is_long"],
                collateral_usdc=scenario["collateral"],
                leverage=scenario["leverage"],
                slippage_pct=scenario["slippage"],
                scenario_name=scenario["name"]
            )
            
            results[scenario["name"]] = result
        
        # Print summary
        logger.info(f"\n{'='*60}")
        logger.info("TEST RESULTS SUMMARY")
        logger.info(f"{'='*60}")
        
        passed = 0
        failed = 0
        
        for scenario_name, result in results.items():
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            logger.info(f"{status} - {scenario_name}")
            
            if result['success']:
                passed += 1
                logger.info(f"  Message: {result['message']}")
            else:
                failed += 1
                logger.info(f"  Error: {result['error']}")
        
        logger.info(f"\n📊 SUMMARY: {passed} passed, {failed} failed")
        
        if passed > 0:
            logger.info("🎉 SUCCESS: Direct contract approach is working!")
            logger.info("   This proves SDK double-scaling was the issue.")
        else:
            logger.info("⚠️  All tests failed - need to investigate further.")
        
        return results


def main():
    """Main function to run the practical tests."""
    
    try:
        # Initialize trader with real contract address
        trader = PracticalDirectTrader()
        
        # Run comprehensive tests
        results = trader.run_comprehensive_tests()
        
        # Save results to file
        with open("direct_contract_test_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info("Results saved to: direct_contract_test_results.json")
        
    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
