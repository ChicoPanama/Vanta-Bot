#!/usr/bin/env python3
"""
CLI for opening Avantis trades with human-readable parameters.

This script provides a clean command-line interface for opening trades
with proper validation and error handling.

Usage:
    python -m src.cli.open_trade --collat 10 --lev 2 --slip 1 --pair 0 --long
    python -m src.cli.open_trade --collat 100 --lev 5 --slip 0.5 --pair 1 --short --live
"""

import argparse
import asyncio
import logging
import os
import sys
from decimal import Decimal
from pathlib import Path

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
        description="Open an Avantis trade with human-readable parameters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Open a $10 long BTC position with 2x leverage and 1% slippage
  python -m src.cli.open_trade --collat 10 --lev 2 --slip 1 --pair 0 --long

  # Open a $100 short ETH position with 5x leverage and 0.5% slippage (live trade)
  python -m src.cli.open_trade --collat 100 --lev 5 --slip 0.5 --pair 1 --short --live

  # Test trade parameters without executing (dry run)
  python -m src.cli.open_trade --collat 50 --lev 3 --slip 1 --pair 2 --long
        """
    )
    
    # Required parameters
    parser.add_argument(
        "--collat", "--collateral",
        type=float,
        required=True,
        help="Collateral amount in USDC (e.g., 10 for $10)"
    )
    
    parser.add_argument(
        "--lev", "--leverage",
        type=float,
        required=True,
        help="Leverage multiplier (e.g., 2 for 2x leverage)"
    )
    
    parser.add_argument(
        "--slip", "--slippage",
        type=float,
        required=True,
        help="Slippage percentage (e.g., 1 for 1% slippage)"
    )
    
    parser.add_argument(
        "--pair",
        type=int,
        required=True,
        help="Trading pair index (0=BTC, 1=ETH, 2=SOL)"
    )
    
    # Direction (mutually exclusive)
    direction_group = parser.add_mutually_exclusive_group(required=True)
    direction_group.add_argument(
        "--long",
        action="store_true",
        help="Open long position"
    )
    direction_group.add_argument(
        "--short",
        action="store_true",
        help="Open short position"
    )
    
    # Optional parameters
    parser.add_argument(
        "--live",
        action="store_true",
        help="Execute live trade (default is dry run)"
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


def validate_arguments(args: argparse.Namespace) -> None:
    """
    Validate command line arguments.
    
    Args:
        args: Parsed command line arguments
        
    Raises:
        ValueError: If arguments are invalid
    """
    errors = []
    
    # Validate collateral
    if args.collat <= 0:
        errors.append("Collateral must be positive")
    elif args.collat < 1:
        errors.append("Minimum collateral is $1 USDC")
    elif args.collat > 100000:
        errors.append("Maximum collateral is $100,000 USDC")
    
    # Validate leverage
    if args.lev <= 0:
        errors.append("Leverage must be positive")
    elif args.lev < 1:
        errors.append("Minimum leverage is 1x")
    elif args.lev > 500:
        errors.append("Maximum leverage is 500x")
    
    # Validate slippage
    if args.slip < 0:
        errors.append("Slippage cannot be negative")
    elif args.slip > 10:
        errors.append("Maximum slippage is 10%")
    
    # Validate pair index
    if args.pair < 0:
        errors.append("Pair index must be non-negative")
    elif args.pair > 100:  # Conservative limit
        errors.append("Pair index too high")
    
    if errors:
        raise ValueError("Invalid arguments:\n" + "\n".join(f"  - {error}" for error in errors))


async def main():
    """Main CLI entry point."""
    try:
        # Parse arguments
        args = parse_args()
        
        # Set logging level
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Validate arguments
        validate_arguments(args)
        
        # Load environment
        rpc_url, private_key = load_environment()
        
        # Override RPC URL if provided
        if args.rpc != "https://mainnet.base.org":
            rpc_url = args.rpc
        
        # Create trade parameters
        params = HumanTradeParams(
            collateral_usdc=Decimal(str(args.collat)),
            leverage_x=Decimal(str(args.lev)),
            slippage_pct=Decimal(str(args.slip)),
            pair_index=args.pair,
            is_long=args.long,
            order_type=OrderType.MARKET
        )
        
        # Initialize trade service
        trade_service = TradeService(
            rpc_url=rpc_url,
            private_key=private_key,
            network_config_path=args.config
        )
        
        # Print trade summary
        print("=" * 60)
        print("AVANTIS TRADE SUMMARY")
        print("=" * 60)
        print(f"Collateral: ${params.collateral_usdc}")
        print(f"Leverage: {params.leverage_x}x")
        print(f"Slippage: {params.slippage_pct}%")
        print(f"Pair Index: {params.pair_index}")
        print(f"Direction: {'LONG' if params.is_long else 'SHORT'}")
        print(f"Mode: {'LIVE' if args.live else 'DRY RUN'}")
        print("=" * 60)
        
        # Confirm live trade
        if args.live:
            confirm = input("\n⚠️  LIVE TRADE - Are you sure? (yes/no): ")
            if confirm.lower() != "yes":
                print("Trade cancelled.")
                return
        
        # Execute trade
        result = await trade_service.open_market_trade(
            params=params,
            dry_run=not args.live
        )
        
        # Print result
        print("\n" + "=" * 60)
        if result.success:
            print("✅ TRADE SUCCESS")
            if result.transaction_hash == "DRY_RUN":
                print("Dry run completed successfully - trade would execute")
            else:
                print(f"Transaction Hash: {result.transaction_hash}")
                print(f"BaseScan URL: https://basescan.org/tx/{result.transaction_hash}")
                print(f"Block Number: {result.block_number}")
                print(f"Gas Used: {result.gas_used}")
        else:
            print("❌ TRADE FAILED")
            print(f"Error: {result.error_message}")
        print("=" * 60)
        
        # Exit with appropriate code
        sys.exit(0 if result.success else 1)
        
    except KeyboardInterrupt:
        print("\nTrade cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Trade failed: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
