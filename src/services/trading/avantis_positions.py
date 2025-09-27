"""
Avantis Positions - Position Management Utilities

This module provides convenience wrappers for position management using the Avantis Trader SDK.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from avantis_trader_sdk import TradeExtendedResponse, PendingLimitOrderExtendedResponse

from src.integrations.avantis.sdk_client import get_sdk_client
from src.services.trading.avantis_executor import get_executor, TradeResult

logger = logging.getLogger(__name__)


@dataclass
class PositionSummary:
    """Position summary data structure"""
    pair: str
    is_long: bool
    size: float
    entry_price: float
    current_price: float
    pnl: float
    pnl_percent: float
    collateral: float
    leverage: float
    trade_index: int
    pair_index: int


@dataclass
class CloseResult:
    """Position close result"""
    success: bool
    tx_hash: Optional[str] = None
    closed_collateral: Optional[float] = None
    error: Optional[str] = None


class AvantisPositions:
    """
    Position management utilities using Avantis Trader SDK
    
    Provides methods for getting trades, closing positions, and position analysis.
    """
    
    def __init__(self):
        """Initialize the positions manager"""
        self._sdk_client = None
        self._executor = None
        
    async def _get_sdk_client(self):
        """Get or initialize the SDK client"""
        if self._sdk_client is None:
            sdk_client = get_sdk_client()
            self._sdk_client = sdk_client.get_client()
        return self._sdk_client
    
    async def _get_executor(self):
        """Get or initialize the executor"""
        if self._executor is None:
            self._executor = get_executor()
        return self._executor
    
    async def get_trades(self, trader_address: str) -> Tuple[List[TradeExtendedResponse], List[PendingLimitOrderExtendedResponse]]:
        """
        Get all trades and pending limit orders for a trader
        
        Args:
            trader_address: Trader wallet address
            
        Returns:
            Tuple[List[TradeExtendedResponse], List[PendingLimitOrderExtendedResponse]]: 
                Active trades and pending limit orders
        """
        try:
            client = await self._get_sdk_client()
            
            # Get trades using SDK
            trades, pending_orders = await client.trade.get_trades(trader_address)
            
            logger.info(f"Retrieved {len(trades)} active trades and {len(pending_orders)} pending orders for {trader_address}")
            
            return trades, pending_orders
            
        except Exception as e:
            logger.error(f"❌ Error getting trades for {trader_address}: {e}")
            return [], []
    
    async def get_position_summary(self, trade: TradeExtendedResponse, 
                                  current_price: Optional[float] = None) -> PositionSummary:
        """
        Get a summary of a position
        
        Args:
            trade: Trade data from SDK
            current_price: Current market price (optional, will be fetched if not provided)
            
        Returns:
            PositionSummary: Position summary data
        """
        try:
            # Extract basic position data
            pair_index = trade.pair_index
            is_long = trade.is_long
            collateral = float(trade.collateral_in_trade)
            leverage = float(trade.leverage)
            entry_price = float(trade.open_price)
            trade_index = trade.index
            
            # Calculate position size
            position_size = collateral * leverage
            
            # Get current price if not provided
            if current_price is None:
                # For now, use entry price as current price
                # In a full implementation, you'd fetch current market price
                current_price = entry_price
            
            # Calculate PnL
            price_change = (current_price - entry_price) if is_long else (entry_price - current_price)
            pnl = price_change * (position_size / entry_price)
            pnl_percent = (pnl / collateral) * 100
            
            return PositionSummary(
                pair=f"PAIR_{pair_index}",  # You might want to resolve this to actual pair name
                is_long=is_long,
                size=position_size,
                entry_price=entry_price,
                current_price=current_price,
                pnl=pnl,
                pnl_percent=pnl_percent,
                collateral=collateral,
                leverage=leverage,
                trade_index=trade_index,
                pair_index=pair_index
            )
            
        except Exception as e:
            logger.error(f"❌ Error creating position summary: {e}")
            raise
    
    async def close_full(self, trader_address: str, trade: TradeExtendedResponse) -> CloseResult:
        """
        Close a position fully
        
        Args:
            trader_address: Trader wallet address
            trade: Trade to close
            
        Returns:
            CloseResult: Close operation result
        """
        try:
            executor = await self._get_executor()
            
            # Close full position
            result = await executor.close_trade(
                pair_index=trade.pair_index,
                trade_index=trade.index,
                collateral_to_close=float(trade.collateral_in_trade),
                trader_address=trader_address
            )
            
            if result.success:
                return CloseResult(
                    success=True,
                    tx_hash=result.tx_hash,
                    closed_collateral=float(trade.collateral_in_trade)
                )
            else:
                return CloseResult(
                    success=False,
                    error=result.error
                )
                
        except Exception as e:
            logger.error(f"❌ Error closing full position: {e}")
            return CloseResult(
                success=False,
                error=str(e)
            )
    
    async def close_partial(self, trader_address: str, trade: TradeExtendedResponse, 
                           fraction: float) -> CloseResult:
        """
        Close a position partially
        
        Args:
            trader_address: Trader wallet address
            trade: Trade to close partially
            fraction: Fraction to close (0.0 to 1.0)
            
        Returns:
            CloseResult: Close operation result
        """
        try:
            if fraction <= 0 or fraction >= 1:
                return CloseResult(
                    success=False,
                    error="Fraction must be between 0 and 1 for partial close"
                )
            
            executor = await self._get_executor()
            
            # Calculate collateral to close
            total_collateral = float(trade.collateral_in_trade)
            collateral_to_close = total_collateral * fraction
            
            # Close partial position
            result = await executor.close_trade(
                pair_index=trade.pair_index,
                trade_index=trade.index,
                collateral_to_close=collateral_to_close,
                trader_address=trader_address
            )
            
            if result.success:
                return CloseResult(
                    success=True,
                    tx_hash=result.tx_hash,
                    closed_collateral=collateral_to_close
                )
            else:
                return CloseResult(
                    success=False,
                    error=result.error
                )
                
        except Exception as e:
            logger.error(f"❌ Error closing partial position: {e}")
            return CloseResult(
                success=False,
                error=str(e)
            )
    
    async def get_portfolio_summary(self, trader_address: str) -> Dict[str, Any]:
        """
        Get a comprehensive portfolio summary
        
        Args:
            trader_address: Trader wallet address
            
        Returns:
            Dict[str, Any]: Portfolio summary including PnL, positions, etc.
        """
        try:
            # Get all trades
            trades, pending_orders = await self.get_trades(trader_address)
            
            # Calculate portfolio metrics
            total_collateral = sum(float(trade.collateral_in_trade) for trade in trades)
            total_pnl = 0.0
            long_positions = 0
            short_positions = 0
            
            position_summaries = []
            
            for trade in trades:
                try:
                    summary = await self.get_position_summary(trade)
                    position_summaries.append(summary)
                    total_pnl += summary.pnl
                    
                    if summary.is_long:
                        long_positions += 1
                    else:
                        short_positions += 1
                        
                except Exception as e:
                    logger.warning(f"Could not create summary for trade {trade.index}: {e}")
                    continue
            
            # Calculate portfolio metrics
            total_pnl_percent = (total_pnl / total_collateral * 100) if total_collateral > 0 else 0
            
            return {
                "trader_address": trader_address,
                "total_positions": len(trades),
                "pending_orders": len(pending_orders),
                "long_positions": long_positions,
                "short_positions": short_positions,
                "total_collateral": total_collateral,
                "total_pnl": total_pnl,
                "total_pnl_percent": total_pnl_percent,
                "positions": position_summaries,
                "pending_limit_orders": pending_orders
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting portfolio summary for {trader_address}: {e}")
            return {
                "trader_address": trader_address,
                "error": str(e),
                "total_positions": 0,
                "pending_orders": 0,
                "long_positions": 0,
                "short_positions": 0,
                "total_collateral": 0.0,
                "total_pnl": 0.0,
                "total_pnl_percent": 0.0,
                "positions": [],
                "pending_limit_orders": []
            }
    
    async def close_all_positions(self, trader_address: str) -> List[CloseResult]:
        """
        Close all positions for a trader
        
        Args:
            trader_address: Trader wallet address
            
        Returns:
            List[CloseResult]: Results of closing each position
        """
        try:
            trades, _ = await self.get_trades(trader_address)
            
            if not trades:
                logger.info(f"No positions to close for {trader_address}")
                return []
            
            results = []
            for trade in trades:
                result = await self.close_full(trader_address, trade)
                results.append(result)
                
                if not result.success:
                    logger.error(f"Failed to close position {trade.index}: {result.error}")
            
            successful_closes = sum(1 for r in results if r.success)
            logger.info(f"Closed {successful_closes}/{len(trades)} positions for {trader_address}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error closing all positions for {trader_address}: {e}")
            return []
    
    async def close_profitable_positions(self, trader_address: str, min_profit_percent: float = 0.0) -> List[CloseResult]:
        """
        Close only profitable positions
        
        Args:
            trader_address: Trader wallet address
            min_profit_percent: Minimum profit percentage to close
            
        Returns:
            List[CloseResult]: Results of closing profitable positions
        """
        try:
            trades, _ = await self.get_trades(trader_address)
            
            if not trades:
                return []
            
            results = []
            for trade in trades:
                try:
                    summary = await self.get_position_summary(trade)
                    
                    if summary.pnl_percent >= min_profit_percent:
                        result = await self.close_full(trader_address, trade)
                        results.append(result)
                        
                        if result.success:
                            logger.info(f"Closed profitable position {trade.index}: {summary.pnl_percent:.2f}% profit")
                        else:
                            logger.error(f"Failed to close profitable position {trade.index}: {result.error}")
                            
                except Exception as e:
                    logger.warning(f"Could not evaluate position {trade.index} for profitability: {e}")
                    continue
            
            logger.info(f"Closed {len(results)} profitable positions for {trader_address}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error closing profitable positions for {trader_address}: {e}")
            return []


# Global positions manager instance
_positions_manager: Optional[AvantisPositions] = None


def get_positions_manager() -> AvantisPositions:
    """
    Get the global positions manager instance
    
    Returns:
        AvantisPositions: Global positions manager
    """
    global _positions_manager
    
    if _positions_manager is None:
        _positions_manager = AvantisPositions()
        
    return _positions_manager
