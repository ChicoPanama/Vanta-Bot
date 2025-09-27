# src/services/indexers/abi_inspector.py
from __future__ import annotations
import json, os
from typing import Dict, List, Any
from web3 import Web3
from web3.providers.rpc import HTTPProvider

ABI_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "config", "abis")
TRADING_ABI_PATH = os.path.join(ABI_DIR, "Trading.json")

def inspect_trading_events() -> Dict[str, List[str]]:
    """Inspect Trading.json ABI and extract event names and field names"""
    try:
        with open(TRADING_ABI_PATH, "r") as f:
            abi = json.load(f)
    except FileNotFoundError:
        print(f"❌ ABI file not found: {TRADING_ABI_PATH}")
        return {}
    
    events = {}
    for item in abi:
        if item.get("type") == "event":
            name = item.get("name")
            fields = [inp["name"] for inp in item.get("inputs", [])]
            events[name] = fields
    
    return events

def print_event_field_mapping():
    """Print a mapping guide for event field names"""
    events = inspect_trading_events()
    
    print("🔍 **Avantis Trading Contract Event Field Mapping**\n")
    print("Use these field names in your `_consume_event` method:\n")
    
    for event_name, fields in events.items():
        print(f"📊 **{event_name}**:")
        print(f"   Fields: {fields}")
        
        # Suggest mapping for common fields
        mapping_suggestions = []
        for field in fields:
            if field.lower() in ['trader', 'user', 'account', 'owner']:
                mapping_suggestions.append(f"address = args.get('{field}')")
            elif field.lower() in ['pair', 'symbol', 'asset']:
                mapping_suggestions.append(f"pair = args.get('{field}')")
            elif field.lower() in ['islong', 'direction']:
                mapping_suggestions.append(f"is_long = args.get('{field}')")
            elif field.lower() in ['size', 'positionsize', 'amount']:
                mapping_suggestions.append(f"size = args.get('{field}')")
            elif field.lower() in ['executionprice', 'entryprice', 'price']:
                mapping_suggestions.append(f"price = args.get('{field}')")
            elif field.lower() in ['fee', 'fees']:
                mapping_suggestions.append(f"fee = args.get('{field}')")
        
        if mapping_suggestions:
            print(f"   Suggested mapping:")
            for suggestion in mapping_suggestions[:3]:  # Show first 3
                print(f"     {suggestion}")
        print()

if __name__ == "__main__":
    print_event_field_mapping()
