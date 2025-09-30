#!/usr/bin/env python3
"""
Test script for Avantis Vault Resolver
Verifies that the vault contract can be resolved from the Trading Proxy
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from web3 import Web3

from src.services.contracts.avantis_registry import (
    initialize_registry,
    resolve_avantis_vault,
)


async def test_vault_resolver():
    """Test the vault resolver functionality"""

    # Configuration
    TRADING_CONTRACT = "0x5FF292d70bA9cD9e7CCb313782811b3D7120535f"
    BASE_RPC_URL = "https://mainnet.base.org"

    print("🔍 Testing Avantis Vault Resolver")
    print(f"Trading Contract: {TRADING_CONTRACT}")
    print(f"RPC URL: {BASE_RPC_URL}")
    print()

    try:
        # Initialize Web3 connection
        print("📡 Connecting to Base network...")
        w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))

        if not w3.is_connected():
            print("❌ Failed to connect to Base RPC")
            return False

        print(f"✅ Connected to Base (Chain ID: {w3.eth.chain_id})")

        # Initialize registry
        print("🔧 Initializing contract registry...")
        registry = initialize_registry(w3, TRADING_CONTRACT)

        # Resolve vault address
        print("🔍 Resolving vault address...")
        vault_address = await resolve_avantis_vault()

        print(f"✅ Vault address resolved: {vault_address}")

        # Get contract info
        print("\n📋 Contract Information:")
        contract_info = await registry.get_contract_info()

        for key, value in contract_info.items():
            print(f"  {key}: {value}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_vault_resolver())
    sys.exit(0 if success else 1)
