"""
Copy Execution Engine for Vanta Bot
Handles copy trading logic, monitoring leaders, and executing trades
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from functools import partial
from typing import Any, Dict, List, Optional

import asyncpg
import redis.asyncio as redis
from decimal import Decimal

from src.blockchain.wallet_manager import wallet_manager
from src.database import models
from src.services.price_service import price_service
from src.utils.resilience import CircuitBreaker, guarded_call

logger = logging.getLogger(__name__)

class CopyStatus(Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

@dataclass
class CopyTradeRequest:
    copytrader_id: int
    leader_address: str
    trade_data: Dict
    original_size: float
    target_size: float
    max_slippage_bps: int
    priority: int = 1
    request_id: str = None

@dataclass
class CopyConfiguration:
    copytrader_id: int
    user_id: int
    sizing_mode: str  # 'FIXED_NOTIONAL' or 'PCT_EQUITY'
    sizing_value: float
    max_slippage_bps: int
    max_leverage: float
    notional_cap: Optional[float]
    pair_filters: Dict
    is_enabled: bool

class CopyExecutor:
    """Main copy trading execution engine"""
    
    def __init__(self, db_pool: asyncpg.Pool, redis_client: redis.Redis,
                 avantis_client, market_intelligence, config):
        self.db_pool = db_pool
        self.redis = redis_client
        self.avantis = avantis_client
        self.market_intel = market_intelligence
        self.config = config

        if self.avantis is None:
            raise ValueError("Avantis client must be provided for live copy trading execution")
        
        # Execution state
        self.execution_queue = asyncio.Queue()
        self.active_copytraders = set()
        self.is_running = False

        # Rate limiting
        self.execution_limits = {}
        self._avantis_breaker = CircuitBreaker(fail_threshold=3, reset_after=60.0)
        
    async def start_execution(self):
        """Start copy trading execution system"""
        if self.is_running:
            logger.warning("Copy executor is already running")
            return
            
        self.is_running = True
        logger.info("Starting copy trading execution...")
        
        try:
            # Start execution worker
            execution_task = asyncio.create_task(self._execution_worker())
            
            # Start leader monitoring
            monitoring_task = asyncio.create_task(self._monitor_leaders())
            
            # Start position tracking
            tracking_task = asyncio.create_task(self._track_positions())
            
            # Wait for all tasks
            await asyncio.gather(execution_task, monitoring_task, tracking_task)
            
        except Exception as e:
            logger.error(f"Error in copy execution: {e}")
            self.is_running = False
            raise
    
    async def stop_execution(self):
        """Stop copy trading execution"""
        self.is_running = False
        logger.info("Stopped copy trading execution")
    
    async def _execution_worker(self):
        """Worker that processes copy trade requests"""
        logger.info("Starting copy execution worker...")
        
        while self.is_running:
            try:
                # Get next copy request with timeout
                try:
                    copy_request = await asyncio.wait_for(
                        self.execution_queue.get(), 
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Execute the copy trade
                await self._execute_copy_trade(copy_request)
                
            except Exception as e:
                logger.error(f"Error in copy execution worker: {e}")
                await asyncio.sleep(1)
    
    async def _monitor_leaders(self):
        """Monitor followed leaders for new trades"""
        logger.info("Starting leader monitoring...")
        
        while self.is_running:
            try:
                # Get all active copy configurations
                active_configs = await self._get_active_copy_configs()
                
                for config in active_configs:
                    await self._check_leader_activity(config)
                
                # Wait before next check
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in leader monitoring: {e}")
                await asyncio.sleep(10)
    
    async def _track_positions(self):
        """Track and update copy positions"""
        logger.info("Starting position tracking...")
        
        while self.is_running:
            try:
                # Update open positions
                await self._update_open_positions()
                
                # Wait before next update
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in position tracking: {e}")
                await asyncio.sleep(30)
    
    async def _get_active_copy_configs(self) -> List[CopyConfiguration]:
        """Get all active copy trading configurations"""
        try:
            acq = await self.db_pool.acquire()
            async with acq as conn:
                rows = await conn.fetch("""
                    SELECT 
                        cp.id as copytrader_id,
                        cp.user_id,
                        cp.is_enabled,
                        cc.sizing_mode,
                        cc.sizing_value,
                        cc.max_slippage_bps,
                        cc.max_leverage,
                        cc.notional_cap,
                        cc.pair_filters
                    FROM copytrader_profiles cp
                    JOIN copy_configurations cc ON cp.id = cc.copytrader_id
                    JOIN leader_follows lf ON cp.id = lf.copytrader_id
                    WHERE cp.is_enabled = true 
                      AND lf.is_active = true
                """)
                
                configs = []
                for row in rows:
                    config = CopyConfiguration(
                        copytrader_id=row['copytrader_id'],
                        user_id=row['user_id'],
                        sizing_mode=row['sizing_mode'],
                        sizing_value=float(row['sizing_value']),
                        max_slippage_bps=row['max_slippage_bps'],
                        max_leverage=float(row['max_leverage']),
                        notional_cap=float(row['notional_cap']) if row['notional_cap'] else None,
                        pair_filters=row['pair_filters'] or {},
                        is_enabled=row['is_enabled']
                    )
                    configs.append(config)
                
                return configs
                
        except Exception as e:
            logger.error(f"Error getting active copy configs: {e}")
            return []
    
    async def _check_leader_activity(self, config: CopyConfiguration):
        """Check if leader has new trades to copy"""
        try:
            # Get leaders for this copytrader
            leaders = await self._get_copytrader_leaders(config.copytrader_id)
            
            for leader_address in leaders:
                # Check for new trades since last check
                last_check_key = f"last_check:{config.copytrader_id}:{leader_address}"
                last_check = await self.redis.get(last_check_key)
                
                if last_check:
                    last_check_time = datetime.fromisoformat(last_check)
                else:
                    # First check - look at last hour
                    last_check_time = datetime.utcnow() - timedelta(hours=1)
                
                # Get new trades
                new_trades = await self._get_new_leader_trades(
                    leader_address, 
                    since=last_check_time
                )
                
                for trade in new_trades:
                    # Check if we should copy this trade
                    if await self._should_copy_trade(config, trade):
                        copy_request = await self._create_copy_request(config, trade, leader_address)
                        await self.execution_queue.put(copy_request)
                
                # Update last check timestamp
                await self.redis.set(last_check_key, datetime.utcnow().isoformat())
                
        except Exception as e:
            logger.error(f"Error checking leader activity: {e}")
    
    async def _get_copytrader_leaders(self, copytrader_id: int) -> List[str]:
        """Get leaders followed by a copytrader"""
        try:
            acq = await self.db_pool.acquire()
            async with acq as conn:
                rows = await conn.fetch("""
                    SELECT leader_address
                    FROM leader_follows
                    WHERE copytrader_id = $1 AND is_active = true
                """, copytrader_id)
                
                return [row['leader_address'] for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting copytrader leaders: {e}")
            return []
    
    async def _get_new_leader_trades(self, leader_address: str, since: datetime) -> List[Dict]:
        """Get new trades from a leader since given time"""
        try:
            acq = await self.db_pool.acquire()
            async with acq as conn:
                rows = await conn.fetch("""
                    SELECT pair, is_long, size, price, leverage, timestamp, 
                           block_number, tx_hash, event_type
                    FROM trade_events
                    WHERE address = $1 
                      AND timestamp > $2
                      AND event_type = 'OPENED'
                    ORDER BY timestamp ASC
                """, leader_address, since)
                
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
            if config.pair_filters:
                allowed_pairs = config.pair_filters.get('allowed', [])
                blocked_pairs = config.pair_filters.get('blocked', [])
                
                if allowed_pairs and trade['pair'] not in allowed_pairs:
                    return False
                if blocked_pairs and trade['pair'] in blocked_pairs:
                    return False
            
            # Check market regime
            symbol = self._get_symbol_from_pair(trade['pair'])
            timing_signal = await self.market_intel.get_copy_timing_signal(symbol)
            
            if timing_signal.signal == 'red':
                logger.info(f"Skipping copy due to red regime for {symbol}")
                return False
            
            # Check leverage limits
            if trade.get('leverage', 1) > config.max_leverage:
                logger.info(f"Skipping copy due to leverage limit: {trade.get('leverage', 1)} > {config.max_leverage}")
                return False
            
            # Check position size limits against our target notional, not leader's
            try:
                if config.sizing_mode == 'FIXED_NOTIONAL':
                    target_notional = float(config.sizing_value)
                elif config.sizing_mode == 'PCT_EQUITY':
                    user_balance = await self._get_user_balance(config.user_id)
                    target_notional = user_balance * (float(config.sizing_value) / 100.0)
                else:
                    logger.info(f"Unknown sizing mode {config.sizing_mode}; skipping copy")
                    return False
            except Exception as _e:
                logger.error(f"Error computing target notional: {_e}")
                return False

            if config.notional_cap and target_notional > float(config.notional_cap):
                logger.info(
                    f"Skipping copy due to notional cap: {target_notional} > {config.notional_cap}"
                )
                return False
            
            # Check rate limiting
            if not await self._check_rate_limit(config.copytrader_id, trade['pair']):
                logger.info(f"Skipping copy due to rate limit for copytrader {config.copytrader_id}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking if should copy trade: {e}")
            return False
    
    def _get_symbol_from_pair(self, pair: str) -> str:
        """Convert pair index to symbol name"""
        if '/' in pair or '-' in pair:
            return pair
        pair_mapping = {
            '0': 'BTC-USD',
            '1': 'ETH-USD',
            '2': 'SOL-USD',
            '3': 'AVAX-USD',
        }
        return pair_mapping.get(pair, 'BTC-USD')
    
    async def _check_rate_limit(self, copytrader_id: int, pair: str) -> bool:
        """Check if copytrader is within rate limits"""
        try:
            key = f"rate_limit:{copytrader_id}:{pair}"
            current_count = await self.redis.get(key)
            
            if current_count is None:
                await self.redis.setex(key, 3600, 1)  # 1 hour window
                return True
            
            if int(current_count) >= 10:  # Max 10 copies per hour per pair
                return False
            
            await self.redis.incr(key)
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # Allow on error
    
    async def _create_copy_request(self, config: CopyConfiguration, trade: Dict, leader_address: str) -> CopyTradeRequest:
        """Create copy trade request with proper sizing"""
        try:
            # Calculate target size based on configuration
            original_notional = trade['size'] * trade['price']
            
            if config.sizing_mode == 'FIXED_NOTIONAL':
                target_notional = float(config.sizing_value)
            elif config.sizing_mode == 'PCT_EQUITY':
                user_balance = await self._get_user_balance(config.user_id)
                target_notional = user_balance * (config.sizing_value / 100)
            else:
                raise ValueError(f"Unknown sizing mode: {config.sizing_mode}")
            
            # Calculate target size
            target_size = target_notional / trade['price']
            
            # Apply notional cap
            if config.notional_cap and target_notional > config.notional_cap:
                target_size = config.notional_cap / trade['price']
            
            return CopyTradeRequest(
                copytrader_id=config.copytrader_id,
                leader_address=leader_address,
                trade_data=trade,
                original_size=trade['size'],
                target_size=target_size,
                max_slippage_bps=config.max_slippage_bps,
                request_id=str(uuid.uuid4())
            )
            
        except Exception as e:
            logger.error(f"Error creating copy request: {e}")
            raise
    
    async def _get_user_balance(self, user_id: int) -> float:
        """Estimate the user's available balance for copy trading."""
        balance = 0.0

        try:
            acq = await self.db_pool.acquire()
            async with acq as conn:
                user_row = await conn.fetchrow(
                    "SELECT wallet_address FROM users WHERE id = $1",
                    user_id,
                )
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Error loading user {user_id} for balance lookup: {exc}")
            user_row = None

        wallet_address = user_row["wallet_address"] if user_row else None

        if wallet_address and wallet_manager:
            try:
                wallet_info = wallet_manager.get_wallet_info(wallet_address)
                balance = float(wallet_info.get("usdc_balance", 0.0))
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Wallet balance lookup failed for %s: %s", wallet_address, exc
                )

        # Add notional from open manual positions as conservative estimate
        try:
            acq = await self.db_pool.acquire()
            async with acq as conn:
                rows = await conn.fetch(
                    """
                    SELECT size
                    FROM positions
                    WHERE user_id = $1 AND status = 'OPEN'
                    """,
                    user_id,
                )
            balance += sum(float(row["size"] or 0.0) for row in rows)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to aggregate open positions for user %s: %s", user_id, exc)

        return balance if balance > 0 else 1000.0
    
    async def _execute_copy_trade(self, request: CopyTradeRequest):
        """Execute a copy trade with slippage protection"""
        try:
            logger.info(f"Executing copy trade: {request.request_id}")
            
            # Check slippage before execution
            current_price = await self._get_current_price(request.trade_data['pair'])
            price_impact = abs(current_price - request.trade_data['price']) / request.trade_data['price']
            
            if price_impact * 10000 > request.max_slippage_bps:
                logger.warning(f"Skipping copy trade due to slippage: {price_impact:.2%}")
                await self._record_copy_position(request, CopyStatus.FAILED, reason='Slippage exceeded')
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
                pair=request.trade_data['pair'],
                is_long=request.trade_data['is_long'],
                size=request.target_size,
                leverage=min(request.trade_data['leverage'], await self._get_max_leverage(request.copytrader_id)),
                order_type=order_type,
                limit_price=limit_price
            )
            
            # Record successful copy
            await self._record_copy_position(
                request, 
                CopyStatus.OPEN,
                tx_hash=tx_hash,
                executed_price=current_price,
                executed_size=request.target_size
            )
            
            # Send notification
            await self._send_copy_notification(request, tx_hash, 'success')
            
            logger.info(f"Successfully executed copy trade: {request.request_id}")
            
        except Exception as e:
            logger.error(f"Failed to execute copy trade {request.request_id}: {e}")
            await self._record_copy_position(request, CopyStatus.FAILED, reason=str(e))
            await self._send_copy_notification(request, None, 'failed', str(e))
    
    async def _get_current_price(self, pair: str) -> float:
        """Get current market price for a pair"""
        try:
            symbol = pair if "/" in pair or "-" in pair else self._get_symbol_from_pair(pair)
            asset = symbol.split("/")[0] if "/" in symbol else symbol.split("-")[0]

            price = price_service.get_price(asset)
            if not price or price <= 0:
                await price_service.fetch_prices()
                price = price_service.get_price(asset)

            if not price or price <= 0:
                raise ValueError(f"Price unavailable for {asset}")

            return float(price)

        except Exception as e:  # noqa: BLE001
            logger.error(f"Error getting current price for {pair}: {e}")
            raise
    
    async def _execute_avantis_trade(self, user_id: int, pair: str, is_long: bool, 
                                   size: float, leverage: int, order_type: str, 
                                   limit_price: Optional[float]) -> str:
        """Execute trade on Avantis Protocol"""
        try:
            if not self.avantis:
                raise RuntimeError("Avantis client not configured")

            acq = await self.db_pool.acquire()
            async with acq as conn:
                credentials = await conn.fetchrow(
                    "SELECT wallet_address, encrypted_private_key FROM users WHERE id = $1",
                    user_id,
                )

            if not credentials or not credentials["wallet_address"] or not credentials["encrypted_private_key"]:
                raise ValueError("User wallet credentials are not configured for copy trading")

            wallet_address = credentials["wallet_address"]
            private_key = wallet_manager.decrypt_private_key(credentials["encrypted_private_key"])

            symbol = pair if "/" in pair or "-" in pair else self._get_symbol_from_pair(pair)

            if order_type != "market":
                logger.warning("Limit/advanced orders not yet supported in copy executor; executing as market trade")

            async def _open_trade() -> str:
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(
                    None,
                    partial(
                        self.avantis.open_position,
                        wallet_address,
                        private_key,
                        symbol,
                        size,
                        is_long,
                        int(leverage),
                    ),
                )

            tx_hash = await guarded_call(
                self._avantis_breaker,
                _open_trade,
                timeout_s=30.0,
                retries=2,
            )

            logger.info("Executed Avantis trade", extra={"tx_hash": tx_hash, "user_id": user_id, "pair": symbol})
            return tx_hash

        except Exception as e:  # noqa: BLE001
            logger.error(f"Error executing Avantis trade: {e}")
            raise
    
    async def _get_user_id(self, copytrader_id: int) -> int:
        """Get user ID for a copytrader"""
        try:
            acq = await self.db_pool.acquire()
            async with acq as conn:
                row = await conn.fetchrow("""
                    SELECT user_id FROM copytrader_profiles WHERE id = $1
                """, copytrader_id)
                
                return row['user_id'] if row else 0
                
        except Exception as e:
            logger.error(f"Error getting user ID: {e}")
            return 0
    
    async def _get_max_leverage(self, copytrader_id: int) -> float:
        """Get maximum leverage for a copytrader"""
        try:
            acq = await self.db_pool.acquire()
            async with acq as conn:
                row = await conn.fetchrow("""
                    SELECT max_leverage FROM copy_configurations WHERE copytrader_id = $1
                """, copytrader_id)
                
                return float(row['max_leverage']) if row else 50.0
                
        except Exception as e:
            logger.error(f"Error getting max leverage: {e}")
            return 50.0
    
    async def _record_copy_position(self, request: CopyTradeRequest, status: CopyStatus, **kwargs):
        """Record copy trade in database"""
        try:
            acq = await self.db_pool.acquire()
            async with acq as conn:
                await conn.execute("""
                    INSERT INTO copy_positions (
                        copytrader_id, leader_address, leader_trade_id, 
                        our_tx_hash, status, opened_at, executed_price, executed_size
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, 
                    request.copytrader_id,
                    request.leader_address,
                    request.request_id,
                    kwargs.get('tx_hash'),
                    status.value,
                    datetime.utcnow(),
                    kwargs.get('executed_price'),
                    kwargs.get('executed_size')
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
                logger.info(f"Copy trade success notification for user {request.copytrader_id}: {tx_hash}")
            else:
                logger.warning(f"Copy trade failure notification for user {request.copytrader_id}: {error}")
                
        except Exception as e:
            logger.error(f"Error sending copy notification: {e}")
    
    async def _update_open_positions(self):
        """Update status of open copy positions"""
        try:
            acq = await self.db_pool.acquire()
            async with acq as conn:
                # Get open positions
                rows = await conn.fetch("""
                    SELECT id, our_tx_hash, leader_address
                    FROM copy_positions
                    WHERE status = 'OPEN'
                """)
                
                for row in rows:
                    # Check if position is still open on Avantis
                    is_still_open = await self._check_position_status(row['our_tx_hash'])
                    
                    if not is_still_open:
                        # Position was closed
                        await conn.execute("""
                            UPDATE copy_positions
                            SET status = 'CLOSED', closed_at = $1
                            WHERE id = $2
                        """, datetime.utcnow(), row['id'])
                        
                        logger.info(f"Updated position {row['id']} to CLOSED")
                
        except Exception as e:
            logger.error(f"Error updating open positions: {e}")
    
    async def _check_position_status(self, tx_hash: str) -> bool:
        """Check if position is still open on Avantis"""
        try:
            acq = await self.db_pool.acquire()
            async with acq as conn:
                record = await conn.fetchrow(
                    """
                    SELECT event_type
                    FROM trade_events
                    WHERE tx_hash = $1
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    tx_hash,
                )

            if not record:
                return True

            return record["event_type"] != "CLOSED"

        except Exception as e:  # noqa: BLE001
            logger.error(f"Error checking position status: {e}")
            return True
    
    # Public API methods
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
            acq = await self.db_pool.acquire()
            async with acq as conn:
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
    
    async def get_copy_status(self, user_id: int) -> Dict:
        """Get comprehensive copy trading status for user"""
        try:
            acq = await self.db_pool.acquire()
            async with acq as conn:
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
                    SELECT cp.leader_address, cp.status, cp.opened_at, cp.closed_at, cp.pnl
                    FROM copy_positions cp
                    JOIN copytrader_profiles ctp ON cp.copytrader_id = ctp.id
                    WHERE ctp.user_id = $1
                    ORDER BY cp.opened_at DESC
                    LIMIT 20
                """, user_id)

                closed_positions = await conn.fetch("""
                    SELECT cp.pnl, cp.size, cp.entry_price
                    FROM copy_positions cp
                    JOIN copytrader_profiles ctp ON cp.copytrader_id = ctp.id
                    WHERE ctp.user_id = $1 AND cp.status = 'CLOSED'
                """, user_id)
            
            # Calculate performance attribution
            manual_pnl = await self._calculate_manual_pnl(user_id)
            closed_dicts = [dict(p) for p in closed_positions]
            copy_pnl = sum(float(p.get('pnl') or 0) for p in closed_dicts)
            total_volume = sum(
                float((p.get('executed_size') or p.get('size') or 0) * (p.get('executed_price') or p.get('entry_price') or 0))
                for p in closed_dicts
            )
            open_positions_dicts = [dict(p) for p in recent_positions if p['status'] == 'OPEN']
            total_volume += sum(
                float((p.get('executed_size') or 0) * (p.get('executed_price') or 0))
                for p in open_positions_dicts
            )

            wins = sum(1 for p in closed_dicts if (p.get('pnl') or 0) > 0)
            losses = sum(1 for p in closed_dicts if (p.get('pnl') or 0) < 0)
            win_rate = (wins / (wins + losses) * 100.0) if (wins + losses) else 0.0
            
            return {
                'profiles': [dict(p) for p in profiles],
                'following': [dict(f) for f in follows],
                'recent_positions': [dict(p) for p in recent_positions],
                'performance': {
                    'manual_pnl': manual_pnl,
                    'copy_pnl': copy_pnl,
                    'total_pnl': manual_pnl + copy_pnl,
                    'copy_attribution': copy_pnl / (manual_pnl + copy_pnl) if (manual_pnl + copy_pnl) != 0 else 0,
                    'total_volume': total_volume,
                    'win_rate': win_rate,
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
                    'copy_attribution': 0,
                    'total_volume': 0,
                    'win_rate': 0,
                }
            }
    
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
            if config['sizing_mode'] == 'FIXED_NOTIONAL' and config['sizing_value'] <= 0:
                return {'valid': False, 'error': 'Fixed notional must be positive'}
            
            # For safety and tests, cap PCT_EQUITY to 25%
            if config['sizing_mode'] == 'PCT_EQUITY' and (config['sizing_value'] <= 0 or config['sizing_value'] > 25):
                return {'valid': False, 'error': 'Percentage must be between 0 and 25'}
            
            return {'valid': True}
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    async def _create_or_update_copytrader(self, user_id: int, config: Dict) -> int:
        """Create or update copytrader profile"""
        try:
            acq = await self.db_pool.acquire()
            async with acq as conn:
                # Check if user already has a copytrader profile
                existing = await conn.fetchrow("""
                    SELECT id FROM copytrader_profiles WHERE user_id = $1
                """, user_id)
                
                if existing:
                    copytrader_id = existing['id']
                    
                    # Update configuration
                    await conn.execute("""
                        UPDATE copy_configurations
                        SET sizing_mode = $2, sizing_value = $3, 
                            max_slippage_bps = $4, max_leverage = $5,
                            notional_cap = $6, pair_filters = $7,
                            updated_at = $8
                        WHERE copytrader_id = $1
                    """, 
                        copytrader_id,
                        config['sizing_mode'],
                        config['sizing_value'],
                        config.get('max_slippage_bps', 100),
                        config.get('max_leverage', 50),
                        config.get('notional_cap'),
                        config.get('pair_filters', {}),
                        datetime.utcnow()
                    )
                else:
                    # Create new copytrader profile
                    copytrader_id = await conn.fetchval("""
                        INSERT INTO copytrader_profiles (user_id, name, is_enabled)
                        VALUES ($1, $2, true)
                        RETURNING id
                    """, user_id, config.get('name', 'Default Copytrader'))
                    
                    # Create configuration
                    await conn.execute("""
                        INSERT INTO copy_configurations (
                            copytrader_id, sizing_mode, sizing_value,
                            max_slippage_bps, max_leverage, notional_cap, pair_filters
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                        copytrader_id,
                        config['sizing_mode'],
                        config['sizing_value'],
                        config.get('max_slippage_bps', 100),
                        config.get('max_leverage', 50),
                        config.get('notional_cap'),
                        config.get('pair_filters', {})
                    )
                
                return copytrader_id
                
        except Exception as e:
            logger.error(f"Error creating/updating copytrader: {e}")
            raise
    
    async def _add_leader_follow(self, copytrader_id: int, leader_address: str):
        """Add leader follow relationship"""
        try:
            acq = await self.db_pool.acquire()
            async with acq as conn:
                await conn.execute("""
                    INSERT INTO leader_follows (copytrader_id, leader_address, is_active)
                    VALUES ($1, $2, true)
                    ON CONFLICT (copytrader_id, leader_address) 
                    DO UPDATE SET is_active = true, started_at = $3
                """, copytrader_id, leader_address, datetime.utcnow())
                
        except Exception as e:
            logger.error(f"Error adding leader follow: {e}")
            raise
    
    async def _calculate_manual_pnl(self, user_id: int) -> float:
        """Calculate manual trading PnL for user"""
        try:
            acq = await self.db_pool.acquire()
            async with acq as conn:
                row = await conn.fetchrow(
                    """
                    SELECT COALESCE(SUM(p.pnl), 0) AS manual_pnl
                    FROM positions p
                    WHERE p.user_id = $1 AND p.status = 'CLOSED'
                    """,
                    user_id,
                )
            return float(row["manual_pnl"] or 0.0)

        except Exception as e:  # noqa: BLE001
            logger.error(f"Error calculating manual PnL: {e}")
            return 0.0
