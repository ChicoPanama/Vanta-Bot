"""Chainlink oracle provider for on-chain price feeds."""

import logging
from typing import Dict, Optional
import os
from web3 import Web3
from decimal import Decimal

from ..oracle_base import Oracle, Price
from src.services.markets.symbols import to_canonical
from src.config.feeds_config import get_feeds_config

logger = logging.getLogger(__name__)


class ChainlinkOracle(Oracle):
    """Chainlink oracle implementation using on-chain aggregators."""
    
    def __init__(self, web3: Web3, validate_on_init: bool = True):
        self.web3 = web3
        
        # Load configuration from centralized feeds.json
        feeds_config = get_feeds_config()
        if feeds_config.is_available():
            # Use centralized configuration
            self.aggregators = feeds_config.get_chainlink_feeds()
            logger.info(f"Loaded Chainlink feeds from centralized config: {len(self.aggregators)} feeds")
        else:
            # Fallback to environment variables
            self.aggregators = {
                # Crypto majors
                'BTC': os.getenv('CHAINLINK_BTC_USD_FEED', '0x64c911996D3c6aC71f9b455B1E8E7266BcbD848F'),
                'ETH': os.getenv('CHAINLINK_ETH_USD_FEED', '0x71041dddad3595F9CEd3DcCFBe3D1F4b0a16Bb70'),
                'SOL': os.getenv('CHAINLINK_SOL_USD_FEED', '0x975043adBb80fc32276CbF9Bbcfd4A601a12462D'),
                
                # Coinbase-wrapped assets
                'CBBTC': os.getenv('CHAINLINK_CBBTC_USD_FEED', '0x07DA0E54543a844a80ABE69c8A12F22B3aA59f9D'),
                'CBETH': os.getenv('CHAINLINK_CBETH_USD_FEED', '0xd7818272B9e248357d13057AAb0B417aF31E817d'),
                
                # Base-native token
                'AERO': os.getenv('CHAINLINK_AERO_USD_FEED', '0x4EC5970fC728C5f65ba413992CD5fF6FD70fcfF0'),
                
                # FX & commodities (optional)
                'EUR': os.getenv('CHAINLINK_EUR_USD_FEED', '0xc91D5C4e0C8DC21E9a29Aa03C172421f313b3F0F'),
                'XAU': os.getenv('CHAINLINK_XAU_USD_FEED', '0x5213eBB69743b85644dbB6E25cdF994aFBb8cF31'),
                
                # Stable/pegged on Base
                'EURC': os.getenv('CHAINLINK_EURC_USD_FEED', '0xDAe398520e2B67cd3f27aeF9Cf14D93D927f8250'),
            }
            logger.info(f"Using environment variables for Chainlink feeds: {len(self.aggregators)} feeds")
        
        # Check for configuration conflicts between feeds.json and environment variables
        self._check_config_conflicts()
        
        # Validate feeds on startup in production (can be disabled for health checks)
        if validate_on_init and os.getenv("ENVIRONMENT", "development") == "production":
            self._validate_feeds_on_startup()
    
    def _check_config_conflicts(self) -> None:
        """Check for conflicts between feeds.json and environment variables."""
        try:
            from src.config.feeds_config import get_feeds_config
            feeds_config = get_feeds_config()
            
            if not feeds_config.is_available():
                return  # No config file, no conflict possible
            
            config_feeds = feeds_config.get_chainlink_feeds()
            if not config_feeds:
                return  # No feeds in config, no conflict possible
            
            # Check if environment variables are set for feeds that exist in config
            env_vars = [
                'CHAINLINK_BTC_USD_FEED', 'CHAINLINK_ETH_USD_FEED', 'CHAINLINK_SOL_USD_FEED',
                'CHAINLINK_CBBTC_USD_FEED', 'CHAINLINK_CBETH_USD_FEED', 'CHAINLINK_AERO_USD_FEED',
                'CHAINLINK_EUR_USD_FEED', 'CHAINLINK_XAU_USD_FEED', 'CHAINLINK_EURC_USD_FEED'
            ]
            
            conflicting_vars = []
            for var in env_vars:
                if os.getenv(var):
                    conflicting_vars.append(var)
            
            if conflicting_vars:
                logger.warning(
                    f"⚠️  Configuration conflict detected: Both feeds.json and environment variables are set. "
                    f"Environment variables will override config: {', '.join(conflicting_vars)}. "
                    f"Consider using only one source of configuration to avoid confusion."
                )
                
        except Exception as e:
            logger.debug(f"Could not check for configuration conflicts: {e}")
        
    async def get_price(self, symbol: str, max_age_s: int = 5, max_dev_bps: int = 50) -> Price:
        """Get price from Chainlink aggregator with validation."""
        try:
            canonical = to_canonical(symbol)
            aggregator_address = self.aggregators.get(canonical.upper())
            if not aggregator_address:
                raise ValueError(f"Unsupported symbol: {symbol}")
            
            # Chainlink aggregator ABI for latestRoundData
            aggregator_abi = [{
                "inputs": [],
                "name": "latestRoundData",
                "outputs": [
                    {"name": "roundId", "type": "uint80"},
                    {"name": "answer", "type": "int256"},
                    {"name": "startedAt", "type": "uint256"},
                    {"name": "updatedAt", "type": "uint256"},
                    {"name": "answeredInRound", "type": "uint80"}
                ],
                "stateMutability": "view",
                "type": "function"
            }]
            
            contract = self.web3.eth.contract(
                address=self.web3.to_checksum_address(aggregator_address),
                abi=aggregator_abi
            )
            
            # Fix: Run blocking call in executor to avoid blocking event loop
            import asyncio
            # Use default thread pool executor (more efficient)
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,  # Use default thread pool
                contract.functions.latestRoundData().call
            )
            round_id, answer, started_at, updated_at, answered_in_round = result
            
            # Validate round data
            if round_id == 0:
                raise ValueError("No price data available")
            
            if answered_in_round != round_id:
                raise ValueError(f"Stale round data: {answered_in_round} != {round_id}")
            
            # Fix: Run get_block in executor to avoid blocking
            loop = asyncio.get_running_loop()
            current_block = await loop.run_in_executor(
                None,  # Use default thread pool
                self.web3.eth.get_block,
                'latest'
            )
            current_time = int(current_block.timestamp)
            age = current_time - updated_at
            if age > max_age_s:
                raise ValueError(f"Price too stale: {age}s > {max_age_s}s")
            
            # Convert to 1e8 fixed-point (Chainlink uses 8 decimals)
            price_1e8 = int(answer)
            
            # For Chainlink, we don't have confidence intervals in the same way
            # Use a conservative estimate based on staleness
            conf_1e8 = price_1e8 * min(age * 10, max_dev_bps) // 10000
            
            return Price(
                symbol=canonical,
                price=price_1e8,
                conf=conf_1e8,
                ts=updated_at,
                source="chainlink"
            )
            
        except Exception as e:
            logger.error(f"Chainlink oracle error for {symbol}: {e}")
            raise ValueError(f"Failed to get price from Chainlink: {e}")
    
    def _validate_feeds_on_startup(self):
        """Validate Chainlink feeds on startup - fail fast if invalid."""
        logger.info("Validating Chainlink feeds on startup...")
        
        # Expected price ranges for sanity checks (from centralized config or env)
        feeds_config = get_feeds_config()
        if feeds_config.is_available():
            # Use centralized configuration
            sanity_ranges = feeds_config.get_chainlink_sanity_ranges()
            price_ranges = {}
            for symbol, ranges in sanity_ranges.items():
                price_ranges[symbol] = (ranges['min'], ranges['max'])
        else:
            # Fallback to environment variables
            price_ranges = {
                'BTC': (
                    float(os.getenv('CHAINLINK_SANITY_BTC_MIN', '10000')),
                    float(os.getenv('CHAINLINK_SANITY_BTC_MAX', '200000'))
                ),
                'ETH': (
                    float(os.getenv('CHAINLINK_SANITY_ETH_MIN', '100')),
                    float(os.getenv('CHAINLINK_SANITY_ETH_MAX', '20000'))
                ),
                'SOL': (
                    float(os.getenv('CHAINLINK_SANITY_SOL_MIN', '10')),
                    float(os.getenv('CHAINLINK_SANITY_SOL_MAX', '1000'))
                ),
                'CBBTC': (
                    float(os.getenv('CHAINLINK_SANITY_CBBTC_MIN', '10000')),
                    float(os.getenv('CHAINLINK_SANITY_CBBTC_MAX', '200000'))
                ),
                'CBETH': (
                    float(os.getenv('CHAINLINK_SANITY_CBETH_MIN', '100')),
                    float(os.getenv('CHAINLINK_SANITY_CBETH_MAX', '20000'))
                ),
                'AERO': (
                    float(os.getenv('CHAINLINK_SANITY_AERO_MIN', '0.01')),
                    float(os.getenv('CHAINLINK_SANITY_AERO_MAX', '100'))
                ),
                'EUR': (
                    float(os.getenv('CHAINLINK_SANITY_EUR_MIN', '0.8')),
                    float(os.getenv('CHAINLINK_SANITY_EUR_MAX', '1.5'))
                ),
                'XAU': (
                    float(os.getenv('CHAINLINK_SANITY_XAU_MIN', '1000')),
                    float(os.getenv('CHAINLINK_SANITY_XAU_MAX', '5000'))
                ),
                'EURC': (
                    float(os.getenv('CHAINLINK_SANITY_EURC_MIN', '0.8')),
                    float(os.getenv('CHAINLINK_SANITY_EURC_MAX', '1.5'))
                ),
            }
        
        for symbol, address in self.aggregators.items():
            try:
                logger.info(f"Validating {symbol} feed at {address}")
                
                # Create contract instance
                aggregator_abi = [{
                    "inputs": [],
                    "name": "latestRoundData",
                    "outputs": [
                        {"name": "roundId", "type": "uint80"},
                        {"name": "answer", "type": "int256"},
                        {"name": "startedAt", "type": "uint256"},
                        {"name": "updatedAt", "type": "uint256"},
                        {"name": "answeredInRound", "type": "uint80"}
                    ],
                    "stateMutability": "view",
                    "type": "function"
                }]
                
                contract = self.web3.eth.contract(
                    address=self.web3.to_checksum_address(address),
                    abi=aggregator_abi
                )
                
                # Call latestRoundData
                result = contract.functions.latestRoundData().call()
                round_id, answer, started_at, updated_at, answered_in_round = result
                
                # Validate round data
                if round_id == 0:
                    raise ValueError(f"Feed {symbol} has no data (round_id = 0)")
                
                if answered_in_round != round_id:
                    raise ValueError(f"Feed {symbol} has stale round data: {answered_in_round} != {round_id}")
                
                # Convert price (Chainlink uses 8 decimals)
                price_usd = float(answer) / 1e8
                
                # Sanity check price range
                if symbol in price_ranges:
                    min_price, max_price = price_ranges[symbol]
                    if not (min_price <= price_usd <= max_price):
                        raise ValueError(f"Feed {symbol} price ${price_usd:,.2f} outside expected range ${min_price:,} - ${max_price:,}")
                
                # Check freshness (within last hour for production, more lenient for development)
                import time
                current_time = int(time.time())
                age_seconds = current_time - updated_at
                max_age = 3600 if os.getenv("ENVIRONMENT", "development") == "production" else 7200  # 1h prod, 2h dev
                if age_seconds > max_age:
                    if os.getenv("ENVIRONMENT", "development") == "production":
                        raise ValueError(f"Feed {symbol} is stale: {age_seconds}s old")
                    else:
                        logger.warning(f"⚠️  {symbol} feed is stale: {age_seconds}s old (development mode - continuing)")
                
                logger.info(f"✅ {symbol} feed validated: ${price_usd:,.2f} (age: {age_seconds}s)")
                
            except Exception as e:
                logger.error(f"❌ Chainlink feed validation failed for {symbol}: {e}")
                raise RuntimeError(f"CRITICAL: Chainlink feed validation failed for {symbol} at {address}: {e}. "
                                 f"Cannot start with invalid price feeds. Please verify CHAINLINK_{symbol}_USD_FEED environment variable.")
        
        logger.info("✅ All Chainlink feeds validated successfully")
