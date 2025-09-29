#!/usr/bin/env python3
"""
Clean Avantis Proxy Check

This script checks both proxy addresses to determine which is the current active one.
"""

from web3 import Web3
import json
from datetime import datetime, timezone

RPC = "https://mainnet.base.org"
w3 = Web3(Web3.HTTPProvider(RPC))

CANDIDATES = [
    "0x5FF292d70bA9cD9e7CCb313782811b3D7120535f",  # Old Avantis Trading Proxy
    "0x44914408af82bC9983bbb330e3578E1105e11d4e",  # Active Avantis proxy
]

# EIP-1967 storage slots
IMPL_SLOT = Web3.keccak(text="eip1967.proxy.implementation")[:-1] + bytes([int.from_bytes(Web3.keccak(text="eip1967.proxy.implementation")[-1:], 'big') - 1])

def read_slot(addr, slot):
    try:
        raw = w3.eth.get_storage_at(addr, slot)
        return Web3.to_checksum_address(raw[-20:].hex())
    except:
        return None

def check_paused_with_abi(addr, abi_json):
    try:
        c = w3.eth.contract(address=addr, abi=abi_json)
        return c.functions.paused().call()
    except:
        return None

def check_has_openTrade(abi_json):
    for item in abi_json:
        if item.get('type') == 'function' and item.get('name') == 'openTrade':
            return True, item.get('inputs', [])
    return False, []

print("🔍 AVANTIS PROXY ANALYSIS")
print("="*50)

# Load our existing ABI
try:
    with open("config/abis/Trading.json") as f:
        TRADING_ABI = json.load(f)
    has_openTrade, openTrade_inputs = check_has_openTrade(TRADING_ABI)
    print(f"✅ Loaded Trading ABI with openTrade function: {has_openTrade}")
    if has_openTrade:
        print(f"   openTrade inputs: {[inp.get('name', 'unknown') for inp in openTrade_inputs]}")
except Exception as e:
    print(f"❌ Failed to load ABI: {e}")
    TRADING_ABI = None

print()

for i, proxy in enumerate(CANDIDATES, 1):
    print(f"=== PROXY {i}: {proxy} ===")
    
    # Check if it's a proxy
    impl = read_slot(proxy, IMPL_SLOT)
    if impl:
        print(f"✅ EIP-1967 Proxy - Implementation: {impl}")
    else:
        print(f"❌ Not an EIP-1967 proxy or unreadable")
        continue
    
    # Check pause status
    if TRADING_ABI:
        paused = check_paused_with_abi(proxy, TRADING_ABI)
        if paused is not None:
            status = "PAUSED" if paused else "ACTIVE"
            print(f"📊 Status: {status}")
        else:
            print(f"❓ Cannot determine pause status")
    else:
        print(f"❓ No ABI available for pause check")
    
    # Get recent transaction count (activity indicator)
    try:
        latest_block = w3.eth.block_number
        # Check last 1000 blocks for transactions to this address
        tx_count = 0
        for block_num in range(max(0, latest_block - 1000), latest_block):
            try:
                block = w3.eth.get_block(block_num, full_transactions=True)
                for tx in block.transactions:
                    if tx.to and tx.to.lower() == proxy.lower():
                        tx_count += 1
            except:
                continue
        
        print(f"📈 Recent activity (last 1000 blocks): {tx_count} transactions")
    except Exception as e:
        print(f"❓ Cannot check activity: {e}")
    
    print()

print("🎯 ANALYSIS SUMMARY:")
print("- Look for the proxy that is ACTIVE (not paused)")
print("- Look for the proxy with recent transaction activity")
print("- Both should have the same implementation ABI with openTrade function")
print()
print("💡 NEXT STEPS:")
print("1. If one proxy is ACTIVE and the other is PAUSED → use the ACTIVE one")
print("2. If both are paused → wait for one to be unpaused")
print("3. Update bulletproof_trading_solution.py with the correct proxy address")
