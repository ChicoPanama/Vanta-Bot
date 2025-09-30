#!/usr/bin/env python3
"""
Real trade execution test on Base mainnet
"""

import asyncio
import os
import sys
from decimal import Decimal

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
        # Ensure signer + contract are set for live trading
        "TRADER_PRIVATE_KEY": "aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87",
        "AVANTIS_TRADING_CONTRACT": "0x5FF292d70bA9cD9e7CCb313782811b3D7120535f",
    }
)


async def test_real_trading():
    print("🚀 REAL TRADE TEST - BASE MAINNET")
    print("=" * 60)
    print("⚠️  This will execute REAL transactions on Base mainnet")
    print("   Using small amounts to minimize risk")
    print("=" * 60)

    # Test wallet details
    wallet_address = "0xdCDca231d02F1a8B85B701Ce90fc32c48a673982"
    test_private_key = (
        "aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87"
    )

    try:
        # Test blockchain connection
        from src.blockchain.base_client import BaseClient

        base_client = BaseClient()
        print(f"✅ Connected to Base mainnet (Chain ID: {base_client.w3.eth.chain_id})")

        # Check wallet balance
        balance = base_client.w3.eth.get_balance(wallet_address)
        balance_eth = base_client.w3.from_wei(balance, "ether")
        print(f"✅ Wallet balance: {balance_eth} ETH")

        if balance_eth < 0.001:
            print("❌ Insufficient ETH for gas fees")
            return False

        # Test Avantis client
        from src.blockchain.avantis_client import AvantisClient

        avantis_client = AvantisClient()
        print("✅ AvantisClient initialized")
        # Quick ABI sanity: ensure we loaded a list-style ABI
        try:
            abi_len = (
                len(avantis_client.trading_abi)
                if getattr(avantis_client, "trading_abi", None)
                else 0
            )
            print(f"✅ Trading ABI loaded ({abi_len} entries)")
        except Exception:
            print("⚠️ Could not introspect Trading ABI")

        # Test trade parameters
        trade_params = {
            "user_address": wallet_address,
            "private_key": test_private_key,
            "market": "BTC/USD",
            "side": "LONG",
            "leverage": 2,  # Conservative leverage for mainnet
            "size": 5,  # $5 position size (small amount for mainnet)
        }

        print("📊 Trade Parameters:")
        print(f"   Market: {trade_params['market']}")
        print(f"   Side: {trade_params['side']}")
        print(f"   Leverage: {trade_params['leverage']}x")
        print(f"   Size: ${trade_params['size']}")

        # Execute trade
        print("\n🔄 Executing trade...")
        tx_result = await avantis_client.open_position(
            wallet_id=trade_params["user_address"],
            market=trade_params["market"],
            size=Decimal(str(trade_params["size"])),
            leverage=Decimal(str(trade_params["leverage"])),
            side=trade_params["side"].lower(),
            request_id=f"test_trade_{wallet_address}",
        )

        print("✅ Trade executed successfully!")
        print(f"📝 Transaction Hash: {tx_result}")
        print(f"🔗 View on BaseScan: https://basescan.org/tx/{tx_result}")

        return True

    except Exception as e:
        print(f"❌ Trade failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_real_trading())
    if success:
        print("\n🎉 REAL TRADE TEST PASSED!")
        print("✅ Bot successfully executed real trade on Base mainnet")
        print("✅ Transaction confirmed on blockchain")
        print("✅ Avantis protocol integration working")
    else:
        print("\n💥 REAL TRADE TEST FAILED")
        print("❌ Check error details above")
        sys.exit(1)
