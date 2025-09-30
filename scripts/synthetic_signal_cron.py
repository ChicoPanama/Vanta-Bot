#!/usr/bin/env python3
"""
Synthetic Signal Cron
Sends a harmless test signal to verify the copy-trading pipeline is alive
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


async def main():
    """Send synthetic signal to verify pipeline health"""
    try:
        from telegram import Bot

        from src.services.copytrading.alerts import on_trader_signal
        from src.services.copytrading.copy_service import set_cfg

        # Get configuration from environment
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            log.error("TELEGRAM_BOT_TOKEN environment variable not set")
            return False

        admin_ids = os.getenv("ADMIN_USER_IDS", "").split(",")
        admin_ids = [aid.strip() for aid in admin_ids if aid.strip()]

        if not admin_ids:
            log.error("ADMIN_USER_IDS environment variable not set")
            return False

        # Use first admin as ops chat
        ops_chat_id = int(admin_ids[0])
        log.info(f"Using ops chat: {ops_chat_id}")

        # Create bot
        bot = Bot(token=bot_token)

        # Set up synthetic trader configuration (auto_copy OFF for safety)
        synthetic_trader = "synthetic:health"
        set_cfg(
            ops_chat_id,
            synthetic_trader,
            {
                "auto_copy": False,  # Safety: never auto-copy synthetic signals
                "notify": True,
                "sizing_mode": "MIRROR",
            },
        )
        log.info(f"Set up synthetic trader config for {synthetic_trader}")

        # Create harmless synthetic signal
        synthetic_signal = {
            "pair": "SYNTH/USD",
            "side": "LONG",
            "lev": 1,
            "notional_usd": 1,
            "collateral_usdc": 1,
        }

        log.info("Sending synthetic signal...")
        await on_trader_signal(bot, ops_chat_id, synthetic_trader, synthetic_signal)
        log.info("✅ Synthetic signal sent successfully")

        # Clean up synthetic trader config
        from src.services.copytrading.copy_service import unfollow

        unfollow(ops_chat_id, synthetic_trader)
        log.info("Cleaned up synthetic trader config")

        return True

    except Exception as e:
        log.error(f"❌ Synthetic signal failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def run_synthetic_check():
    """Run the synthetic check and exit with appropriate code"""
    success = asyncio.run(main())
    if success:
        print("✅ Synthetic signal check passed")
        sys.exit(0)
    else:
        print("❌ Synthetic signal check failed")
        sys.exit(1)


if __name__ == "__main__":
    run_synthetic_check()
