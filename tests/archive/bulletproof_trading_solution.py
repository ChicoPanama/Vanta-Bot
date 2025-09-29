#!/usr/bin/env python3
"""
Bulletproof Avantis Trading Solution

This script implements the complete solution for reliable Avantis trading:
1. Proxy-aware pause checking with implementation ABI
2. Unpaused event watcher with auto-testing
3. Manual scaling bypass (no SDK double-scaling)
4. On-chain limits validation
5. Production-ready transaction builder

Ready to execute trades the moment the contract unpauses.
"""

import json
import time
from decimal import Decimal
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from typing import Dict, Any, Tuple, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BulletproofAvantisTrader:
    """Bulletproof Avantis trader with complete solution."""
    
    def __init__(self):
        """Initialize with all required components."""
        
        # Configuration
        self.RPC = "https://mainnet.base.org"
        self.TRADING_PROXY = "0x44914408af82bC9983bbb330e3578E1105e11d4e"  # Active proxy
        self.WALLET_ADDRESS = "0xdCDca231d02F1a8B85B701Ce90fc32c48a673982"
        self.PRIVATE_KEY = "aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87"
        
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(self.RPC))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to Base network")
        
        # Load Trading ABI (implementation ABI at proxy address)
        with open("config/abis/Trading.json") as f:
            data = json.load(f)
        self.TRADING_ABI = data["abi"]
        
        # Initialize contracts
        self.trading_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.TRADING_PROXY),
            abi=self.TRADING_ABI
        )
        
        # Initialize account
        self.account = Account.from_key(self.PRIVATE_KEY)
        
        # Scaling constants
        self.USDC_6 = Decimal(10) ** 6
        self.SCALE_1E10 = Decimal(10) ** 10
        
        # Event signatures
        self.UNPAUSED_SIG = self.w3.keccak(text="Unpaused(address)").hex()
        
        logger.info(f"🚀 BULLETPROOF TRADER INITIALIZED")
        logger.info(f"   Trading Proxy: {self.TRADING_PROXY}")
        logger.info(f"   Wallet: {self.WALLET_ADDRESS}")
        logger.info(f"   Network: Base Mainnet")
    
    def check_pause_status(self) -> Tuple[bool, Dict[str, Any]]:
        """Check pause status using proxy with implementation ABI."""
        
        logger.info(f"🔍 CHECKING PAUSE STATUS")
        
        try:
            # Call paused() on proxy with implementation ABI
            paused = self.trading_contract.functions.paused().call()
            
            # Get additional contract info
            operator = self.trading_contract.functions.operator().call()
            
            # Try to get max slippage (might fail if paused)
            max_slippage = None
            try:
                max_slippage = self.trading_contract.functions._MAX_SLIPPAGE().call()
            except:
                logger.warning("Could not get max slippage (contract might be paused)")
            
            # Get pair infos
            pair_infos = self.trading_contract.functions.pairInfos().call()
            
            status = {
                "paused": paused,
                "operator": operator,
                "max_slippage": max_slippage,
                "pair_infos": pair_infos,
                "timestamp": time.time()
            }
            
            paused_status = "PAUSED" if paused else "ACTIVE"
            logger.info(f"   Status: {paused_status}")
            logger.info(f"   Operator: {operator}")
            if max_slippage:
                max_slippage_pct = max_slippage / 1e10 * 100
                logger.info(f"   Max Slippage: {max_slippage:,} ({max_slippage_pct:.2f}%)")
            logger.info(f"   PairInfos: {pair_infos}")
            
            return paused, status
            
        except Exception as e:
            logger.error(f"❌ Failed to check pause status: {e}")
            return True, {"error": str(e)}
    
    def manual_scale_parameters(self, collateral_usdc: Decimal, leverage: Decimal, 
                              slippage_pct: Decimal) -> Dict[str, int]:
        """Manual scaling (bypass SDK auto-scaling)."""
        
        logger.info(f"🔧 MANUAL PARAMETER SCALING")
        logger.info(f"   Input: ${collateral_usdc} USDC, {leverage}x leverage, {slippage_pct}% slippage")
        
        # Manual scale (once only)
        initial_pos_token = int(collateral_usdc * self.USDC_6)
        leverage_scaled = int(leverage * self.SCALE_1E10)
        position_size_usdc = (initial_pos_token * leverage_scaled) // int(self.SCALE_1E10)
        slippage_scaled = int((slippage_pct / Decimal(100)) * self.SCALE_1E10)
        
        logger.info(f"   Scaled Results:")
        logger.info(f"     initialPosToken: {initial_pos_token:,} (6dp)")
        logger.info(f"     leverage: {leverage_scaled:,} (1e10)")
        logger.info(f"     positionSizeUSDC: {position_size_usdc:,} (6dp = ${position_size_usdc/1e6:.2f})")
        logger.info(f"     slippage: {slippage_scaled:,} (1e10 = {slippage_scaled/1e10:.2f}%)")
        
        return {
            "initial_pos_token": initial_pos_token,
            "leverage_scaled": leverage_scaled,
            "position_size_usdc": position_size_usdc,
            "slippage_scaled": slippage_scaled
        }
    
    def build_trade_struct(self, pair_index: int, is_long: bool, 
                          scaled_params: Dict[str, int]) -> Dict[str, Any]:
        """Build trade struct with exact field mapping."""
        
        trade_struct = {
            "trader": self.WALLET_ADDRESS,
            "pairIndex": pair_index,
            "index": 0,  # Will be set by contract
            "initialPosToken": scaled_params["initial_pos_token"],
            "positionSizeUSDC": scaled_params["position_size_usdc"],
            "openPrice": 0,  # Market order (must be 0)
            "buy": is_long,
            "leverage": scaled_params["leverage_scaled"],
            "tp": 0,  # No take profit
            "sl": 0,   # No stop loss
            "timestamp": 0  # Will be set by contract
        }
        
        logger.info(f"📝 Built trade struct:")
        for key, value in trade_struct.items():
            if isinstance(value, bool):
                logger.info(f"   {key}: {value}")
            elif isinstance(value, str):
                logger.info(f"   {key}: {value}")
            else:
                logger.info(f"   {key}: {value:,}")
        
        return trade_struct
    
    def validate_on_chain_limits(self, scaled_params: Dict[str, int], 
                                pair_index: int = 0) -> Tuple[bool, str]:
        """Validate against on-chain limits."""
        
        logger.info(f"🔍 VALIDATING ON-CHAIN LIMITS")
        
        try:
            # Try to get limits from contract
            # Note: These might fail if contract is paused, that's OK
            limits = {}
            
            try:
                limits["max_slippage"] = self.trading_contract.functions._MAX_SLIPPAGE().call()
                logger.info(f"   Max Slippage: {limits['max_slippage']:,}")
            except:
                logger.warning("   Could not get max slippage limit")
                limits["max_slippage"] = 500_000_000  # Conservative fallback (5%)
            
            # Basic validation
            if scaled_params["slippage_scaled"] <= 0:
                return False, "Slippage must be greater than 0"
            
            if scaled_params["slippage_scaled"] > limits["max_slippage"]:
                return False, f"Slippage {scaled_params['slippage_scaled']} exceeds max {limits['max_slippage']}"
            
            if scaled_params["position_size_usdc"] <= 0:
                return False, "Position size must be greater than 0"
            
            logger.info(f"   ✅ All limits validated successfully")
            return True, "OK"
            
        except Exception as e:
            logger.error(f"   ❌ Limit validation failed: {e}")
            return False, f"Validation error: {e}"
    
    def staticcall_validation(self, trade_struct: Dict[str, Any], 
                             order_type: int, slippage_scaled: int) -> Tuple[bool, str]:
        """Staticcall validation to see exact revert reason."""
        
        logger.info(f"🔍 STATICCALL VALIDATION")
        
        try:
            # Build transaction data
            data = self.trading_contract.functions.openTrade(
                trade_struct,
                order_type,  # MARKET order
                slippage_scaled
            )._encode_transaction_data()
            
            logger.info("   Built transaction data, making staticcall...")
            
            # Make static call
            result = self.w3.eth.call({
                "to": self.TRADING_PROXY,
                "data": data
            })
            
            logger.info("   ✅ Staticcall validation PASSED")
            logger.info(f"   Result: {result.hex() if result else 'No result'}")
            return True, "OK"
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"   ❌ Staticcall validation FAILED")
            logger.error(f"   Error: {error_msg}")
            
            # Decode custom errors
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
    
    def watch_unpaused_event(self, start_block: Optional[int] = None) -> bool:
        """Watch for Unpaused event and return when detected."""
        
        logger.info(f"👀 WATCHING FOR UNPAUSED EVENT")
        
        last_block = start_block or self.w3.eth.block_number
        logger.info(f"   Watching from block: {last_block}")
        
        while True:
            try:
                latest = self.w3.eth.block_number
                if latest > last_block:
                    # Get logs for Unpaused event
                    logs = self.w3.eth.get_logs({
                        "fromBlock": last_block + 1,
                        "toBlock": latest,
                        "address": self.TRADING_PROXY,
                        "topics": [self.UNPAUSED_SIG]
                    })
                    
                    if logs:
                        unpaused_block = logs[0]["blockNumber"]
                        logger.info(f"🔔 UNPAUSED EVENT DETECTED at block {unpaused_block}")
                        return True
                    
                    last_block = latest
                
                time.sleep(2)  # Check every 2 seconds
                
            except KeyboardInterrupt:
                logger.info("🛑 Event watching stopped by user")
                return False
            except Exception as e:
                logger.error(f"❌ Error watching events: {e}")
                time.sleep(5)  # Wait longer on error
    
    def execute_trade(self, pair_index: int, is_long: bool, 
                     collateral_usdc: Decimal, leverage: Decimal, 
                     slippage_pct: Decimal) -> Dict[str, Any]:
        """Execute trade with complete validation and error handling."""
        
        logger.info(f"🎯 EXECUTING TRADE")
        logger.info(f"   Pair: {pair_index}, Direction: {'LONG' if is_long else 'SHORT'}")
        logger.info(f"   Collateral: {collateral_usdc} USDC, Leverage: {leverage}x, Slippage: {slippage_pct}%")
        
        try:
            # Step 1: Check pause status
            paused, status = self.check_pause_status()
            if paused:
                logger.error("❌ Contract is paused - cannot execute trades")
                return {"success": False, "error": "Contract is paused"}
            
            # Step 2: Manual scaling
            scaled_params = self.manual_scale_parameters(collateral_usdc, leverage, slippage_pct)
            
            # Step 3: Build trade struct
            trade_struct = self.build_trade_struct(pair_index, is_long, scaled_params)
            
            # Step 4: Validate on-chain limits
            is_valid, validation_msg = self.validate_on_chain_limits(scaled_params, pair_index)
            if not is_valid:
                return {"success": False, "error": f"Limit validation failed: {validation_msg}"}
            
            # Step 5: Staticcall validation
            is_valid, validation_msg = self.staticcall_validation(
                trade_struct, 0, scaled_params["slippage_scaled"]
            )
            if not is_valid:
                return {"success": False, "error": f"Staticcall validation failed: {validation_msg}"}
            
            # Step 6: Execute transaction
            logger.info(f"🚀 EXECUTING LIVE TRANSACTION")
            
            # Get nonce
            nonce = self.w3.eth.get_transaction_count(self.WALLET_ADDRESS)
            
            # Build transaction
            transaction = self.trading_contract.functions.openTrade(
                trade_struct,
                0,  # MARKET order
                scaled_params["slippage_scaled"]
            ).build_transaction({
                "from": self.WALLET_ADDRESS,
                "nonce": nonce,
                "type": 2,  # EIP-1559
                "maxFeePerGas": self.w3.to_wei("0.5", "gwei"),
                "maxPriorityFeePerGas": self.w3.to_wei("0.05", "gwei"),
                "gas": 500000,  # Generous gas limit
            })
            
            # Sign transaction
            signed_txn = self.account.sign_transaction(transaction)
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            logger.info(f"✅ TRANSACTION SUBMITTED")
            logger.info(f"   Transaction Hash: {tx_hash.hex()}")
            logger.info(f"   BaseScan URL: https://basescan.org/tx/{tx_hash.hex()}")
            
            # Wait for confirmation
            logger.info(f"⏳ Waiting for confirmation...")
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt.status == 1:
                logger.info(f"🎉 TRADE EXECUTED SUCCESSFULLY!")
                logger.info(f"   Block Number: {receipt.blockNumber}")
                logger.info(f"   Gas Used: {receipt.gasUsed:,}")
                
                return {
                    "success": True,
                    "transaction_hash": tx_hash.hex(),
                    "block_number": receipt.blockNumber,
                    "gas_used": receipt.gasUsed,
                    "basescan_url": f"https://basescan.org/tx/{tx_hash.hex()}",
                    "scaled_params": scaled_params,
                    "trade_struct": trade_struct
                }
            else:
                logger.error(f"❌ Transaction failed")
                return {"success": False, "error": "Transaction reverted"}
                
        except Exception as e:
            logger.error(f"❌ Trade execution failed: {e}")
            return {"success": False, "error": f"Execution failed: {e}"}
    
    def run_bulletproof_test(self):
        """Run bulletproof test with conservative parameters."""
        
        logger.info(f"🧪 RUNNING BULLETPROOF TEST")
        logger.info(f"="*60)
        
        # Conservative test parameters
        test_params = {
            "pair_index": 0,
            "is_long": True,
            "collateral_usdc": Decimal("10"),    # $10 USDC (conservative)
            "leverage": Decimal("2"),            # 2x leverage (conservative)
            "slippage_pct": Decimal("1.0")       # 1% slippage
        }
        
        logger.info(f"Test Parameters:")
        for key, value in test_params.items():
            logger.info(f"   {key}: {value}")
        
        # Execute the test trade
        result = self.execute_trade(**test_params)
        
        # Print results
        if result["success"]:
            logger.info(f"\n🎉 BULLETPROOF TEST SUCCESS!")
            logger.info(f"   Transaction: {result['transaction_hash']}")
            logger.info(f"   BaseScan: {result['basescan_url']}")
            logger.info(f"   Block: {result['block_number']}")
            logger.info(f"   Gas Used: {result['gas_used']:,}")
            
            # Save results
            with open("bulletproof_trade_results.json", "w") as f:
                json.dump(result, f, indent=2, default=str)
            
            logger.info(f"   Results saved to: bulletproof_trade_results.json")
            
        else:
            logger.error(f"\n❌ BULLETPROOF TEST FAILED")
            logger.error(f"   Error: {result['error']}")
            
            # Save error details
            with open("bulletproof_trade_error.json", "w") as f:
                json.dump(result, f, indent=2, default=str)
            
            logger.info(f"   Error details saved to: bulletproof_trade_error.json")
        
        return result


def main():
    """Main function to run bulletproof trading solution."""
    
    try:
        logger.info("🚀 STARTING BULLETPROOF AVANTIS TRADING SOLUTION")
        
        # Initialize trader
        trader = BulletproofAvantisTrader()
        
        # Check current status
        paused, status = trader.check_pause_status()
        
        if not paused:
            logger.info("🎉 CONTRACT IS ACTIVE - RUNNING TRADE TEST")
            result = trader.run_bulletproof_test()
            
            if result["success"]:
                logger.info(f"\n" + "="*60)
                logger.info(f"🎉 MISSION ACCOMPLISHED!")
                logger.info(f"   Bot is PRODUCTION READY")
                logger.info(f"   Transaction: {result['transaction_hash']}")
                logger.info(f"   BaseScan: {result['basescan_url']}")
                logger.info(f"="*60)
            else:
                logger.info(f"\n" + "="*60)
                logger.info(f"⚠️  MISSION CONTINUES")
                logger.info(f"   Error: {result['error']}")
                logger.info(f"   Need to investigate further")
                logger.info(f"="*60)
        
        else:
            logger.info("⏳ CONTRACT IS PAUSED - STARTING EVENT WATCHER")
            logger.info("   Will automatically execute trade when contract unpauses")
            
            # Watch for unpaused event
            if trader.watch_unpaused_event():
                logger.info("🎉 CONTRACT UNPAUSED - EXECUTING TRADE")
                result = trader.run_bulletproof_test()
                
                if result["success"]:
                    logger.info(f"\n" + "="*60)
                    logger.info(f"🎉 MISSION ACCOMPLISHED!")
                    logger.info(f"   Bot is PRODUCTION READY")
                    logger.info(f"   Transaction: {result['transaction_hash']}")
                    logger.info(f"   BaseScan: {result['basescan_url']}")
                    logger.info(f"="*60)
                else:
                    logger.error(f"❌ Trade failed after unpause: {result['error']}")
        
    except KeyboardInterrupt:
        logger.info("🛑 Execution stopped by user")
    except Exception as e:
        logger.error(f"❌ Main execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
