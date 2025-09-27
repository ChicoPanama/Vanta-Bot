"""
Avantis Event Indexer for Base Chain
Extracts and processes trade events from Avantis Protocol contracts
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

logger = logging.getLogger(__name__)

@dataclass
class TradeEvent:
    """Normalized trade event data structure"""
    address: str
    pair_index: int
    pair_symbol: str
    is_long: bool
    size: float
    price: float
    leverage: float
    event_type: str  # 'OPENED' or 'CLOSED'
    block_number: int
    tx_hash: str
    timestamp: datetime
    fee: float
    trade_id: str

class AvantisEventIndexer:
    """Indexes trade events from Avantis Protocol contracts on Base"""
    
    def __init__(self, config, db_pool: asyncpg.Pool):
        self.config = config
        self.db_pool = db_pool
        
        # Initialize Web3 connection
        self.web3 = Web3(Web3.WebsocketProvider(config.BASE_WS_URL))
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        # Load contract ABIs
        self.trading_abi = self._load_abi('Trading')
        self.vault_abi = self._load_abi('Vault')
        
        # Initialize contracts
        self.trading_contract = self.web3.eth.contract(
            address=config.AVANTIS_TRADING_CONTRACT,
            abi=self.trading_abi
        )
        
        self.vault_contract = self.web3.eth.contract(
            address=config.AVANTIS_VAULT_CONTRACT,
            abi=self.vault_abi
        )
        
        # Pair index to symbol mapping (will be populated from contract)
        self.pair_mapping = {}
        
    def _load_abi(self, contract_name: str) -> List[Dict]:
        """Load contract ABI from file"""
        try:
            with open(f'config/abis/{contract_name}.json') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"ABI file not found for {contract_name}, using empty ABI")
            return []
    
    async def start_indexing(self):
        """Start the event indexing process"""
        logger.info("Starting Avantis event indexing...")
        
        # Initialize pair mapping
        await self._initialize_pair_mapping()
        
        # Start background tasks
        asyncio.create_task(self._backfill_historical_events())
        asyncio.create_task(self._monitor_new_events())
        
    async def _initialize_pair_mapping(self):
        """Initialize pair index to symbol mapping"""
        try:
            # Get pair count from contract
            pair_count = self.trading_contract.functions.pairCount().call()
            
            for i in range(pair_count):
                try:
                    # Get pair info from contract
                    pair_info = self.trading_contract.functions.pairs(i).call()
                    symbol = pair_info[0]  # Assuming first element is symbol
                    self.pair_mapping[i] = symbol
                except Exception as e:
                    logger.warning(f"Failed to get pair info for index {i}: {e}")
                    
            logger.info(f"Initialized {len(self.pair_mapping)} pair mappings")
            
        except Exception as e:
            logger.error(f"Failed to initialize pair mapping: {e}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _backfill_historical_events(self):
        """Backfill historical events from the last N blocks"""
        try:
            # Get current block
            current_block = self.web3.eth.block_number
            from_block = max(0, current_block - self.config.EVENT_BACKFILL_BLOCKS)
            
            logger.info(f"Backfilling events from block {from_block} to {current_block}")
            
            # Process in chunks to avoid RPC limits
            chunk_size = 1000
            for start_block in range(from_block, current_block, chunk_size):
                end_block = min(start_block + chunk_size, current_block)
                
                events = await self._fetch_events_in_range(start_block, end_block)
                if events:
                    await self._persist_events(events)
                
                # Small delay to avoid overwhelming RPC
                await asyncio.sleep(0.1)
                
            logger.info("Historical event backfill completed")
            
        except Exception as e:
            logger.error(f"Error in historical backfill: {e}")
    
    async def _monitor_new_events(self):
        """Monitor for new events in real-time"""
        logger.info("Starting real-time event monitoring...")
        
        last_processed_block = await self._get_last_processed_block()
        
        while True:
            try:
                current_block = self.web3.eth.block_number
                
                if current_block > last_processed_block:
                    # Process new blocks
                    events = await self._fetch_events_in_range(
                        last_processed_block + 1, 
                        current_block
                    )
                    
                    if events:
                        await self._persist_events(events)
                        logger.info(f"Processed {len(events)} new events")
                    
                    last_processed_block = current_block
                    await self._update_last_processed_block(current_block)
                
                # Wait before next check
                await asyncio.sleep(self.config.EVENT_MONITORING_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in real-time monitoring: {e}")
                await asyncio.sleep(10)
    
    async def _fetch_events_in_range(self, from_block: int, to_block: int) -> List[TradeEvent]:
        """Fetch all trade events in a block range"""
        events = []
        
        try:
            # Get TradeOpened events
            trade_opened_filter = self.trading_contract.events.TradeOpened.create_filter(
                fromBlock=from_block,
                toBlock=to_block
            )
            
            for event in trade_opened_filter.get_all_entries():
                normalized_event = self._normalize_trade_event(event, 'OPENED')
                if normalized_event:
                    events.append(normalized_event)
            
            # Get TradeClosed events
            trade_closed_filter = self.trading_contract.events.TradeClosed.create_filter(
                fromBlock=from_block,
                toBlock=to_block
            )
            
            for event in trade_closed_filter.get_all_entries():
                normalized_event = self._normalize_trade_event(event, 'CLOSED')
                if normalized_event:
                    events.append(normalized_event)
                    
        except Exception as e:
            logger.error(f"Error fetching events in range {from_block}-{to_block}: {e}")
        
        return events
    
    def _normalize_trade_event(self, event, event_type: str) -> Optional[TradeEvent]:
        """Normalize raw blockchain event to our data structure"""
        try:
            args = event.args
            
            # Get pair symbol from mapping
            pair_symbol = self.pair_mapping.get(args.pairIndex, f"PAIR_{args.pairIndex}")
            
            # Convert values from contract units
            size = float(args.positionSizeDai) / 1e18  # DAI has 18 decimals
            price = float(args.openPrice) / 1e10  # Price has 10 decimals
            fee = float(args.get('fee', 0)) / 1e18
            
            # Get block timestamp
            block = self.web3.eth.get_block(event.blockNumber)
            timestamp = datetime.fromtimestamp(block.timestamp)
            
            # Generate unique trade ID
            trade_id = f"{event.transactionHash.hex()}_{event.logIndex}"
            
            return TradeEvent(
                address=args.trader,
                pair_index=args.pairIndex,
                pair_symbol=pair_symbol,
                is_long=args.long,
                size=size,
                price=price,
                leverage=args.leverage,
                event_type=event_type,
                block_number=event.blockNumber,
                tx_hash=event.transactionHash.hex(),
                timestamp=timestamp,
                fee=fee,
                trade_id=trade_id
            )
            
        except Exception as e:
            logger.error(f"Error normalizing event: {e}")
            return None
    
    async def _persist_events(self, events: List[TradeEvent]):
        """Persist events to database with conflict resolution"""
        if not events:
            return
        
        async with self.db_pool.acquire() as conn:
            # Use upsert to handle duplicate events
            query = """
                INSERT INTO trade_events (
                    address, pair_index, pair_symbol, is_long, size, price, 
                    leverage, event_type, block_number, tx_hash, timestamp, 
                    fee, trade_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                ON CONFLICT (tx_hash, block_number, address, event_type) DO NOTHING
            """
            
            values = [
                (
                    event.address,
                    event.pair_index,
                    event.pair_symbol,
                    event.is_long,
                    event.size,
                    event.price,
                    event.leverage,
                    event.event_type,
                    event.block_number,
                    event.tx_hash,
                    event.timestamp,
                    event.fee,
                    event.trade_id
                )
                for event in events
            ]
            
            await conn.executemany(query, values)
            logger.info(f"Persisted {len(events)} trade events")
    
    async def _get_last_processed_block(self) -> int:
        """Get the last processed block number from database"""
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.fetchval(
                    "SELECT MAX(block_number) FROM trade_events"
                )
                return result or 0
        except Exception as e:
            logger.error(f"Error getting last processed block: {e}")
            return 0
    
    async def _update_last_processed_block(self, block_number: int):
        """Update the last processed block number"""
        # This could be stored in Redis for faster access
        # For now, we'll rely on the database query above
        pass
    
    async def get_trader_events(self, address: str, since: Optional[datetime] = None) -> List[TradeEvent]:
        """Get all events for a specific trader"""
        try:
            async with self.db_pool.acquire() as conn:
                if since:
                    query = """
                        SELECT * FROM trade_events 
                        WHERE address = $1 AND timestamp >= $2
                        ORDER BY timestamp ASC
                    """
                    rows = await conn.fetch(query, address, since)
                else:
                    query = """
                        SELECT * FROM trade_events 
                        WHERE address = $1
                        ORDER BY timestamp ASC
                    """
                    rows = await conn.fetch(query, address)
                
                return [self._row_to_trade_event(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting trader events: {e}")
            return []
    
    def _row_to_trade_event(self, row) -> TradeEvent:
        """Convert database row to TradeEvent object"""
        return TradeEvent(
            address=row['address'],
            pair_index=row['pair_index'],
            pair_symbol=row['pair_symbol'],
            is_long=row['is_long'],
            size=float(row['size']),
            price=float(row['price']),
            leverage=float(row['leverage']),
            event_type=row['event_type'],
            block_number=row['block_number'],
            tx_hash=row['tx_hash'],
            timestamp=row['timestamp'],
            fee=float(row['fee']),
            trade_id=row['trade_id']
        )
    
    async def get_recent_events(self, limit: int = 100) -> List[TradeEvent]:
        """Get recent trade events across all traders"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT * FROM trade_events 
                    ORDER BY timestamp DESC 
                    LIMIT $1
                """
                rows = await conn.fetch(query, limit)
                return [self._row_to_trade_event(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting recent events: {e}")
            return []
    
    async def get_events_by_pair(self, pair_symbol: str, since: Optional[datetime] = None) -> List[TradeEvent]:
        """Get events for a specific trading pair"""
        try:
            async with self.db_pool.acquire() as conn:
                if since:
                    query = """
                        SELECT * FROM trade_events 
                        WHERE pair_symbol = $1 AND timestamp >= $2
                        ORDER BY timestamp ASC
                    """
                    rows = await conn.fetch(query, pair_symbol, since)
                else:
                    query = """
                        SELECT * FROM trade_events 
                        WHERE pair_symbol = $1
                        ORDER BY timestamp ASC
                    """
                    rows = await conn.fetch(query, pair_symbol)
                
                return [self._row_to_trade_event(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting events by pair: {e}")
            return []
    
    async def get_volume_stats(self, since: datetime) -> Dict[str, float]:
        """Get volume statistics by pair since a given time"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT 
                        pair_symbol,
                        SUM(size * price) as total_volume,
                        COUNT(*) as trade_count
                    FROM trade_events 
                    WHERE timestamp >= $1 AND event_type = 'OPENED'
                    GROUP BY pair_symbol
                    ORDER BY total_volume DESC
                """
                rows = await conn.fetch(query, since)
                
                return {
                    row['pair_symbol']: {
                        'volume': float(row['total_volume']),
                        'trade_count': row['trade_count']
                    }
                    for row in rows
                }
                
        except Exception as e:
            logger.error(f"Error getting volume stats: {e}")
            return {}
    
    async def stop(self):
        """Stop the event indexer"""
        logger.info("Stopping Avantis event indexer...")
        # Cleanup resources if needed
