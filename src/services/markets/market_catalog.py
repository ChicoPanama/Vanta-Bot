"""Market catalog with verified Avantis addresses (Phase 3)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MarketInfo:
    """Market information."""

    symbol: str  # "BTC-USD"
    market_id: int  # Avantis internal market ID
    base_token: str  # Base asset (e.g., BTC)
    quote_token: str  # Quote asset (e.g., USD)
    perpetual: str  # Perpetual/Router/Market contract address
    decimals_price: int  # Price decimals used by contract (e.g., 8)
    min_position_usd: int  # Protocol min size in USD (scaled to 1e6)


def default_market_catalog() -> dict[str, MarketInfo]:
    """Default market catalog with Base mainnet addresses.
    
    WARNING: Replace placeholder addresses with verified Avantis addresses.
    These are loaded from config/addresses/base.mainnet.json
    """
    # Load from config file
    import json
    import os
    
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "config",
        "addresses",
        "base.mainnet.json"
    )
    
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        
        trading_address = config["contracts"]["trading"]["address"]
        
        # Define supported markets
        # Note: In production, these should be loaded from on-chain registry
        # or verified configuration. Using placeholder market IDs for now.
        return {
            "BTC-USD": MarketInfo(
                symbol="BTC-USD",
                market_id=0,
                base_token="BTC",
                quote_token="USD",
                perpetual=trading_address,
                decimals_price=8,
                min_position_usd=5_000_000,  # 5 USDC in 1e6
            ),
            "ETH-USD": MarketInfo(
                symbol="ETH-USD",
                market_id=1,
                base_token="ETH",
                quote_token="USD",
                perpetual=trading_address,
                decimals_price=8,
                min_position_usd=5_000_000,
            ),
            "SOL-USD": MarketInfo(
                symbol="SOL-USD",
                market_id=2,
                base_token="SOL",
                quote_token="USD",
                perpetual=trading_address,
                decimals_price=8,
                min_position_usd=5_000_000,
            ),
        }
    except Exception as e:
        # Fallback to hardcoded values if config load fails
        logger.warning(f"Failed to load market config: {e}, using fallback")
        return {
            "BTC-USD": MarketInfo(
                symbol="BTC-USD",
                market_id=0,
                base_token="BTC",
                quote_token="USD",
                perpetual="0x44914408af82bC9983bbb330e3578E1105e11d4e",  # From config
                decimals_price=8,
                min_position_usd=5_000_000,
            ),
            "ETH-USD": MarketInfo(
                symbol="ETH-USD",
                market_id=1,
                base_token="ETH",
                quote_token="USD",
                perpetual="0x44914408af82bC9983bbb330e3578E1105e11d4e",
                decimals_price=8,
                min_position_usd=5_000_000,
            ),
        }


import logging
logger = logging.getLogger(__name__)
