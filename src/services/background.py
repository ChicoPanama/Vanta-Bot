"""
Background Service Manager
Manages all background services for the bot
"""

import asyncio
import os
from typing import List, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config.settings import settings
from src.utils.logging import get_logger
from src.services.analytics.position_tracker import PositionTracker
from src.services.indexers.avantis_indexer import AvantisIndexer
from src.services.contracts.avantis_registry import initialize_registry, resolve_avantis_vault
from src.services.cache_service import cache_service
from src.services.monitoring import metrics_service
from src.monitoring.health import start_health_monitoring

logger = get_logger(__name__)


class BackgroundServiceManager:
    """Manages all background services"""
    
    def __init__(self):
        self.services: List[asyncio.Task] = []
    
    async def start_all_services(self) -> None:
        """Start all background services"""
        logger.info("🔄 Starting background services...")
        
        # Start services in parallel
        tasks = [
            self._start_cache_service(),
            self._start_avantis_sdk_client(),
            self._start_price_feed_client(),
            self._start_contract_registry(),
            self._start_position_tracker(),
            self._start_avantis_indexer(),
            self._start_health_monitoring()
        ]
        
        # Wait for all services to start
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log any failures
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Service {i} failed to start: {result}")
        
        logger.info("✅ Background services startup completed")
    
    async def _start_cache_service(self) -> None:
        """Initialize cache service"""
        try:
            await cache_service.initialize()
            logger.info("✅ Cache service initialized")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize cache service: {e}")
    
    async def _start_avantis_sdk_client(self) -> None:
        """Initialize Avantis SDK client"""
        try:
            logger.info("🔄 Initializing Avantis SDK client...")
            from src.integrations.avantis.sdk_client import initialize_sdk_client
            
            sdk_client = initialize_sdk_client()
            logger.info("✅ Avantis SDK client initialized")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize SDK client: {e}")
    
    async def _start_price_feed_client(self) -> None:
        """Start price feed client"""
        try:
            from src.integrations.avantis.feed_client import initialize_feed_client
            
            feed_client = initialize_feed_client()
            if feed_client.is_configured():
                logger.info("🔄 Starting price feed client...")
                
                # Register price callbacks for major pairs
                from src.services.markets.avantis_price_provider import get_price_provider
                price_provider = get_price_provider()
                
                async def price_callback(price_update):
                    logger.debug(f"Price update: {price_update.pair} = {price_update.price}")
                    price_provider.latest_price[price_update.pair] = price_update.price
                
                await feed_client.start({
                    "ETH/USD": price_callback,
                    "BTC/USD": price_callback,
                })
                logger.info("✅ Price feed client started")
            else:
                logger.info("ℹ️ Price feed client not configured (PYTH_WS_URL not set)")
        except Exception as e:
            logger.warning(f"⚠️ Failed to start price feed client: {e}")
    
    async def _start_contract_registry(self) -> None:
        """Initialize contract registry"""
        try:
            if not (settings.AVANTIS_TRADING_CONTRACT and settings.BASE_RPC_URL):
                return
            
            from web3 import Web3
            
            # Initialize Web3 connection
            w3 = Web3(Web3.HTTPProvider(settings.BASE_RPC_URL))
            if not w3.is_connected():
                logger.error("❌ Failed to connect to Base RPC")
                return
            
            # Initialize contract registry
            registry = initialize_registry(w3, settings.AVANTIS_TRADING_CONTRACT)
            
            # Resolve vault address
            try:
                vault_address = await resolve_avantis_vault()
                if vault_address:
                    os.environ["AVANTIS_VAULT_CONTRACT"] = vault_address
                    logger.info(f"✅ Resolved Avantis Vault: {vault_address}")
                else:
                    logger.warning("⚠️ Could not resolve vault address from Trading Proxy")
            except Exception as e:
                logger.warning(f"⚠️ Error resolving vault address: {e}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to start contract registry: {e}")
    
    async def _start_position_tracker(self) -> None:
        """Start position tracker"""
        try:
            if not settings.DATABASE_URL:
                return
            
            engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
            tracker = PositionTracker(engine=engine)
            
            # Set tracker for handlers
            from src.bot.handlers.copy_trading_commands import set_position_tracker
            set_position_tracker(tracker)
            
            # Start position tracker as background task
            task = asyncio.create_task(tracker.start())
            self.services.append(task)
            logger.info("✅ Position tracker started")
        except Exception as e:
            logger.warning(f"⚠️ Failed to start position tracker: {e}")
    
    async def _start_avantis_indexer(self) -> None:
        """Start Avantis indexer"""
        try:
            if not (settings.AVANTIS_TRADING_CONTRACT and settings.BASE_RPC_URL):
                return
            
            # Set up database session factory for indexer
            engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
            Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
            
            indexer = AvantisIndexer()
            indexer.set_db_session_factory(Session)
            
            # Get latest block and do initial backfill
            w3 = indexer.w3_http
            latest = w3.eth.block_number
            backfill_range = settings.INDEXER_BACKFILL_RANGE
            backfill_from = max(0, latest - backfill_range)
            
            logger.info(f"🔄 Starting indexer backfill from block {backfill_from} to {latest}")
            
            # Do initial backfill, then start tailing
            task = asyncio.create_task(self._run_indexer_with_backfill(indexer, backfill_from, latest))
            self.services.append(task)
            logger.info("✅ Avantis indexer started with backfill")
        except Exception as e:
            logger.warning(f"⚠️ Failed to start Avantis indexer: {e}")
    
    async def _start_health_monitoring(self) -> None:
        """Start health monitoring"""
        try:
            task = asyncio.create_task(start_health_monitoring())
            self.services.append(task)
            logger.info("✅ Health monitoring started")
        except Exception as e:
            logger.warning(f"⚠️ Failed to start health monitoring: {e}")
    
    async def _run_indexer_with_backfill(self, indexer, from_block: int, to_block: int):
        """Run indexer with backfill then tail follow"""
        try:
            await indexer.backfill(from_block, to_block)
            logger.info("✅ Backfill completed, starting tail following...")
            await indexer.tail_follow(start_block=to_block)
        except Exception as e:
            logger.error(f"❌ Indexer error: {e}")
    
    async def stop_all_services(self) -> None:
        """Stop all background services"""
        logger.info("🔄 Stopping background services...")
        
        for task in self.services:
            if not task.done():
                task.cancel()
        
        # Wait for all tasks to complete
        if self.services:
            await asyncio.gather(*self.services, return_exceptions=True)
        
        # Close cache service
        await cache_service.close()
        
        logger.info("✅ All background services stopped")
