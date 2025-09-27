"""
Base Chain Event Indexer for Vanta Bot
Handles backfilling and real-time monitoring of Avantis Trading contract events
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from web3 import Web3
from web3.middleware import geth_poa_middleware
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncpg
import redis.asyncio as redis

logger = logging.getLogger(__name__)

@dataclass
class TradeEvent:
    address: str
    pair: str
    is_long: bool
    size: float
    price: float
    leverage: int
    event_type: str
    block_number: int
    tx_hash: str
    timestamp: datetime
    fee: float = 0.0

class AvantisEventIndexer:
    """Indexes Avantis Trading contract events from Base chain"""
    
    def __init__(self, config, db_pool: asyncpg.Pool, redis_client: redis.Redis):
        self.config = config
        self.db_pool = db_pool
        self.redis = redis_client
        self.web3 = None
        self.trading_contract = None
        self.is_running = False
        
        # Initialize Web3 connection
        self._setup_web3()
        
    def _setup_web3(self):
        """Setup Web3 connection to Base chain"""
        try:
            self.web3 = Web3(Web3.WebsocketProvider(self.config.BASE_WS_URL))
            self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            # Load Trading contract ABI
            with open('config/abis/Trading.json') as f:
                trading_abi = json.load(f)
            
            self.trading_contract = self.web3.eth.contract(
                address=self.config.AVANTIS_TRADING_CONTRACT,
                abi=trading_abi
            )
            
            logger.info(f"Connected to Base chain, contract: {self.config.AVANTIS_TRADING_CONTRACT}")
            
        except Exception as e:
            logger.error(f"Failed to setup Web3 connection: {e}")
            raise
    
    async def start_monitoring(self):
        """Start real-time event monitoring"""
        if self.is_running:
            logger.warning("Event indexer is already running")
            return
            
        self.is_running = True
        logger.info("Starting Avantis event monitoring...")
        
        try:
            # First, backfill recent events
            await self._backfill_recent_events()
            
            # Start real-time monitoring
            await self._monitor_real_time_events()
            
        except Exception as e:
            logger.error(f"Error in event monitoring: {e}")
            self.is_running = False
            raise
    
    async def stop_monitoring(self):
        """Stop event monitoring"""
        self.is_running = False
        logger.info("Stopped Avantis event monitoring")
    
    async def _backfill_recent_events(self):
        """Backfill recent events to catch up"""
        try:
            # Get last indexed block from Redis
            last_block_key = "last_indexed_block"
            last_block = await self.redis.get(last_block_key)
            
            if last_block:
                from_block = int(last_block) + 1
            else:
                # Start from blocks ago if no previous index
                current_block = self.web3.eth.block_number
                from_block = current_block - self.config.EVENT_BACKFILL_BLOCKS
            
            current_block = self.web3.eth.block_number
            to_block = min(current_block, from_block + 1000)  # Process in chunks
            
            if from_block <= to_block:
                logger.info(f"Backfilling events from block {from_block} to {to_block}")
                await self._process_block_range(from_block, to_block)
                
                # Update last indexed block
                await self.redis.set(last_block_key, to_block)
            
        except Exception as e:
            logger.error(f"Error in backfill: {e}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _process_block_range(self, from_block: int, to_block: int):
        """Process events in a block range with retry logic"""
        try:
            events = []
            
            # Get TradeOpened events
            trade_opened_filter = self.trading_contract.events.TradeOpened.create_filter(
                fromBlock=from_block,
                toBlock=to_block
            )
            
            for event in trade_opened_filter.get_all_entries():
                trade_event = self._normalize_trade_event(event, 'OPENED')
                events.append(trade_event)
                
            # Get TradeClosed events
            trade_closed_filter = self.trading_contract.events.TradeClosed.create_filter(
                fromBlock=from_block,
                toBlock=to_block
            )
            
            for event in trade_closed_filter.get_all_entries():
                trade_event = self._normalize_trade_event(event, 'CLOSED')
                events.append(trade_event)
            
            # Persist events to database
            if events:
                await self._persist_events(events)
                logger.info(f"Processed {len(events)} events from blocks {from_block}-{to_block}")
            
        except Exception as e:
            logger.error(f"Error processing blocks {from_block}-{to_block}: {e}")
            raise
    
    def _normalize_trade_event(self, event, event_type: str) -> TradeEvent:
        """Normalize raw blockchain event to our data structure"""
        try:
            # Convert price from Avantis format (multiplied by 1e10)
            price = float(event.args.openPrice) / 1e10 if hasattr(event.args, 'openPrice') else 0.0
            
            # Convert size from DAI (multiplied by 1e18)
            size = float(event.args.positionSizeDai) / 1e18 if hasattr(event.args, 'positionSizeDai') else 0.0
            
            # Get fee if available
            fee = float(event.args.get('fee', 0)) / 1e18 if hasattr(event.args, 'fee') else 0.0
            
            # Get block timestamp
            timestamp = self._get_block_timestamp(event.blockNumber)
            
            return TradeEvent(
                address=event.args.trader.lower(),
                pair=str(event.args.pairIndex),
                is_long=event.args.long,
                size=size,
                price=price,
                leverage=event.args.leverage,
                event_type=event_type,
                block_number=event.blockNumber,
                tx_hash=event.transactionHash.hex(),
                timestamp=timestamp,
                fee=fee
            )
            
        except Exception as e:
            logger.error(f"Error normalizing event: {e}")
            raise
    
    def _get_block_timestamp(self, block_number: int) -> datetime:
        """Get timestamp for a block number"""
        try:
            block = self.web3.eth.get_block(block_number)
            return datetime.fromtimestamp(block['timestamp'])
        except Exception as e:
            logger.error(f"Error getting block timestamp for block {block_number}: {e}")
            return datetime.utcnow()
    
    async def _persist_events(self, events: List[TradeEvent]):
        """Persist events to database with conflict resolution"""
        if not events:
            return
            
        try:
            async with self.db_pool.acquire() as conn:
                # Use INSERT ... ON CONFLICT to handle duplicate events
                await conn.executemany("""
                    INSERT INTO trade_events (
                        address, pair, is_long, size, price, leverage, 
                        event_type, block_number, tx_hash, timestamp, fee
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (block_number, tx_hash, event_type) DO NOTHING
                """, [
                    (
                        event.address,
                        event.pair,
                        event.is_long,
                        event.size,
                        event.price,
                        event.leverage,
                        event.event_type,
                        event.block_number,
                        event.tx_hash,
                        event.timestamp,
                        event.fee
                    ) for event in events
                ])
                
                logger.debug(f"Persisted {len(events)} events to database")
                
        except Exception as e:
            logger.error(f"Error persisting events: {e}")
            raise
    
    async def _monitor_real_time_events(self):
        """Monitor real-time events using WebSocket"""
        logger.info("Starting real-time event monitoring...")
        
        # Create event filters
        trade_opened_filter = self.trading_contract.events.TradeOpened.create_filter(
            fromBlock='latest'
        )
        
        trade_closed_filter = self.trading_contract.events.TradeClosed.create_filter(
            fromBlock='latest'
        )
        
        while self.is_running:
            try:
                # Check for new TradeOpened events
                opened_events = trade_opened_filter.get_new_entries()
                for event in opened_events:
                    trade_event = self._normalize_trade_event(event, 'OPENED')
                    await self._persist_events([trade_event])
                    
                    # Update last indexed block
                    await self.redis.set("last_indexed_block", event.blockNumber)
                
                # Check for new TradeClosed events
                closed_events = trade_closed_filter.get_new_entries()
                for event in closed_events:
                    trade_event = self._normalize_trade_event(event, 'CLOSED')
                    await self._persist_events([trade_event])
                    
                    # Update last indexed block
                    await self.redis.set("last_indexed_block", event.blockNumber)
                
                # Wait before next check
                await asyncio.sleep(self.config.EVENT_MONITORING_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in real-time monitoring: {e}")
                await asyncio.sleep(10)  # Wait longer on error
    
    async def get_trader_events(self, address: str, since: Optional[datetime] = None) -> List[TradeEvent]:
        """Get trade events for a specific trader"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT address, pair, is_long, size, price, leverage, 
                           event_type, block_number, tx_hash, timestamp, fee
                    FROM trade_events
                    WHERE address = $1
                """
                params = [address]
                
                if since:
                    query += " AND timestamp >= $2"
                    params.append(since)
                
                query += " ORDER BY timestamp DESC"
                
                rows = await conn.fetch(query, *params)
                
                return [
                    TradeEvent(
                        address=row['address'],
                        pair=row['pair'],
                        is_long=row['is_long'],
                        size=float(row['size']),
                        price=float(row['price']),
                        leverage=row['leverage'],
                        event_type=row['event_type'],
                        block_number=row['block_number'],
                        tx_hash=row['tx_hash'],
                        timestamp=row['timestamp'],
                        fee=float(row['fee'] or 0)
                    ) for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Error getting trader events for {address}: {e}")
            return []
    
    async def get_recent_events(self, limit: int = 100) -> List[TradeEvent]:
        """Get recent trade events across all traders"""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT address, pair, is_long, size, price, leverage, 
                           event_type, block_number, tx_hash, timestamp, fee
                    FROM trade_events
                    ORDER BY timestamp DESC
                    LIMIT $1
                """, limit)
                
                return [
                    TradeEvent(
                        address=row['address'],
                        pair=row['pair'],
                        is_long=row['is_long'],
                        size=float(row['size']),
                        price=float(row['price']),
                        leverage=row['leverage'],
                        event_type=row['event_type'],
                        block_number=row['block_number'],
                        tx_hash=row['tx_hash'],
                        timestamp=row['timestamp'],
                        fee=float(row['fee'] or 0)
                    ) for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Error getting recent events: {e}")
            return []