#!/usr/bin/env python3
"""
Avantis Proxy Diagnostics

This script identifies the current active trading proxy by checking:
- EIP-1967 proxy implementation slots
- Current implementation addresses
- Pause status on both old and new proxies
- Event history to determine which is active
"""

from web3 import Web3
from eth_abi import decode
import json
from datetime import datetime, timezone

RPC = "https://mainnet.base.org"
w3 = Web3(Web3.HTTPProvider(RPC))

CANDIDATES = [
    "0x5FF292d70bA9cD9e7CCb313782811b3D7120535f",  # Avantis: Trading Proxy (older)
    "0x44914408af82bC9983bbb330e3578E1105e11d4e",  # Active Avantis proxy
]

# EIP-1967 storage slots
IMPL_SLOT = Web3.keccak(text="eip1967.proxy.implementation")[:-1] + bytes([int.from_bytes(Web3.keccak(text="eip1967.proxy.implementation")[-1:], 'big') - 1])
ADMIN_SLOT = Web3.keccak(text="eip1967.proxy.admin")[:-1] + bytes([int.from_bytes(Web3.keccak(text="eip1967.proxy.admin")[-1:], 'big') - 1])

# Event topics
TOPIC_PAUSED   = w3.keccak(text="Paused(address)").hex()
TOPIC_UNPAUSED = w3.keccak(text="Unpaused(address)").hex()

def read_slot(addr, slot):
    raw = w3.eth.get_storage_at(addr, slot)
    return Web3.to_checksum_address(raw[-20:].hex())

def try_paused(addr, abi_json):
    c = w3.eth.contract(address=addr, abi=abi_json)
    try:
        return c.functions.paused().call()
    except:
        return None

def latest_event(addr, topic0):
    try:
        logs = w3.eth.get_logs({"address": addr, "fromBlock": 0, "toBlock": "latest", "topics":[topic0]})
        if not logs: return None
        last = logs[-1]
        ts = w3.eth.get_block(last["blockNumber"])["timestamp"]
        return {"block": last["blockNumber"], "time": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()}
    except Exception as e:
        return {"error": str(e)}

def check_abi_for_openTrade(abi_json):
    """Check if ABI contains openTrade function."""
    for item in abi_json:
        if item.get('type') == 'function' and item.get('name') == 'openTrade':
            return True, item
    return False, None

print("🔍 AVANTIS PROXY DIAGNOSTICS")
print("="*60)

for proxy in CANDIDATES:
    print(f"\n=== {proxy} ===")
    try:
        impl = read_slot(proxy, IMPL_SLOT)
        admin = read_slot(proxy, ADMIN_SLOT)
        print("Implementation:", impl)
        print("Admin:", admin)
    except Exception as e:
        print("Not an EIP-1967 proxy or unreadable slots:", e)
        impl = None

    # Try to get pause status using our existing ABI
    paused_state = None
    try:
        with open("config/abis/Trading.json") as f:
            TRADING_ABI = json.load(f)
        
        # Check if this ABI works with the proxy
        paused_state = try_paused(Web3.to_checksum_address(proxy), TRADING_ABI)
        
        # Check if ABI has openTrade function
        has_openTrade, openTrade_func = check_abi_for_openTrade(TRADING_ABI)
        print("Has openTrade function:", has_openTrade)
        if has_openTrade:
            print("openTrade signature:", openTrade_func.get('name', 'unknown'))
            inputs = [inp.get('name', 'unknown') for inp in openTrade_func.get('inputs', [])]
            print("openTrade inputs:", inputs)
        
    except FileNotFoundError:
        print("Trading.json ABI not found")
    except Exception as e:
        print(f"ABI test failed: {e}")
    
    print("paused():", paused_state)

    # Events history (proxy-level)
    p_evt = latest_event(Web3.to_checksum_address(proxy), TOPIC_PAUSED)
    u_evt = latest_event(Web3.to_checksum_address(proxy), TOPIC_UNPAUSED)
    print("Last Paused event:", p_evt)
    print("Last Unpaused event:", u_evt)

print(f"\n" + "="*60)
print("🎯 DIAGNOSTIC COMPLETE")
print("Look for:")
print("- Which proxy has paused(): False")
print("- Which proxy has recent Unpaused events")
print("- Which proxy has openTrade function")
print("- Which proxy has active implementation")
