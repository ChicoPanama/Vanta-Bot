"""
Avantis Trade Executor - Trade Execution Service

This module translates bot order DTOs to SDK TradeInput and handles trade execution
using the Avantis Trader SDK with DRY/LIVE safety controls.
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from avantis_trader_sdk import TradeInput, TradeInputOrderType

from src.integrations.avantis.sdk_client import get_sdk_client
from src.services.markets.avantis_price_provider import get_price_provider

logger = logging.getLogger(__name__)

# Global execution mode (DRY or LIVE)
_execution_mode = os.getenv('COPY_EXECUTION_MODE', 'DRY').upper()


@dataclass
class OrderRequest:
    """Order request data structure"""
    pair: str
    is_long: bool
    collateral_usdc: float
    leverage: float
    order_type: str = "market"  # "market" or "limit"
    limit_price: Optional[float] = None
    tp: Optional[float] = None  # Take profit
    sl: Optional[float] = None  # Stop loss
    slippage_pct: float = 0.5


@dataclass
class TradeResult:
    """Trade execution result"""
    success: bool
    tx_hash: Optional[str] = None
    trade_index: Optional[int] = None
    quote: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AvantisExecutor:
    """
    Trade execution service using Avantis Trader SDK
    
    Handles trade execution, order building, and transaction broadcasting.
    """
    
    def __init__(self):
        """Initialize the trade executor"""
        self._sdk_client = None
        self._price_provider = None
        
    async def _get_sdk_client(self):
        """Get or initialize the SDK client"""
        if self._sdk_client is None:
            sdk_client = get_sdk_client()
            self._sdk_client = sdk_client.get_client()
        return self._sdk_client
    
    async def _get_price_provider(self):
        """Get or initialize the price provider"""
        if self._price_provider is None:
            self._price_provider = get_price_provider()
        return self._price_provider
    
    def _build_trade_input(self, order: OrderRequest, trader_address: str, pair_index: int) -> TradeInput:
        """
        Build TradeInput from order request using snake_case fields
        
        Args:
            order: Order request
            trader_address: Trader wallet address
            pair_index: Trading pair index
            
        Returns:
            TradeInput: SDK trade input object
        """
        return TradeInput(
            trader=trader_address,
            open_price=order.limit_price if order.order_type == "limit" else None,
            pair_index=pair_index,
            collateral_in_trade=order.collateral_usdc,
            is_long=order.is_long,
            leverage=order.leverage,
            index=0,
            tp=order.tp or 0,
            sl=order.sl or 0,
            timestamp=0
        )
    
    def _get_order_type(self, order: OrderRequest, zero_fee: bool = False) -> TradeInputOrderType:
        """
        Convert order type string to SDK order type
        
        Args:
            order: Order request
            zero_fee: Whether to use zero fee order type
            
        Returns:
            TradeInputOrderType: SDK order type
        """
        if order.order_type.lower() == "market":
            return TradeInputOrderType.MARKET_ZERO_FEE if zero_fee else TradeInputOrderType.MARKET
        elif order.order_type.lower() == "limit":
            return TradeInputOrderType.LIMIT
        else:
            logger.warning(f"Unknown order type: {order.order_type}, defaulting to MARKET")
            return TradeInputOrderType.MARKET_ZERO_FEE if zero_fee else TradeInputOrderType.MARKET
    
    async def open_market(self, order: OrderRequest, zero_fee: bool = False) -> TradeResult:
        """
        Open a market order with DRY/LIVE execution mode
        
        Args:
            order: Order request
            zero_fee: Whether to use zero fee order type
            
        Returns:
            TradeResult: Execution result
        """
        try:
            client = await self._get_sdk_client()
            price_provider = await self._get_price_provider()
            
            # Get trader address
            trader_address = client.get_trader_address()
            if not trader_address:
                return TradeResult(
                    success=False,
                    error="No trader address available - signer not configured"
                )
            
            # Get pair index
            pair_index = await price_provider.get_pair_index(order.pair)
            
            # Build trade input
            trade_input = self._build_trade_input(order, trader_address, pair_index)
            
            # Get trade quote for logging
            quote = await price_provider.quote_open(
                order.pair, 
                order.is_long, 
                order.collateral_usdc, 
                order.leverage,
                order.slippage_pct
            )
            
            # Structured logging
            logger.info(f"🎯 Trade Request: {order.pair} {'LONG' if order.is_long else 'SHORT'} "
                       f"${order.collateral_usdc} @ {order.leverage}x, slippage {order.slippage_pct}%, "
                       f"fee ${quote['opening_fee_usdc']:.4f}, impact {quote.get('impact_spread', 'N/A')}")
            
            # Check execution mode
            if _execution_mode == "DRY":
                logger.info("🔍 DRY RUN MODE - Would execute trade")
                return TradeResult(
                    success=True,
                    tx_hash="DRYRUN",
                    trade_index=0,
                    quote=quote
                )
            
            # LIVE mode execution
            logger.warning("⚠️ LIVE EXECUTION MODE - Executing real trade")
            
            # Ensure USDC allowance
            sdk_client = get_sdk_client()
            allowance_ok = await sdk_client.ensure_usdc_allowance(order.collateral_usdc, trader_address)
            if not allowance_ok:
                return TradeResult(
                    success=False,
                    error="Failed to ensure USDC allowance"
                )
            
            # Build and execute trade
            order_type = self._get_order_type(order, zero_fee)
            tx = await client.trade.build_trade_open_tx(
                trade_input, 
                order_type, 
                order.slippage_pct
            )
            
            # Sign and broadcast transaction
            tx_hash = await client.sign_and_get_receipt(tx)
            
            if tx_hash:
                logger.info(f"✅ LIVE Trade executed: {order.pair} {'LONG' if order.is_long else 'SHORT'} "
                           f"${order.collateral_usdc} USDC @ {order.leverage}x - TX: {tx_hash}")
                
                return TradeResult(
                    success=True,
                    tx_hash=tx_hash,
                    trade_index=0,  # Will be determined after position is created
                    quote=quote
                )
            else:
                return TradeResult(
                    success=False,
                    error="Transaction failed to broadcast"
                )
                
        except Exception as e:
            logger.error(f"❌ Error executing market order: {e}")
            return TradeResult(
                success=False,
                error=str(e)
            )
    
    async def open_limit(self, order: OrderRequest) -> TradeResult:
        """
        Open a limit order
        
        Args:
            order: Order request
            
        Returns:
            TradeResult: Execution result
        """
        try:
            if not order.limit_price:
                return TradeResult(
                    success=False,
                    error="Limit price required for limit orders"
                )
            
            # TODO: Implement proper limit order functionality when SDK supports it
            raise NotImplementedError("Limit orders not yet implemented in SDK integration")
            
        except Exception as e:
            logger.error(f"❌ Error executing limit order: {e}")
            return TradeResult(
                success=False,
                error=str(e)
            )
    
    async def close_trade(self, pair_index: int, trade_index: int, 
                         collateral_to_close: float, trader_address: str) -> TradeResult:
        """
        Close a trade (full or partial)
        
        Args:
            pair_index: Trading pair index
            trade_index: Trade index to close
            collateral_to_close: Amount of collateral to close
            trader_address: Trader wallet address
            
        Returns:
            TradeResult: Execution result
        """
        try:
            client = await self._get_sdk_client()
            
            # Build close trade transaction
            tx = await client.trade.build_trade_close_tx(
                pair_index=pair_index,
                trade_index=trade_index,
                collateral_to_close=collateral_to_close,
                trader=trader_address
            )
            
            # Sign and broadcast transaction
            tx_hash = await client.sign_and_get_receipt(tx)
            
            if tx_hash:
                logger.info(f"✅ Trade closed: pair {pair_index}, trade {trade_index}, "
                           f"collateral {collateral_to_close} - TX: {tx_hash}")
                
                return TradeResult(
                    success=True,
                    tx_hash=tx_hash
                )
            else:
                return TradeResult(
                    success=False,
                    error="Close transaction failed to broadcast"
                )
                
        except Exception as e:
            logger.error(f"❌ Error closing trade: {e}")
            return TradeResult(
                success=False,
                error=str(e)
            )
    
    async def estimate_gas(self, order: OrderRequest) -> Optional[int]:
        """
        Estimate gas cost for a trade
        
        Args:
            order: Order request
            
        Returns:
            int: Estimated gas cost in wei
        """
        try:
            client = await self._get_sdk_client()
            trader_address = client.get_trader_address()
            
            if not trader_address:
                return None
            
            # Build trade input for gas estimation
            trade_input = self._build_trade_input(order, trader_address)
            pair_index = await self._get_price_provider().get_pair_index(order.pair)
            trade_input.pair_index = pair_index
            
            order_type = self._get_order_type(order)
            
            # Build transaction (without sending)
            tx = await client.trade.build_trade_open_tx(
                trade_input, 
                order_type, 
                order.slippage_pct
            )
            
            # Estimate gas
            estimated_gas = await client.estimate_gas(tx)
            return estimated_gas
            
        except Exception as e:
            logger.error(f"❌ Error estimating gas: {e}")
            return None
    
    async def get_trader_info(self) -> Optional[Dict[str, Any]]:
        """
        Get trader information including balance and allowance
        
        Returns:
            Dict[str, Any]: Trader information
        """
        try:
            client = await self._get_sdk_client()
            trader_address = client.get_trader_address()
            
            if not trader_address:
                return None
            
            # Get balances
            eth_balance = get_sdk_client().get_balance(trader_address)
            usdc_allowance = await client.get_usdc_allowance_for_trading(trader_address)
            usdc_balance = await client.get_usdc_balance(trader_address)
            
            return {
                "address": trader_address,
                "eth_balance": eth_balance,
                "usdc_balance": usdc_balance,
                "usdc_allowance": usdc_allowance,
                "chain_id": get_sdk_client().get_chain_id()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting trader info: {e}")
            return None


# Global executor instance
_executor: Optional[AvantisExecutor] = None


def get_executor() -> AvantisExecutor:
    """
    Get the global executor instance
    
    Returns:
        AvantisExecutor: Global executor
    """
    global _executor
    
    if _executor is None:
        _executor = AvantisExecutor()
        
    return _executor


def get_execution_mode() -> str:
    """
    Get current execution mode
    
    Returns:
        str: Current execution mode (DRY or LIVE)
    """
    return _execution_mode


def set_execution_mode(mode: str) -> bool:
    """
    Set execution mode (admin only)
    
    Args:
        mode: Execution mode (DRY or LIVE)
        
    Returns:
        bool: True if mode was set successfully
    """
    global _execution_mode
    
    mode = mode.upper()
    if mode not in ["DRY", "LIVE"]:
        logger.error(f"Invalid execution mode: {mode}. Must be DRY or LIVE")
        return False
    
    old_mode = _execution_mode
    _execution_mode = mode
    
    logger.warning(f"🔄 Execution mode changed from {old_mode} to {_execution_mode}")
    
    if mode == "LIVE":
        logger.warning("⚠️ LIVE MODE ENABLED - Real trades will be executed!")
    else:
        logger.info("🔍 DRY MODE ENABLED - No real trades will be executed")
    
    return True
