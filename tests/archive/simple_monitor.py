#!/usr/bin/env python3
"""
Simple Avantis Contract Monitor

A lightweight monitor that checks contract status every 30 seconds
and alerts when the contract becomes unpaused.
"""

import json
import time
from web3 import Web3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_contract_status():
    """Check if contract is paused."""
    try:
        w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))
        with open("config/abis/Trading.json") as f:
            data = json.load(f)
        
        contract = w3.eth.contract(
            address="0x5FF292d70bA9cD9e7CCb313782811b3D7120535f",
            abi=data["abi"]
        )
        
        paused = contract.functions.paused().call()
        return paused
    except Exception as e:
        logger.error(f"Error checking status: {e}")
        return True

def main():
    """Main monitoring loop."""
    logger.info("🔍 Starting Avantis Contract Monitor")
    logger.info("   Checking every 30 seconds")
    logger.info("   Press Ctrl+C to stop")
    
    try:
        while True:
            paused = check_contract_status()
            
            if paused:
                logger.info("⏳ Contract is PAUSED")
            else:
                logger.info("🎉 CONTRACT IS UNPAUSED - READY FOR TRADING!")
                logger.info("   Run: python3 bulletproof_trading_solution.py")
                break
            
            time.sleep(30)
            
    except KeyboardInterrupt:
        logger.info("🛑 Monitor stopped by user")

if __name__ == "__main__":
    main()
