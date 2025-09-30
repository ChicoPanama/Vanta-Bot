#!/usr/bin/env python3
"""
Development script to test copy-trading signal firing
Usage: python scripts/dev_fire_signal.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    try:
        from telegram import Bot

        from src.services.copytrading.alerts import on_trader_signal
        from src.services.copytrading.copy_service import set_cfg

        # Get bot token from environment
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            print("❌ TELEGRAM_BOT_TOKEN environment variable not set")
            return

        # Configuration
        bot = Bot(token=bot_token)
        uid = int(os.getenv("TEST_USER_ID", "12345"))  # Default to test user
        tk = os.getenv("TEST_TRADER_KEY", "0xabc...trader")  # Default test trader

        print(f"🚀 Testing signal firing for user {uid}, trader {tk}")

        # Ensure a follow exists & auto_copy is ON
        test_config = {
            "auto_copy": True,
            "notify": True,
            "sizing_mode": "MIRROR",
            "per_trade_cap_usd": 1000,
            "max_leverage": 50,
            "fixed_usd": 250.0,
        }
        set_cfg(uid, tk, test_config)
        print(f"✅ Set follow config for trader {tk}")

        # Create test signal
        signal = {
            "pair": "ETH/USD",
            "side": "LONG",
            "lev": 25,
            "notional_usd": 500,
            "collateral_usdc": 20,
        }

        print(f"📡 Firing signal: {signal}")
        await on_trader_signal(bot, uid, tk, signal)
        print("✅ Signal fired successfully!")

        # Test with notifications off
        print("\n🔄 Testing with notifications OFF...")
        set_cfg(uid, tk, {"auto_copy": True, "notify": False, "sizing_mode": "MIRROR"})
        await on_trader_signal(bot, uid, tk, signal)
        print("✅ Signal fired with notifications off (should not receive alert)")

        # Test with auto-copy off
        print("\n🔄 Testing with auto-copy OFF...")
        set_cfg(uid, tk, {"auto_copy": False, "notify": True, "sizing_mode": "MIRROR"})
        await on_trader_signal(bot, uid, tk, signal)
        print("✅ Signal fired with auto-copy off (should receive alert but no copy)")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
