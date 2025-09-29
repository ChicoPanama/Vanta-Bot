#!/usr/bin/env python3
"""
CLI for monitoring contract unpause events.

This script watches for Unpaused(address) events and exits with code 0
when the contract becomes unpaused, ready for automated trading.

Usage:
    python -m src.cli.monitor_unpaused
    python -m src.cli.monitor_unpaused --auto-test
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from decimal import Decimal

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.models import HumanTradeParams, OrderType
from src.services.trade_service import TradeService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Monitor contract for unpause events",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor for unpause events (exit when unpaused)
  python -m src.cli.monitor_unpaused

  # Monitor and automatically test trade when unpaused
  python -m src.cli.monitor_unpaused --auto-test

  # Monitor with custom check interval
  python -m src.cli.monitor_unpaused --interval 10
        """
    )
    
    parser.add_argument(
        "--auto-test",
        action="store_true",
        help="Automatically test trade when contract unpauses"
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Check interval in seconds (default: 30)"
    )
    
    parser.add_argument(
        "--rpc",
        type=str,
        default="https://mainnet.base.org",
        help="RPC endpoint URL"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="config/addresses/base.mainnet.json",
        help="Network configuration file path"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser.parse_args()


def load_environment() -> tuple[str, str]:
    """
    Load environment variables for RPC URL and private key.
    
    Returns:
        Tuple of (rpc_url, private_key)
    """
    # Load from .env file if it exists
    env_file = Path("env/.env")
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
    
    # Get RPC URL
    rpc_url = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
    
    # Get private key
    private_key = os.getenv("TRADER_PRIVATE_KEY")
    if not private_key:
        raise ValueError(
            "TRADER_PRIVATE_KEY environment variable not set. "
            "Please set it in env/.env or export it directly."
        )
    
    return rpc_url, private_key


async def check_contract_status(trade_service: TradeService) -> bool:
    """
    Check if contract is unpaused.
    
    Returns:
        True if unpaused, False if paused
    """
    try:
        status = trade_service.get_contract_status()
        return not status.is_paused
    except Exception as e:
        logger.error(f"Failed to check contract status: {e}")
        return False


async def test_trade_when_unpaused(trade_service: TradeService) -> None:
    """Test a small trade when contract becomes unpaused."""
    print("\n🧪 TESTING TRADE ON UNPAUSE")
    print("-" * 40)
    
    # Use conservative test parameters
    test_params = HumanTradeParams(
        collateral_usdc=Decimal("1"),    # $1 USDC
        leverage_x=Decimal("2"),         # 2x leverage
        slippage_pct=Decimal("1"),       # 1% slippage
        pair_index=0,                    # BTC
        is_long=True,                    # Long position
        order_type=OrderType.MARKET
    )
    
    try:
        print(f"Testing with: ${test_params.collateral_usdc}, {test_params.leverage_x}x leverage")
        
        result = await trade_service.open_market_trade(
            params=test_params,
            dry_run=True  # Always dry run for safety
        )
        
        if result.success:
            print("✅ Test trade validation passed!")
        else:
            print(f"❌ Test trade validation failed: {result.error_message}")
            
    except Exception as e:
        print(f"❌ Test trade error: {e}")


async def monitor_loop(
    trade_service: TradeService,
    interval: int,
    auto_test: bool
) -> None:
    """
    Main monitoring loop.
    
    Args:
        trade_service: Initialized trade service
        interval: Check interval in seconds
        auto_test: Whether to auto-test when unpaused
    """
    print(f"🔍 Monitoring contract status (checking every {interval}s)")
    print("Press Ctrl+C to stop monitoring")
    print("-" * 60)
    
    check_count = 0
    
    while True:
        try:
            check_count += 1
            is_unpaused = await check_contract_status(trade_service)
            
            if is_unpaused:
                print(f"\n🎉 CONTRACT UNPAUSED! (check #{check_count})")
                print("Trading is now available!")
                
                if auto_test:
                    await test_trade_when_unpaused(trade_service)
                
                print("\n✅ Monitoring complete - exiting with success code")
                sys.exit(0)
            else:
                print(f"Check #{check_count}: Contract still paused...")
            
            # Wait for next check
            await asyncio.sleep(interval)
            
        except KeyboardInterrupt:
            print(f"\nMonitoring stopped by user (after {check_count} checks)")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            print(f"Error: {e} - continuing monitoring...")
            await asyncio.sleep(interval)


async def main():
    """Main CLI entry point."""
    try:
        # Parse arguments
        args = parse_args()
        
        # Set logging level
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Load environment
        rpc_url, private_key = load_environment()
        
        # Override RPC URL if provided
        if args.rpc != "https://mainnet.base.org":
            rpc_url = args.rpc
        
        # Initialize trade service
        trade_service = TradeService(
            rpc_url=rpc_url,
            private_key=private_key,
            network_config_path=args.config
        )
        
        print("🚀 AVANTIS CONTRACT UNPAUSE MONITOR")
        print("=" * 60)
        
        # Show initial status
        initial_status = await check_contract_status(trade_service)
        if initial_status:
            print("🟢 Contract is already unpaused!")
            if args.auto_test:
                await test_trade_when_unpaused(trade_service)
            sys.exit(0)
        else:
            print("🔴 Contract is currently paused")
        
        # Start monitoring
        await monitor_loop(
            trade_service=trade_service,
            interval=args.interval,
            auto_test=args.auto_test
        )
        
    except KeyboardInterrupt:
        print("\nMonitoring cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Monitor failed: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
