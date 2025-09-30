#!/usr/bin/env python3
"""
Simple blockchain connection test
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Set environment variables
os.environ.update(
    {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "DATABASE_URL": "sqlite+aiosqlite:///test.db",
        "BASE_RPC_URL": "https://mainnet.base.org",
        "BASE_CHAIN_ID": "8453",
        "ENCRYPTION_KEY": "vkpZGJ3stdTs-i-gAM4sQGC7V5wi-pPkTDqyglD5x50=",
        "ADMIN_USER_IDS": "123456789",
        "COPY_EXECUTION_MODE": "LIVE",
        "PYTH_PRICE_SERVICE_URL": "https://hermes.pyth.network",
        "CHAINLINK_BASE_URL": "https://api.chain.link/v1",
    }
)


async def test_blockchain_connection():
    """Test basic blockchain connection"""
    print("🔗 Testing blockchain connection...")

    try:
        from src.blockchain.base_client import BaseClient

        base_client = BaseClient()
        print(f"✅ Base client connected to: {base_client.w3.eth.chain_id}")

        # Test wallet creation
        from src.blockchain.wallet_manager import WalletManager

        wallet_manager = WalletManager()

        # Create a test wallet
        wallet_data = wallet_manager.create_wallet(user_id="test_user")
        wallet_address = wallet_data["address"]
        wallet_data["private_key"]
        print(f"✅ Wallet created: {wallet_address}")

        # Check balance
        balance = base_client.w3.eth.get_balance(wallet_address)
        balance_eth = base_client.w3.from_wei(balance, "ether")
        print(f"✅ Wallet balance: {balance_eth} ETH")

        print("\n🎉 All basic tests passed!")
        print("✅ Blockchain connection working")
        print("✅ Wallet creation working")
        print("✅ Balance checking working")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_blockchain_connection())
    if success:
        print("\n🚀 Ready for real trading!")
    else:
        print("\n💥 Blockchain test failed")
        sys.exit(1)
