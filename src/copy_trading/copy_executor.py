"""
Copy Execution Engine for Vanta Bot
Handles copy trading execution and position management
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import uuid
import asyncpg
import redis.asyncio as redis

from ..ai.market_intelligence import MarketIntelligence

logger = logging.getLogger(__name__)

@dataclass
class CopyTradeRequest:
    """Copy trade request data structure"""
    copytrader_id: int
    leader_address: str
    trade_data: Dict
    original_size: float
    target_size: float
    max_slippage_bps: int
    priority: int = 1
    request_id: str = None

    def __post_init__(self):
        if self.request_id is None:
            self.request_id = str(uuid.uuid4())

@dataclass
class CopyConfiguration:
    """Copy trading configuration"""
    copytrader_id: int
    user_id: int
    leader_address: str
    is_enabled: bool
    sizing_mode: str
    sizing_value: float
    max_slippage_bps: int
    max_leverage: float
    notional_cap: float
    pair_filters: Dict
    tp_sl_policy: Dict

class CopyExecutor:
    """Copy trading execution engine"""
    
    def __init__(self, db_pool: asyncpg.Pool, redis_client: redis.Redis, 
                 avantis_client, market_intelligence: MarketIntelligence, config):
        self.db_pool = db_pool
        self.redis = redis_client
        self.avantis = avantis_client
        self.market_intel = market_intelligence
        self.config = config
        
        # Execution queue and state
        self.execution_queue = asyncio.Queue()
        self.active_copytraders = set()
        self.running = False
        
    async def start_monitoring(self):
        """Start monitoring leaders and processing copy trades"""
        logger.info("Starting copy execution engine...")
        self.running = True
        
        # Start execution worker
        asyncio.create_task(self._execution_worker())
        
        # Start leader monitoring
        asyncio.create_task(self._monitor_leaders())
        
        # Start configuration monitoring
        asyncio.create_task(self._monitor_configurations())
    
    async def _execution_worker(self):
        """Worker that processes copy trade requests"""
        logger.info("Copy execution worker started")
        
        while self.running:
            try:
                # Get next copy request
                copy_request = await self.execution_queue.get()
                
                # Execute the copy trade
                await self._execute_copy_trade(copy_request)
                
            except Exception as e:
                logger.error(f"Error in copy execution worker: {e}")
                await asyncio.sleep(1)
    
    async def _monitor_leaders(self):
        """Monitor followed leaders for new trades"""
        logger.info("Leader monitoring started")
        
        while self.running:
            try:
                # Get all active copy configurations
                active_configs = await self._get_active_copy_configs()
                
                for config in active_configs:
                    await self._check_leader_activity(config)
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in leader monitoring: {e}")
                await asyncio.sleep(10)
    
    async def _monitor_configurations(self):
        """Monitor for configuration changes"""
        while self.running:
            try:
                # Check for new or updated configurations
                await self._update_active_copytraders()
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring configurations: {e}")
                await asyncio.sleep(30)
    
    async def _get_active_copy_configs(self) -> List[CopyConfiguration]:
        """Get all active copy configurations"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT 
                        cp.id as copytrader_id,
                        cp.user_id,
                        lf.leader_address,
                        lf.is_active,
                        cc.sizing_mode,
                        cc.sizing_value,
                        cc.max_slippage_bps,
                        cc.max_leverage,
                        cc.notional_cap,
                        cc.pair_filters,
                        cc.tp_sl_policy
                    FROM copytrader_profiles cp
                    JOIN leader_follows lf ON cp.id = lf.copytrader_id
                    LEFT JOIN copy_configurations cc ON cp.id = cc.copytrader_id
                    WHERE cp.is_enabled = true 
                      AND lf.is_active = true
                """
                
                rows = await conn.fetch(query)
                
                return [
                    CopyConfiguration(
                        copytrader_id=row['copytrader_id'],
                        user_id=row['user_id'],
                        leader_address=row['leader_address'],
                        is_enabled=row['is_active'],
                        sizing_mode=row['sizing_mode'] or 'FIXED_NOTIONAL',
                        sizing_value=float(row['sizing_value'] or 100),
                        max_slippage_bps=row['max_slippage_bps'] or 100,
                        max_leverage=float(row['max_leverage'] or 50),
                        notional_cap=float(row['notional_cap'] or 10000),
                        pair_filters=row['pair_filters'] or {},
                        tp_sl_policy=row['tp_sl_policy'] or {}
                    )
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Error getting active copy configs: {e}")
            return []
    
    async def _check_leader_activity(self, config: CopyConfiguration):
        """Check if leader has new trades to copy"""
        try:
            leader_address = config.leader_address
            last_check_key = f"last_check:{leader_address}:{config.copytrader_id}"
            last_check = await self.redis.get(last_check_key)
            
            # Get new trades since last check
            new_trades = await self._get_new_leader_trades(
                leader_address, 
                since=last_check
            )
            
            for trade in new_trades:
                # Check if we should copy this trade
                if await self._should_copy_trade(config, trade):
                    copy_request = await self._create_copy_request(config, trade)
                    await self.execution_queue.put(copy_request)
            
            # Update last check timestamp
            await self.redis.set(last_check_key, datetime.utcnow().isoformat())
            
        except Exception as e:
            logger.error(f"Error checking leader activity for {config.leader_address}: {e}")
    
    async def _get_new_leader_trades(self, leader_address: str, since: Optional[str] = None) -> List[Dict]:
        """Get new trades from a leader since last check"""
        try:
            async with self.db_pool.acquire() as conn:
                if since:
                    since_dt = datetime.fromisoformat(since)
                    query = """
                        SELECT * FROM trade_events 
                        WHERE address = $1 AND timestamp > $2
                        ORDER BY timestamp ASC
                    """
                    rows = await conn.fetch(query, leader_address, since_dt)
                else:
                    # Get trades from last hour if no previous check
                    since_dt = datetime.utcnow() - timedelta(hours=1)
                    query = """
                        SELECT * FROM trade_events 
                        WHERE address = $1 AND timestamp > $2
                        ORDER BY timestamp ASC
                    """
                    rows = await conn.fetch(query, leader_address, since_dt)
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting new leader trades: {e}")
            return []
    
    async def _should_copy_trade(self, config: CopyConfiguration, trade: Dict) -> bool:
        """Determine if trade should be copied based on filters and conditions"""
        try:
            # Check if copytrader is enabled
            if not config.is_enabled:
                return False
            
            # Check pair filters
            pair_filters = config.pair_filters
            if pair_filters:
                allowed_pairs = pair_filters.get('allowed', [])
                blocked_pairs = pair_filters.get('blocked', [])
                
                if allowed_pairs and trade['pair_symbol'] not in allowed_pairs:
                    return False
                if blocked_pairs and trade['pair_symbol'] in blocked_pairs:
                    return False
            
            # Check market regime
            symbol = trade['pair_symbol']
            timing_signal = await self.market_intel.get_copy_timing_signal(symbol)
            
            if timing_signal.signal == 'red':
                logger.info(f"Skipping copy due to red regime for {symbol}")
                return False
            
            # Check leverage limits
            if trade.get('leverage', 1) > config.max_leverage:
                return False
            
            # Check position size limits
            trade_notional = trade['size'] * trade['price']
            if trade_notional > config.notional_cap:
                return False
            
            # Check if trade is recent (within last 5 minutes)
            trade_time = trade['timestamp']
            if (datetime.utcnow() - trade_time).total_seconds() > 300:  # 5 minutes
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking if should copy trade: {e}")
            return False
    
    async def _create_copy_request(self, config: CopyConfiguration, trade: Dict) -> CopyTradeRequest:
        """Create copy trade request with proper sizing"""
        try:
            # Calculate target size based on configuration
            original_notional = trade['size'] * trade['price']
            
            if config.sizing_mode == 'FIXED_NOTIONAL':
                target_notional = config.sizing_value
            elif config.sizing_mode == 'PCT_EQUITY':
                user_balance = await self._get_user_balance(config.user_id)
                target_notional = user_balance * (config.sizing_value / 100)
            else:
                target_notional = config.sizing_value  # Default to fixed
            
            # Calculate target size
            target_size = target_notional / trade['price']
            
            # Apply notional cap
            if target_notional > config.notional_cap:
                target_size = config.notional_cap / trade['price']
            
            return CopyTradeRequest(
                copytrader_id=config.copytrader_id,
                leader_address=config.leader_address,
                trade_data=trade,
                original_size=trade['size'],
                target_size=target_size,
                max_slippage_bps=config.max_slippage_bps,
                priority=1
            )
            
        except Exception as e:
            logger.error(f"Error creating copy request: {e}")
            raise
    
    async def _execute_copy_trade(self, request: CopyTradeRequest):
        """Execute a copy trade with slippage protection"""
        try:
            logger.info(f"Executing copy trade for copytrader {request.copytrader_id}")
            
            # Check slippage before execution
            current_price = await self._get_current_price(request.trade_data['pair_symbol'])
            price_impact = abs(current_price - request.trade_data['price']) / request.trade_data['price']
            
            if price_impact * 10000 > request.max_slippage_bps:
                logger.warning(f"Skipping copy trade due to slippage: {price_impact:.2%}")
                await self._record_copy_position(request, status='FAILED', reason='Slippage exceeded')
                return
            
            # Determine order type based on slippage
            if price_impact * 10000 > request.max_slippage_bps * 0.5:
                order_type = 'limit'
                limit_price = request.trade_data['price']
            else:
                order_type = 'market'
                limit_price = None
            
            # Execute trade via Avantis
            tx_hash = await self._execute_avantis_trade(
                user_id=await self._get_user_id(request.copytrader_id),
                pair=request.trade_data['pair_symbol'],
                is_long=request.trade_data['is_long'],
                size=request.target_size,
                leverage=min(request.trade_data['leverage'], await self._get_max_leverage(request.copytrader_id)),
                order_type=order_type,
                limit_price=limit_price
            )
            
            # Record successful copy
            await self._record_copy_position(
                request, 
                status='OPEN',
                tx_hash=tx_hash,
                executed_price=current_price,
                executed_size=request.target_size
            )
            
            # Send notification
            await self._send_copy_notification(request, tx_hash, 'success')
            
            logger.info(f"Successfully executed copy trade: {tx_hash}")
            
        except Exception as e:
            logger.error(f"Failed to execute copy trade: {e}")
            await self._record_copy_position(request, status='FAILED', reason=str(e))
            await self._send_copy_notification(request, None, 'failed', str(e))
    
    async def _get_current_price(self, pair_symbol: str) -> float:
        """Get current price for a trading pair"""
        try:
            # This would integrate with your price feed system
            # For now, return a mock price
            return 50000.0  # Mock price
            
        except Exception as e:
            logger.error(f"Error getting current price for {pair_symbol}: {e}")
            return 0.0
    
    async def _execute_avantis_trade(self, user_id: int, pair: str, is_long: bool, 
                                   size: float, leverage: float, order_type: str, 
                                   limit_price: Optional[float] = None) -> str:
        """Execute trade via Avantis Protocol"""
        try:
            # This would integrate with your Avantis trading system
            # For now, return a mock transaction hash
            mock_tx_hash = f"0x{''.join([f'{i:02x}' for i in range(32)])}"
            
            logger.info(f"Executing Avantis trade: {pair}, {size}, {leverage}x, {order_type}")
            
            return mock_tx_hash
            
        except Exception as e:
            logger.error(f"Error executing Avantis trade: {e}")
            raise
    
    async def _get_user_id(self, copytrader_id: int) -> int:
        """Get user ID from copytrader ID"""
        try:
            async with self.db_pool.acquire() as conn:
                query = "SELECT user_id FROM copytrader_profiles WHERE id = $1"
                result = await conn.fetchval(query, copytrader_id)
                return result
                
        except Exception as e:
            logger.error(f"Error getting user ID for copytrader {copytrader_id}: {e}")
            return 0
    
    async def _get_user_balance(self, user_id: int) -> float:
        """Get user's available balance"""
        try:
            # This would integrate with your balance system
            # For now, return a mock balance
            return 10000.0  # Mock balance
            
        except Exception as e:
            logger.error(f"Error getting user balance: {e}")
            return 0.0
    
    async def _get_max_leverage(self, copytrader_id: int) -> float:
        """Get maximum leverage for a copytrader"""
        try:
            async with self.db_pool.acquire() as conn:
                query = "SELECT max_leverage FROM copy_configurations WHERE copytrader_id = $1"
                result = await conn.fetchval(query, copytrader_id)
                return float(result) if result else 50.0
                
        except Exception as e:
            logger.error(f"Error getting max leverage for copytrader {copytrader_id}: {e}")
            return 50.0
    
    async def _record_copy_position(self, request: CopyTradeRequest, status: str, **kwargs):
        """Record copy trade in database"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    INSERT INTO copy_positions (
                        copytrader_id, leader_address, leader_trade_id, 
                        our_tx_hash, status, opened_at, executed_price, 
                        executed_size, failure_reason
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """
                
                await conn.execute(
                    query,
                    request.copytrader_id,
                    request.leader_address,
                    request.trade_data.get('trade_id'),
                    kwargs.get('tx_hash'),
                    status,
                    datetime.utcnow(),
                    kwargs.get('executed_price'),
                    kwargs.get('executed_size'),
                    kwargs.get('reason')
                )
                
        except Exception as e:
            logger.error(f"Error recording copy position: {e}")
    
    async def _send_copy_notification(self, request: CopyTradeRequest, tx_hash: Optional[str], 
                                    status: str, error: Optional[str] = None):
        """Send copy trade notification to user"""
        try:
            # This would integrate with your notification system
            # For now, just log the notification
            if status == 'success':
                logger.info(f"Copy trade successful: {tx_hash}")
            else:
                logger.warning(f"Copy trade failed: {error}")
                
        except Exception as e:
            logger.error(f"Error sending copy notification: {e}")
    
    async def _update_active_copytraders(self):
        """Update the set of active copytraders"""
        try:
            active_configs = await self._get_active_copy_configs()
            self.active_copytraders = {config.copytrader_id for config in active_configs}
            
        except Exception as e:
            logger.error(f"Error updating active copytraders: {e}")
    
    async def follow_trader(self, user_id: int, leader_address: str, config: Dict) -> Dict:
        """Start following a trader with given configuration"""
        try:
            # Validate configuration
            validation_result = await self._validate_copy_config(config)
            if not validation_result['valid']:
                return {'success': False, 'error': validation_result['error']}
            
            # Create or update copytrader profile
            copytrader_id = await self._create_or_update_copytrader(user_id, config)
            
            # Add leader follow relationship
            await self._add_leader_follow(copytrader_id, leader_address)
            
            # Start monitoring this leader
            self.active_copytraders.add(copytrader_id)
            
            return {
                'success': True, 
                'copytrader_id': copytrader_id,
                'message': f'Now following {leader_address[:10]}... trades will be copied according to your settings.'
            }
            
        except Exception as e:
            logger.error(f"Error following trader: {e}")
            return {'success': False, 'error': str(e)}
    
    async def unfollow_trader(self, user_id: int, leader_address: str) -> Dict:
        """Stop following a trader"""
        try:
            async with self.db_pool.acquire() as conn:
                # Deactivate follow relationship
                await conn.execute("""
                    UPDATE leader_follows 
                    SET is_active = false, stopped_at = $1
                    WHERE copytrader_id IN (
                        SELECT id FROM copytrader_profiles WHERE user_id = $2
                    ) AND leader_address = $3
                """, datetime.utcnow(), user_id, leader_address)
            
            return {
                'success': True,
                'message': f'Stopped following {leader_address[:10]}...'
            }
            
        except Exception as e:
            logger.error(f"Error unfollowing trader: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _validate_copy_config(self, config: Dict) -> Dict:
        """Validate copy trading configuration"""
        try:
            # Check required fields
            required_fields = ['sizing_mode', 'sizing_value']
            for field in required_fields:
                if field not in config:
                    return {'valid': False, 'error': f'Missing required field: {field}'}
            
            # Validate sizing mode
            if config['sizing_mode'] not in ['FIXED_NOTIONAL', 'PCT_EQUITY']:
                return {'valid': False, 'error': 'Invalid sizing mode'}
            
            # Validate sizing value
            if config['sizing_value'] <= 0:
                return {'valid': False, 'error': 'Sizing value must be positive'}
            
            if config['sizing_mode'] == 'PCT_EQUITY' and config['sizing_value'] > 100:
                return {'valid': False, 'error': 'Percentage sizing cannot exceed 100%'}
            
            return {'valid': True}
            
        except Exception as e:
            logger.error(f"Error validating copy config: {e}")
            return {'valid': False, 'error': str(e)}
    
    async def _create_or_update_copytrader(self, user_id: int, config: Dict) -> int:
        """Create or update copytrader profile"""
        try:
            async with self.db_pool.acquire() as conn:
                # Check if copytrader profile exists
                query = "SELECT id FROM copytrader_profiles WHERE user_id = $1 AND name = $2"
                existing_id = await conn.fetchval(query, user_id, config.get('name', 'Default'))
                
                if existing_id:
                    # Update existing profile
                    await conn.execute("""
                        UPDATE copytrader_profiles 
                        SET is_enabled = true, updated_at = $1
                        WHERE id = $2
                    """, datetime.utcnow(), existing_id)
                    
                    # Update configuration
                    await conn.execute("""
                        UPDATE copy_configurations 
                        SET sizing_mode = $1, sizing_value = $2, max_slippage_bps = $3,
                            max_leverage = $4, notional_cap = $5, pair_filters = $6,
                            tp_sl_policy = $7, updated_at = $8
                        WHERE copytrader_id = $9
                    """, 
                        config['sizing_mode'], config['sizing_value'], 
                        config.get('max_slippage_bps', 100),
                        config.get('max_leverage', 50), config.get('notional_cap', 10000),
                        config.get('pair_filters', {}), config.get('tp_sl_policy', {}),
                        datetime.utcnow(), existing_id
                    )
                    
                    return existing_id
                else:
                    # Create new profile
                    copytrader_id = await conn.fetchval("""
                        INSERT INTO copytrader_profiles (user_id, name, is_enabled)
                        VALUES ($1, $2, true)
                        RETURNING id
                    """, user_id, config.get('name', 'Default'))
                    
                    # Create configuration
                    await conn.execute("""
                        INSERT INTO copy_configurations (
                            copytrader_id, sizing_mode, sizing_value, max_slippage_bps,
                            max_leverage, notional_cap, pair_filters, tp_sl_policy
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                        copytrader_id, config['sizing_mode'], config['sizing_value'],
                        config.get('max_slippage_bps', 100), config.get('max_leverage', 50),
                        config.get('notional_cap', 10000), config.get('pair_filters', {}),
                        config.get('tp_sl_policy', {})
                    )
                    
                    return copytrader_id
                    
        except Exception as e:
            logger.error(f"Error creating/updating copytrader: {e}")
            raise
    
    async def _add_leader_follow(self, copytrader_id: int, leader_address: str):
        """Add leader follow relationship"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO leader_follows (copytrader_id, leader_address, is_active)
                    VALUES ($1, $2, true)
                    ON CONFLICT (copytrader_id, leader_address) DO UPDATE SET
                        is_active = true, started_at = $3, stopped_at = NULL
                """, copytrader_id, leader_address, datetime.utcnow())
                
        except Exception as e:
            logger.error(f"Error adding leader follow: {e}")
            raise
    
    async def get_copy_status(self, user_id: int) -> Dict:
        """Get comprehensive copy trading status for user"""
        try:
            async with self.db_pool.acquire() as conn:
                # Get copytrader profiles
                profiles = await conn.fetch("""
                    SELECT cp.*, cc.sizing_mode, cc.sizing_value, cc.max_leverage
                    FROM copytrader_profiles cp
                    LEFT JOIN copy_configurations cc ON cp.id = cc.copytrader_id
                    WHERE cp.user_id = $1
                """, user_id)
                
                # Get active follows
                follows = await conn.fetch("""
                    SELECT lf.leader_address, lf.started_at, lf.is_active,
                           ts.last_30d_volume_usd, ts.realized_pnl_clean_usd
                    FROM leader_follows lf
                    JOIN copytrader_profiles cp ON lf.copytrader_id = cp.id
                    LEFT JOIN trader_stats ts ON lf.leader_address = ts.address
                    WHERE cp.user_id = $1 AND lf.is_active = true
                """, user_id)
                
                # Get recent copy positions
                recent_positions = await conn.fetch("""
                    SELECT cp.leader_address, cp.status, cp.opened_at, cp.pnl_usd
                    FROM copy_positions cp
                    JOIN copytrader_profiles ctp ON cp.copytrader_id = ctp.id
                    WHERE ctp.user_id = $1
                    ORDER BY cp.opened_at DESC
                    LIMIT 20
                """, user_id)
            
            # Calculate performance attribution
            manual_pnl = await self._calculate_manual_pnl(user_id)
            copy_pnl = sum(pos['pnl_usd'] or 0 for pos in recent_positions if pos['pnl_usd'])
            
            return {
                'profiles': [dict(p) for p in profiles],
                'following': [dict(f) for f in follows],
                'recent_positions': [dict(p) for p in recent_positions],
                'performance': {
                    'manual_pnl': manual_pnl,
                    'copy_pnl': copy_pnl,
                    'total_pnl': manual_pnl + copy_pnl,
                    'copy_attribution': copy_pnl / (manual_pnl + copy_pnl) if (manual_pnl + copy_pnl) != 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting copy status: {e}")
            return {
                'profiles': [],
                'following': [],
                'recent_positions': [],
                'performance': {
                    'manual_pnl': 0,
                    'copy_pnl': 0,
                    'total_pnl': 0,
                    'copy_attribution': 0
                }
            }
    
    async def _calculate_manual_pnl(self, user_id: int) -> float:
        """Calculate manual trading PnL for user"""
        try:
            # This would integrate with your manual trading system
            # For now, return a mock value
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating manual PnL: {e}")
            return 0.0
    
    async def stop(self):
        """Stop the copy execution engine"""
        logger.info("Stopping copy execution engine...")
        self.running = False
        
        # Wait for queue to empty
        while not self.execution_queue.empty():
            await asyncio.sleep(0.1)
        
        # Cleanup resources if needed
