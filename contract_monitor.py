#!/usr/bin/env python3
"""
Avantis Contract Monitor

This script monitors the Avantis trading contract to detect when it becomes
unpaused and ready for trading. It also validates that our parameter scaling
approach will work once the contract is active.
"""

import json
import time
from datetime import datetime
from decimal import Decimal
from web3 import Web3
from typing import Dict, Any, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AvantisContractMonitor:
    """Monitor Avantis contract status and validate trading parameters."""
    
    def __init__(self):
        """Initialize monitor with contract details."""
        
        self.rpc_url = "https://mainnet.base.org"
        self.trading_contract = "0x5FF292d70bA9cD9e7CCb313782811b3D7120535f"
        
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to Base network")
        
        # Load ABI
        with open("config/abis/Trading.json") as f:
            data = json.load(f)
        self.trading_abi = data["abi"]
        
        # Initialize contract
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.trading_contract),
            abi=self.trading_abi
        )
        
        # Scaling constants
        self.USDC_6 = Decimal(10) ** 6
        self.SCALE_1E10 = Decimal(10) ** 10
        
        logger.info(f"🔍 CONTRACT MONITOR INITIALIZED")
        logger.info(f"   Contract: {self.trading_contract}")
        logger.info(f"   Network: Base Mainnet")
    
    def get_contract_status(self) -> Dict[str, Any]:
        """Get current contract status."""
        try:
            # Check if contract is paused
            paused = self.contract.functions.paused().call()
            
            # Get operator
            operator = self.contract.functions.operator().call()
            
            # Try to get max slippage
            max_slippage = None
            try:
                max_slippage = self.contract.functions._MAX_SLIPPAGE().call()
            except:
                pass
            
            # Get pair infos contract
            pair_infos = self.contract.functions.pairInfos().call()
            
            # Get current block info
            latest_block = self.w3.eth.get_block('latest')
            
            return {
                "paused": paused,
                "operator": operator,
                "max_slippage": max_slippage,
                "pair_infos": pair_infos,
                "block_number": latest_block.number,
                "block_timestamp": latest_block.timestamp,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get contract status: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def validate_trading_parameters(self) -> Dict[str, Any]:
        """Validate that our trading parameters will work once contract is active."""
        
        logger.info(f"🧪 VALIDATING TRADING PARAMETERS")
        
        # Test parameters
        test_params = {
            "collateral_usdc": Decimal("10"),
            "leverage": Decimal("2"),
            "slippage_pct": Decimal("1.0")
        }
        
        # Scale parameters correctly
        initial_pos_token = int(test_params["collateral_usdc"] * self.USDC_6)
        leverage_scaled = int(test_params["leverage"] * self.SCALE_1E10)
        position_size_usdc = (initial_pos_token * leverage_scaled) // int(self.SCALE_1E10)
        slippage_scaled = int((test_params["slippage_pct"] / Decimal(100)) * self.SCALE_1E10)
        
        logger.info(f"   Test Parameters:")
        logger.info(f"     Collateral: {test_params['collateral_usdc']} USDC")
        logger.info(f"     Leverage: {test_params['leverage']}x")
        logger.info(f"     Slippage: {test_params['slippage_pct']}%")
        
        logger.info(f"   Scaled Parameters:")
        logger.info(f"     initialPosToken: {initial_pos_token:,}")
        logger.info(f"     leverage: {leverage_scaled:,}")
        logger.info(f"     positionSizeUSDC: {position_size_usdc:,}")
        logger.info(f"     slippage: {slippage_scaled:,}")
        
        # Build trade struct
        trade_struct = {
            "trader": "0xdCDca231d02F1a8B85B701Ce90fc32c48a673982",
            "pairIndex": 0,
            "index": 0,
            "initialPosToken": initial_pos_token,
            "positionSizeUSDC": position_size_usdc,
            "openPrice": 0,
            "buy": True,
            "leverage": leverage_scaled,
            "tp": 0,
            "sl": 0,
            "timestamp": 0
        }
        
        return {
            "test_params": test_params,
            "scaled_params": {
                "initial_pos_token": initial_pos_token,
                "leverage_scaled": leverage_scaled,
                "position_size_usdc": position_size_usdc,
                "slippage_scaled": slippage_scaled
            },
            "trade_struct": trade_struct,
            "ready_for_trading": True
        }
    
    def test_staticcall(self) -> Tuple[bool, str]:
        """Test staticcall to validate our parameters work."""
        
        logger.info(f"🔍 TESTING STATICCALL VALIDATION")
        
        try:
            # Get validation data
            validation_data = self.validate_trading_parameters()
            trade_struct = validation_data["trade_struct"]
            slippage_scaled = validation_data["scaled_params"]["slippage_scaled"]
            
            # Build transaction data
            tx_data = self.contract.functions.openTrade(
                trade_struct,
                0,  # MARKET order
                slippage_scaled
            )._encode_transaction_data()
            
            # Make static call
            result = self.w3.eth.call({
                "to": self.trading_contract,
                "data": tx_data
            })
            
            logger.info(f"   ✅ Staticcall validation PASSED")
            return True, "Parameters are valid"
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"   ❌ Staticcall validation FAILED: {error_msg}")
            return False, error_msg
    
    def monitor_contract(self, check_interval: int = 60):
        """Monitor contract status and alert when it becomes available."""
        
        logger.info(f"🔄 STARTING CONTRACT MONITOR")
        logger.info(f"   Check interval: {check_interval} seconds")
        logger.info(f"   Press Ctrl+C to stop")
        
        try:
            while True:
                # Get current status
                status = self.get_contract_status()
                
                if "error" in status:
                    logger.error(f"❌ Error getting status: {status['error']}")
                    time.sleep(check_interval)
                    continue
                
                # Log status
                paused_status = "PAUSED" if status["paused"] else "ACTIVE"
                logger.info(f"📊 Contract Status: {paused_status}")
                
                if status["max_slippage"]:
                    max_slippage_pct = status["max_slippage"] / 1e10 * 100
                    logger.info(f"   Max Slippage: {status['max_slippage']:,} (1e10 scale = {max_slippage_pct:.2f}%)")
                
                logger.info(f"   Operator: {status['operator']}")
                logger.info(f"   Block: {status['block_number']}")
                logger.info(f"   Time: {status['timestamp']}")
                
                # Check if contract is unpaused
                if not status["paused"]:
                    logger.info(f"🎉 CONTRACT IS NOW ACTIVE!")
                    logger.info(f"   Ready for trading!")
                    
                    # Test our parameters
                    is_valid, validation_msg = self.test_staticcall()
                    
                    if is_valid:
                        logger.info(f"✅ OUR PARAMETERS ARE VALID!")
                        logger.info(f"   Ready to execute trades with our scaling approach")
                        
                        # Save ready status
                        ready_data = {
                            "contract_active": True,
                            "parameters_valid": True,
                            "validation_message": validation_msg,
                            "status": status,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        with open("contract_ready.json", "w") as f:
                            json.dump(ready_data, f, indent=2, default=str)
                        
                        logger.info(f"   Ready status saved to: contract_ready.json")
                        logger.info(f"   You can now run: python3 live_trading_execution.py")
                        
                    else:
                        logger.warning(f"⚠️  Contract active but parameters invalid: {validation_msg}")
                else:
                    logger.info(f"⏳ Contract still paused, checking again in {check_interval} seconds...")
                
                # Wait before next check
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            logger.info(f"🛑 Monitor stopped by user")
        except Exception as e:
            logger.error(f"❌ Monitor error: {e}")


def main():
    """Main function to run the contract monitor."""
    
    try:
        # Initialize monitor
        monitor = AvantisContractMonitor()
        
        # Get initial status
        logger.info(f"📊 INITIAL CONTRACT STATUS")
        status = monitor.get_contract_status()
        
        if "error" not in status:
            paused_status = "PAUSED" if status["paused"] else "ACTIVE"
            logger.info(f"   Status: {paused_status}")
            logger.info(f"   Operator: {status['operator']}")
            
            if status["max_slippage"]:
                max_slippage_pct = status["max_slippage"] / 1e10 * 100
                logger.info(f"   Max Slippage: {status['max_slippage']:,} ({max_slippage_pct:.2f}%)")
        
        # Validate our parameters
        logger.info(f"\n🔧 PARAMETER VALIDATION")
        validation_data = monitor.validate_trading_parameters()
        
        # Test staticcall
        is_valid, validation_msg = monitor.test_staticcall()
        
        if is_valid:
            logger.info(f"✅ Our parameter scaling approach is VALID!")
            logger.info(f"   Ready to trade once contract is unpaused")
        else:
            logger.warning(f"⚠️  Parameter validation failed: {validation_msg}")
        
        # Start monitoring
        logger.info(f"\n🔄 Starting continuous monitoring...")
        monitor.monitor_contract(check_interval=60)
        
    except Exception as e:
        logger.error(f"❌ Monitor execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
