# src/services/copy_trading/copy_executor.py
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Dict, Any, List
import os
import math
import time
import json
from sqlalchemy.orm import Session
from sqlalchemy import text

from loguru import logger

MAX_RETRIES = 3

@dataclass
class CopyConfig:
    sizing_mode: str   # "FIXED_NOTIONAL" or "PCT_EQUITY"
    sizing_value: Decimal
    max_slippage_bps: int
    max_leverage: Decimal
    notional_cap: Decimal
    pair_filters: Optional[dict] = None

class CopyExecutor:
    def __init__(self, account_provider, price_provider, portfolio_provider, audit_sink, session_factory):
        """
        account_provider: wallet/signing context
        price_provider: get_best_price(pair), estimate_impact(pair, notional)
        portfolio_provider: get_equity(), get_leverage(), balances
        audit_sink: persist CopyPositions/audit logs
        session_factory: database session factory
        """
        self.account = account_provider
        self.price = price_provider
        self.portfolio = portfolio_provider
        self.audit = audit_sink
        self.session_factory = session_factory

    async def follow(self, user_id: int, leader_address: str, cfg: CopyConfig) -> bool:
        """Start following a leader with the given configuration"""
        try:
            with self.session_factory() as session:
                # Check if already following
                existing = session.execute(
                    text("SELECT id FROM copy_configurations WHERE user_id = :user_id AND leader_address = :leader_address"),
                    {"user_id": user_id, "leader_address": leader_address.lower()}
                ).fetchone()
                
                if existing:
                    # Update existing configuration
                    session.execute(
                        text("""
                            UPDATE copy_configurations 
                            SET sizing_mode = :sizing_mode, sizing_value = :sizing_value,
                                max_slippage_bps = :max_slippage_bps, max_leverage = :max_leverage,
                                notional_cap = :notional_cap, pair_filters = :pair_filters,
                                is_active = true, updated_at = :updated_at
                            WHERE user_id = :user_id AND leader_address = :leader_address
                        """),
                        {
                            "user_id": user_id,
                            "leader_address": leader_address.lower(),
                            "sizing_mode": cfg.sizing_mode,
                            "sizing_value": str(cfg.sizing_value),
                            "max_slippage_bps": cfg.max_slippage_bps,
                            "max_leverage": str(cfg.max_leverage),
                            "notional_cap": str(cfg.notional_cap),
                            "pair_filters": json.dumps(cfg.pair_filters) if cfg.pair_filters else None,
                            "updated_at": int(time.time())
                        }
                    )
                    logger.info("Updated copy configuration for user={} leader={}", user_id, leader_address)
                else:
                    # Create new configuration
                    session.execute(
                        text("""
                            INSERT INTO copy_configurations 
                            (user_id, leader_address, sizing_mode, sizing_value, max_slippage_bps,
                             max_leverage, notional_cap, pair_filters, is_active, created_at, updated_at)
                            VALUES (:user_id, :leader_address, :sizing_mode, :sizing_value, :max_slippage_bps,
                                    :max_leverage, :notional_cap, :pair_filters, true, :created_at, :updated_at)
                        """),
                        {
                            "user_id": user_id,
                            "leader_address": leader_address.lower(),
                            "sizing_mode": cfg.sizing_mode,
                            "sizing_value": str(cfg.sizing_value),
                            "max_slippage_bps": cfg.max_slippage_bps,
                            "max_leverage": str(cfg.max_leverage),
                            "notional_cap": str(cfg.notional_cap),
                            "pair_filters": json.dumps(cfg.pair_filters) if cfg.pair_filters else None,
                            "created_at": int(time.time()),
                            "updated_at": int(time.time())
                        }
                    )
                    logger.info("Created copy configuration for user={} leader={}", user_id, leader_address)
                
                session.commit()
                return True
                
        except Exception as e:
            logger.error("Failed to follow leader: {}", e)
            return False

    async def unfollow(self, user_id: int, leader_address: str) -> bool:
        """Stop following a leader"""
        try:
            with self.session_factory() as session:
                # Deactivate configuration
                result = session.execute(
                    text("""
                        UPDATE copy_configurations 
                        SET is_active = false, updated_at = :updated_at
                        WHERE user_id = :user_id AND leader_address = :leader_address
                    """),
                    {
                        "user_id": user_id,
                        "leader_address": leader_address.lower(),
                        "updated_at": int(time.time())
                    }
                )
                
                session.commit()
                
                if result.rowcount > 0:
                    logger.info("Unfollowed leader: user={} leader={}", user_id, leader_address)
                    return True
                else:
                    logger.warning("No active follow found: user={} leader={}", user_id, leader_address)
                    return False
                    
        except Exception as e:
            logger.error("Failed to unfollow leader: {}", e)
            return False

    async def status(self, user_id: int) -> Dict[str, Any]:
        """Get copy trading status for a user"""
        try:
            with self.session_factory() as session:
                # Get active configurations
                configs = session.execute(
                    text("""
                        SELECT leader_address, sizing_mode, sizing_value, max_slippage_bps,
                               max_leverage, notional_cap, created_at
                        FROM copy_configurations
                        WHERE user_id = :user_id AND is_active = true
                    """),
                    {"user_id": user_id}
                ).fetchall()
                
                # Get open copy positions
                positions = session.execute(
                    text("""
                        SELECT leader_address, pair, is_long, size, entry_price,
                               opened_at, pnl, status
                        FROM copy_positions
                        WHERE user_id = :user_id AND status = 'OPEN'
                    """),
                    {"user_id": user_id}
                ).fetchall()
                
                # Calculate 30-day PnL
                pnl_result = session.execute(
                    text("""
                        SELECT SUM(pnl) as total_pnl
                        FROM copy_positions
                        WHERE user_id = :user_id 
                          AND status = 'CLOSED'
                          AND opened_at >= :thirty_days_ago
                    """),
                    {
                        "user_id": user_id,
                        "thirty_days_ago": int(time.time()) - (30 * 24 * 60 * 60)
                    }
                ).fetchone()
                
                total_pnl = float(pnl_result.total_pnl or 0)
                
                return {
                    "leaders": len(configs),
                    "active_configs": [dict(c._mapping) for c in configs],
                    "open_positions": len(positions),
                    "positions": [dict(p._mapping) for p in positions],
                    "copy_pnl_30d": f"{total_pnl:.2f}",
                    "total_volume": 0.0,  # TODO: Calculate from positions
                    "win_rate": 0.0  # TODO: Calculate from positions
                }
                
        except Exception as e:
            logger.error("Failed to get copy status: {}", e)
            return {
                "leaders": 0,
                "active_configs": [],
                "open_positions": 0,
                "positions": [],
                "copy_pnl_30d": "0.00",
                "total_volume": 0.0,
                "win_rate": 0.0
            }

    async def mirror_open(self, user_id: int, leader_trade: Dict[str, Any]) -> bool:
        """Mirror a leader's open trade"""
        pair = leader_trade["pair"]
        leader_address = leader_trade["address"]
        
        try:
            with self.session_factory() as session:
                # Get user's copy configuration for this leader
                config_result = session.execute(
                    text("""
                        SELECT sizing_mode, sizing_value, max_slippage_bps, max_leverage,
                               notional_cap, pair_filters
                        FROM copy_configurations
                        WHERE user_id = :user_id AND leader_address = :leader_address AND is_active = true
                    """),
                    {"user_id": user_id, "leader_address": leader_address.lower()}
                ).fetchone()
                
                if not config_result:
                    logger.debug("No active copy configuration for user={} leader={}", user_id, leader_address)
                    return False
                
                # Parse configuration
                cfg = CopyConfig(
                    sizing_mode=config_result.sizing_mode,
                    sizing_value=Decimal(config_result.sizing_value),
                    max_slippage_bps=config_result.max_slippage_bps,
                    max_leverage=Decimal(config_result.max_leverage),
                    notional_cap=Decimal(config_result.notional_cap),
                    pair_filters=json.loads(config_result.pair_filters) if config_result.pair_filters else None
                )
                
                # Check pair filters
                if cfg.pair_filters and not self._pair_allowed(pair, cfg.pair_filters):
                    logger.debug("Pair {} not allowed by filters for user={}", pair, user_id)
                    return False
                
                # Calculate position size
                equity = await self.portfolio.get_equity(user_id)
                if equity <= 0:
                    logger.warning("User {} has no equity for copy trading", user_id)
                    return False
                
                if cfg.sizing_mode == "FIXED_NOTIONAL":
                    notional = cfg.sizing_value
                else:  # PCT_EQUITY
                    notional = Decimal(equity) * (cfg.sizing_value / Decimal(100))
                
                notional = min(notional, cfg.notional_cap)
                
                # Get best price and estimate impact
                best_px = await self.price.get_best_price(pair)
                impact_bps = await self.price.estimate_impact(pair, notional)
                
                # Determine order type and limit price
                if impact_bps > cfg.max_slippage_bps:
                    # Use limit order at allowed slippage
                    slippage_multiplier = Decimal(cfg.max_slippage_bps) / Decimal(10000)
                    if leader_trade["is_long"]:
                        limit_px = best_px * (Decimal(1) + slippage_multiplier)
                    else:
                        limit_px = best_px * (Decimal(1) - slippage_multiplier)
                    order_type = "LIMIT"
                else:
                    limit_px = None
                    order_type = "MARKET"
                
                # Check leverage limits
                if not await self._check_leverage(user_id, notional, cfg.max_leverage):
                    logger.warning("Leverage cap exceeded for user={}; skipping mirror", user_id)
                    return False
                
                # Execute trade with retries
                for attempt in range(1, MAX_RETRIES + 1):
                    try:
                        tx_hash = await self._execute_trade(
                            user_id=user_id,
                            pair=pair,
                            is_long=leader_trade["is_long"],
                            notional=notional,
                            order_type=order_type,
                            limit_px=limit_px
                        )
                        
                        # Record copy position
                        copy_ratio = notional / Decimal(leader_trade["size"]) if leader_trade["size"] > 0 else Decimal(0)
                        
                        session.execute(
                            text("""
                                INSERT INTO copy_positions
                                (user_id, leader_address, leader_tx_hash, copy_tx_hash, pair, is_long,
                                 size, entry_price, copy_ratio, opened_at, pnl, status)
                                VALUES (:user_id, :leader_address, :leader_tx_hash, :copy_tx_hash, :pair, :is_long,
                                        :size, :entry_price, :copy_ratio, :opened_at, 0, 'OPEN')
                            """),
                            {
                                "user_id": user_id,
                                "leader_address": leader_address.lower(),
                                "leader_tx_hash": leader_trade["tx_hash"],
                                "copy_tx_hash": tx_hash,
                                "pair": pair,
                                "is_long": leader_trade["is_long"],
                                "size": str(notional),
                                "entry_price": str(best_px),
                                "copy_ratio": str(copy_ratio),
                                "opened_at": int(time.time())
                            }
                        )
                        
                        session.commit()
                        
                        logger.info("Mirrored open trade: user={} leader={} pair={} notional={}", 
                                   user_id, leader_address, pair, notional)
                        return True
                        
                    except Exception as e:
                        logger.exception("mirror_open attempt {} failed: {}", attempt, e)
                        if attempt == MAX_RETRIES:
                            raise
                        await asyncio.sleep(1)  # Brief delay before retry
                        
        except Exception as e:
            logger.error("Failed to mirror open trade: {}", e)
            return False

    async def mirror_close(self, user_id: int, leader_trade: Dict[str, Any]) -> bool:
        """Mirror a leader's close trade"""
        pair = leader_trade["pair"]
        leader_address = leader_trade["address"]
        
        try:
            with self.session_factory() as session:
                # Find open copy positions for this leader/pair
                positions = session.execute(
                    text("""
                        SELECT id, size, entry_price, copy_tx_hash
                        FROM copy_positions
                        WHERE user_id = :user_id AND leader_address = :leader_address 
                          AND pair = :pair AND status = 'OPEN'
                        ORDER BY opened_at ASC
                    """),
                    {
                        "user_id": user_id,
                        "leader_address": leader_address.lower(),
                        "pair": pair
                    }
                ).fetchall()
                
                if not positions:
                    logger.debug("No open copy positions to close for user={} leader={} pair={}", 
                                user_id, leader_address, pair)
                    return False
                
                # Close positions proportionally
                for position in positions:
                    try:
                        # Execute close trade
                        close_tx_hash = await self._execute_trade(
                            user_id=user_id,
                            pair=pair,
                            is_long=not leader_trade["is_long"],  # Opposite direction to close
                            notional=Decimal(position.size),
                            order_type="MARKET",
                            limit_px=None
                        )
                        
                        # Calculate PnL (simplified - in reality you'd get the actual close price)
                        entry_price = Decimal(position.entry_price)
                        close_price = Decimal(leader_trade["price"])  # Use leader's close price as proxy
                        pnl = (close_price - entry_price) * Decimal(position.size)
                        
                        # Update position
                        session.execute(
                            text("""
                                UPDATE copy_positions
                                SET closed_at = :closed_at, pnl = :pnl, status = 'CLOSED'
                                WHERE id = :position_id
                            """),
                            {
                                "position_id": position.id,
                                "closed_at": int(time.time()),
                                "pnl": str(pnl)
                            }
                        )
                        
                        logger.info("Mirrored close trade: user={} leader={} pair={} pnl={}", 
                                   user_id, leader_address, pair, pnl)
                        
                    except Exception as e:
                        logger.exception("Failed to close copy position: {}", e)
                        continue
                
                session.commit()
                return True
                
        except Exception as e:
            logger.error("Failed to mirror close trade: {}", e)
            return False

    async def _execute_trade(self, user_id: int, pair: str, is_long: bool, notional: Decimal, 
                           order_type: str, limit_px: Optional[Decimal]) -> str:
        """
        Execute a trade on the Avantis protocol.
        TODO: Bind to actual Avantis trade operation (Trader SDK / client).
        Keep a single choke-point so you can swap sim/mock/live easily.
        """
        # Mock implementation - replace with actual Avantis SDK call
        logger.info("EXECUTE {} {} notional={} limit_px={} order_type={}", 
                   pair, "LONG" if is_long else "SHORT", notional, limit_px, order_type)
        
        # Simulate transaction hash
        import hashlib
        tx_data = f"{user_id}_{pair}_{is_long}_{notional}_{limit_px}_{time.time()}"
        tx_hash = "0x" + hashlib.sha256(tx_data.encode()).hexdigest()[:64]
        
        # TODO: Replace with actual Avantis SDK call:
        # return await self.avantis_client.open_position(
        #     wallet_address=user_wallet,
        #     private_key=user_private_key,
        #     asset=pair,
        #     size=float(notional),
        #     is_long=is_long,
        #     leverage=leverage
        # )
        
        return tx_hash
    
    async def _check_leverage(self, user_id: int, new_notional: Decimal, max_lev: Decimal) -> bool:
        """Check if adding this position would exceed leverage limits"""
        try:
            current_leverage = await self.portfolio.get_leverage(user_id)
            return Decimal(current_leverage) <= max_lev
        except Exception as e:
            logger.error("Failed to check leverage: {}", e)
            return False

    def _pair_allowed(self, pair: str, filters: dict) -> bool:
        """Check if a trading pair is allowed by the filters"""
        allow = filters.get("allow", [])
        deny = filters.get("deny", [])
        
        if allow and pair not in allow:
            return False
        if pair in deny:
            return False
        return True
