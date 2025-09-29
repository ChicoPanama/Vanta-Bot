#!/usr/bin/env python3
"""
CLI for preflight validation and testing.

This script performs comprehensive validation of trade parameters
and contract status without executing any transactions.

Usage:
    python -m src.cli.preflight
    python -m src.cli.preflight --collat 10 --lev 2 --slip 1 --pair 0 --long
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
        description="Perform preflight validation of trading parameters and contract status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check contract status and wallet info
  python -m src.cli.preflight

  # Validate specific trade parameters
  python -m src.cli.preflight --collat 10 --lev 2 --slip 1 --pair 0 --long

  # Test with different parameters
  python -m src.cli.preflight --collat 100 --lev 5 --slip 0.5 --pair 1 --short
        """
    )
    
    # Optional trade parameters for validation
    parser.add_argument(
        "--collat", "--collateral",
        type=float,
        help="Collateral amount in USDC (e.g., 10 for $10)"
    )
    
    parser.add_argument(
        "--lev", "--leverage",
        type=float,
        help="Leverage multiplier (e.g., 2 for 2x leverage)"
    )
    
    parser.add_argument(
        "--slip", "--slippage",
        type=float,
        help="Slippage percentage (e.g., 1 for 1% slippage)"
    )
    
    parser.add_argument(
        "--pair",
        type=int,
        help="Trading pair index (0=BTC, 1=ETH, 2=SOL)"
    )
    
    # Direction (mutually exclusive)
    direction_group = parser.add_mutually_exclusive_group()
    direction_group.add_argument(
        "--long",
        action="store_true",
        help="Validate long position"
    )
    direction_group.add_argument(
        "--short",
        action="store_true",
        help="Validate short position"
    )
    
    # Optional parameters
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


async def check_contract_status(trade_service: TradeService) -> None:
    """Check and display contract status."""
    print("🔍 CONTRACT STATUS")
    print("-" * 40)
    
    try:
        status = trade_service.get_contract_status()
        
        print(f"Network: {trade_service.network_config['network']}")
        print(f"Chain ID: {trade_service.network_config['chainId']}")
        print(f"Trading Contract: {status.operator}")
        print(f"Status: {'🟢 UNPAUSED' if not status.is_paused else '🔴 PAUSED'}")
        print(f"Operator: {status.operator}")
        print(f"Max Slippage: {status.max_slippage}")
        print(f"Pair Infos: {status.pair_infos_address}")
        
        if status.is_paused:
            print("\n⚠️  WARNING: Trading is currently paused!")
            print("   Trades will fail until the contract is unpaused.")
        
    except Exception as e:
        print(f"❌ Failed to get contract status: {e}")


async def check_wallet_info(trade_service: TradeService) -> None:
    """Check and display wallet information."""
    print("\n💰 WALLET INFORMATION")
    print("-" * 40)
    
    try:
        wallet_info = trade_service.get_wallet_info()
        
        print(f"Address: {wallet_info.address}")
        print(f"ETH Balance: {wallet_info.eth_balance:.6f} ETH")
        print(f"USDC Balance: ${wallet_info.usdc_balance:.2f} USDC")
        print(f"Connected: {'✅ Yes' if wallet_info.is_connected else '❌ No'}")
        
        # Check minimum requirements
        if wallet_info.eth_balance < Decimal("0.001"):
            print("\n⚠️  WARNING: Low ETH balance for gas fees!")
        
        if wallet_info.usdc_balance < Decimal("1"):
            print("⚠️  WARNING: Insufficient USDC balance!")
        
    except Exception as e:
        print(f"❌ Failed to get wallet info: {e}")


async def check_contract_limits(trade_service: TradeService) -> None:
    """Check and display contract limits."""
    print("\n📊 CONTRACT LIMITS")
    print("-" * 40)
    
    try:
        limits = trade_service.get_contract_limits()
        
        print(f"Min Position Size: ${limits['minPositionSize'] / 1e6:.2f} USDC")
        print(f"Max Position Size: ${limits['maxPositionSize'] / 1e6:.2f} USDC")
        print(f"Max Leverage: {limits['maxLeverage'] / 1e10:.0f}x")
        print(f"Max Slippage: {limits['maxSlippage'] / 1e10:.1f}%")
        print(f"Max Pairs: {limits['maxPairs']}")
        
    except Exception as e:
        print(f"❌ Failed to get contract limits: {e}")


async def validate_trade_params(
    trade_service: TradeService,
    args: argparse.Namespace
) -> None:
    """Validate specific trade parameters."""
    print("\n🎯 TRADE PARAMETER VALIDATION")
    print("-" * 40)
    
    # Create trade parameters
    params = HumanTradeParams(
        collateral_usdc=Decimal(str(args.collat)),
        leverage_x=Decimal(str(args.lev)),
        slippage_pct=Decimal(str(args.slip)),
        pair_index=args.pair,
        is_long=args.long,
        order_type=OrderType.MARKET
    )
    
    print(f"Collateral: ${params.collateral_usdc}")
    print(f"Leverage: {params.leverage_x}x")
    print(f"Slippage: {params.slippage_pct}%")
    print(f"Pair Index: {params.pair_index}")
    print(f"Direction: {'LONG' if params.is_long else 'SHORT'}")
    
    try:
        # Perform dry run validation
        result = await trade_service.open_market_trade(
            params=params,
            dry_run=True
        )
        
        if result.success:
            print("\n✅ VALIDATION PASSED")
            print("Trade parameters are valid and ready for execution.")
        else:
            print("\n❌ VALIDATION FAILED")
            print(f"Error: {result.error_message}")
            
    except Exception as e:
        print(f"\n❌ VALIDATION ERROR: {e}")


async def check_price_feeds(trade_service: TradeService) -> None:
    """Check price feed availability."""
    print("\n📈 PRICE FEED STATUS")
    print("-" * 40)
    
    try:
        # Test price feeds for common pairs
        pairs = [
            (0, "BTC/USD"),
            (1, "ETH/USD"),
            (2, "SOL/USD")
        ]
        
        for pair_index, pair_name in pairs:
            try:
                price = await trade_service.get_current_price(pair_index)
                if price:
                    print(f"{pair_name}: ${price:,.2f}")
                else:
                    print(f"{pair_name}: ❌ Unavailable")
            except Exception as e:
                print(f"{pair_name}: ❌ Error - {e}")
                
    except Exception as e:
        print(f"❌ Failed to check price feeds: {e}")


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
        
        print("🚀 AVANTIS TRADING PREFLIGHT CHECK")
        print("=" * 60)
        
        # Perform checks
        await check_contract_status(trade_service)
        await check_wallet_info(trade_service)
        await check_contract_limits(trade_service)
        await check_price_feeds(trade_service)
        
        # Validate specific trade parameters if provided
        if all([
            args.collat is not None,
            args.lev is not None,
            args.slip is not None,
            args.pair is not None,
            args.long or args.short
        ]):
            await validate_trade_params(trade_service, args)
        
        print("\n" + "=" * 60)
        print("✅ PREFLIGHT CHECK COMPLETE")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\nPreflight check cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Preflight check failed: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
