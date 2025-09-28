from src.blockchain.base_client import base_client
from src.config.settings import settings
from src.blockchain.abi_loader import abi_loader
from src.services.oracle import create_default_oracle, create_price_validator
import logging
from decimal import Decimal, getcontext
from typing import Dict, Optional
import uuid

# Set high precision for financial calculations
getcontext().prec = 50

logger = logging.getLogger(__name__)


class AvantisClient:
    """Typed Avantis client with envelope encryption and oracle integration."""
    
    def __init__(self, oracle=None, validator=None):
        self.base_client = base_client
        self.oracle = oracle or create_default_oracle()
        self.validator = validator or create_price_validator()
        
        # Load ABIs with hash validation
        try:
            self.trading_abi = abi_loader.load_abi("Trading")
            self.vault_abi = abi_loader.load_abi("Vault")
        except Exception as e:
            logger.error(f"Failed to load ABIs: {e}")
            # Fallback to simplified ABI
            self.trading_abi = self._get_fallback_abi()
            self.vault_abi = []
        
        # Initialize contracts
        if settings.AVANTIS_TRADING_CONTRACT:
            self.trading_contract = self.base_client.w3.eth.contract(
                address=settings.AVANTIS_TRADING_CONTRACT,
                abi=self.trading_abi
            )
        else:
            self.trading_contract = None
            logger.warning("AVANTIS_TRADING_CONTRACT not configured")
        
        if settings.AVANTIS_VAULT_CONTRACT:
            self.vault_contract = self.base_client.w3.eth.contract(
                address=settings.AVANTIS_VAULT_CONTRACT,
                abi=self.vault_abi
            )
        else:
            self.vault_contract = None
            logger.warning("AVANTIS_VAULT_CONTRACT not configured")
    
    def _get_fallback_abi(self):
        """Fallback ABI if loading fails."""
        return [
            {
                "inputs": [
                    {"name": "asset", "type": "string"},
                    {"name": "size", "type": "uint256"},
                    {"name": "isLong", "type": "bool"},
                    {"name": "leverage", "type": "uint256"}
                ],
                "name": "openPosition",
                "outputs": [],
                "type": "function"
            },
            {
                "inputs": [{"name": "positionId", "type": "uint256"}],
                "name": "closePosition", 
                "outputs": [],
                "type": "function"
            }
        ]
        
    def open_position(self, 
                     wallet_id: str, 
                     market: str, 
                     size: Decimal, 
                     leverage: Decimal, 
                     side: str,
                     request_id: str = None) -> str:
        """Open position with proper validation and envelope encryption.
        
        Args:
            wallet_id: Wallet identifier
            market: Market symbol (e.g., 'BTC', 'ETH')
            size: Position size in USDC
            leverage: Leverage multiplier
            side: 'long' or 'short'
            request_id: Unique request identifier
            
        Returns:
            Transaction hash
        """
        try:
            # Generate request ID if not provided
            if not request_id:
                request_id = str(uuid.uuid4())
            
            # Validate inputs
            if side not in ['long', 'short']:
                raise ValueError(f"Invalid side: {side}. Must be 'long' or 'short'")
            
            if size <= 0:
                raise ValueError(f"Invalid size: {size}. Must be positive")
            
            if leverage <= 0 or leverage > settings.MAX_LEVERAGE:
                raise ValueError(f"Invalid leverage: {leverage}. Must be 0 < leverage <= {settings.MAX_LEVERAGE}")
            
            # Get price from oracle
            price_quote = self.oracle.get_price(market)
            
            # Validate price
            if not self.validator.validate_quote(price_quote):
                raise ValueError(f"Price validation failed for {market}")
            
            # Calculate slippage bounds
            min_out = self._calculate_min_out(price_quote.price, side)
            
            # Convert to wei (assuming 18 decimals for size)
            size_wei = int(size * Decimal(10**18))
            leverage_wei = int(leverage * Decimal(10**18))
            
            # Build transaction data
            if not self.trading_contract:
                raise ValueError("Trading contract not configured")
            
            # Encode function call
            data = self.trading_contract.encodeABI(
                fn_name="openPosition",
                args=[market, size_wei, leverage_wei, side == "long", min_out]
            )
            
            # Build transaction parameters
            tx_params = {
                "to": settings.AVANTIS_TRADING_CONTRACT,
                "data": data,
                "value": 0  # No ETH value for position opening
            }
            
            # Send transaction using new pipeline
            tx_hash = self.base_client.send_transaction(
                wallet_id=wallet_id,
                tx_params=tx_params,
                request_id=request_id
            )
            
            logger.info(f"Position opened: {tx_hash} for {market} {side} {size} @ {leverage}x")
            return tx_hash
            
        except Exception as e:
            logger.error(f"Error opening position: {e}")
            raise
    
    def _calculate_min_out(self, price: Decimal, side: str) -> int:
        """Calculate minimum output for slippage protection.
        
        Args:
            price: Current market price
            side: 'long' or 'short'
            
        Returns:
            Minimum output in wei
        """
        slippage_bps = settings.DEFAULT_SLIPPAGE_PCT * 100  # Convert to basis points
        
        if side == "long":
            # For long positions, accept slightly higher price
            min_price = price * (Decimal("1") + Decimal(slippage_bps) / Decimal("10000"))
        else:
            # For short positions, accept slightly lower price
            min_price = price * (Decimal("1") - Decimal(slippage_bps) / Decimal("10000"))
        
        return int(min_price * Decimal(10**18))
            
    def close_position(self, wallet_id: str, position_id: int, request_id: str = None) -> str:
        """Close position with proper validation.
        
        Args:
            wallet_id: Wallet identifier
            position_id: Position ID to close
            request_id: Unique request identifier
            
        Returns:
            Transaction hash
        """
        try:
            # Generate request ID if not provided
            if not request_id:
                request_id = str(uuid.uuid4())
            
            # Validate inputs
            if position_id <= 0:
                raise ValueError(f"Invalid position ID: {position_id}")
            
            # Build transaction data
            if not self.trading_contract:
                raise ValueError("Trading contract not configured")
            
            # Encode function call
            data = self.trading_contract.encodeABI(
                fn_name="closePosition",
                args=[position_id]
            )
            
            # Build transaction parameters
            tx_params = {
                "to": settings.AVANTIS_TRADING_CONTRACT,
                "data": data,
                "value": 0  # No ETH value for position closing
            }
            
            # Send transaction using new pipeline
            tx_hash = self.base_client.send_transaction(
                wallet_id=wallet_id,
                tx_params=tx_params,
                request_id=request_id
            )
            
            logger.info(f"Position closed: {tx_hash} for position {position_id}")
            return tx_hash
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            raise
            
    def get_position_info(self, position_id: int):
        """Get position information from contract"""
        # This would need the actual Avantis view functions
        # Placeholder implementation
        return {
            'id': position_id,
            'status': 'OPEN',
            'pnl': 0.0
        }

    # ========================================
    # ADVANCED AVANTIS SDK COMPATIBLE FEATURES
    # ========================================
    
    def set_take_profit_stop_loss(self, user_address: str, private_key: str, 
                                 position_id: int, tp_price: float, sl_price: float):
        """Set Take Profit and Stop Loss using Avantis SDK build_trade_tp_sl_update_tx method"""
        try:
            # This would use the actual Avantis SDK method
            # return self.sdk.build_trade_tp_sl_update_tx(position_id, tp_price, sl_price)
            
            # For now, simulate the SDK call
            transaction = {
                'from': user_address,
                'to': config.AVANTIS_TRADING_CONTRACT,
                'data': f"0x{position_id:064x}{int(tp_price * 1e6):064x}{int(sl_price * 1e6):064x}",
                'nonce': self.base_client.w3.eth.get_transaction_count(user_address),
                'chainId': config.BASE_CHAIN_ID
            }
            
            tx_hash = self.base_client.send_transaction(transaction, private_key)
            return tx_hash
            
        except Exception as e:
            logger.error(f"Error setting TP/SL: {e}")
            raise e
    
    def update_position_leverage(self, user_address: str, private_key: str, 
                                position_id: int, new_leverage: int):
        """Update position leverage using Avantis SDK"""
        try:
            # This would use the actual Avantis SDK method
            # return self.sdk.update_position_leverage(position_id, new_leverage)
            
            # For now, simulate the SDK call
            transaction = {
                'from': user_address,
                'to': config.AVANTIS_TRADING_CONTRACT,
                'data': f"0x{position_id:064x}{new_leverage:064x}",
                'nonce': self.base_client.w3.eth.get_transaction_count(user_address),
                'chainId': config.BASE_CHAIN_ID
            }
            
            tx_hash = self.base_client.send_transaction(transaction, private_key)
            return tx_hash
            
        except Exception as e:
            logger.error(f"Error updating leverage: {e}")
            raise e
    
    def partial_close_position(self, user_address: str, private_key: str, 
                              position_id: int, close_percentage: float):
        """Partially close position using Avantis SDK"""
        try:
            # This would use the actual Avantis SDK method
            # return self.sdk.partial_close_position(position_id, close_percentage)
            
            # For now, simulate the SDK call
            transaction = {
                'from': user_address,
                'to': config.AVANTIS_TRADING_CONTRACT,
                'data': f"0x{position_id:064x}{int(close_percentage * 100):064x}",
                'nonce': self.base_client.w3.eth.get_transaction_count(user_address),
                'chainId': config.BASE_CHAIN_ID
            }
            
            tx_hash = self.base_client.send_transaction(transaction, private_key)
            return tx_hash
            
        except Exception as e:
            logger.error(f"Error partially closing position: {e}")
            raise e
    
    def get_position_details(self, position_id: int):
        """Get detailed position information from Avantis SDK"""
        try:
            # This would use the actual Avantis SDK method
            # return self.sdk.get_position(position_id)
            
            # For now, return mock data
            return {
                'id': position_id,
                'status': 'OPEN',
                'pnl': 0.0,
                'leverage': 10,
                'size': 100.0,
                'entry_price': 50000.0,
                'current_price': 51000.0,
                'take_profit': None,
                'stop_loss': None
            }
            
        except Exception as e:
            logger.error(f"Error getting position details: {e}")
            return None
    
    def get_portfolio_risk_metrics(self, user_address: str):
        """Get portfolio risk metrics using Avantis SDK"""
        try:
            # This would use the actual Avantis SDK method
            # return self.sdk.get_portfolio_risk(user_address)
            
            # For now, return mock risk metrics
            return {
                'total_value': 10000.0,
                'total_pnl': 500.0,
                'max_drawdown': -200.0,
                'leverage_ratio': 2.5,
                'risk_score': 0.3,
                'var_95': 1000.0
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio risk: {e}")
            return None
    
    def get_real_time_prices(self, symbols: list):
        """Get real-time prices using Avantis SDK price feeds"""
        try:
            # This would use the actual Avantis SDK method
            # return self.sdk.get_price_feeds(symbols)
            
            # For now, return mock prices
            prices = {}
            for symbol in symbols:
                if symbol == 'BTC':
                    prices[symbol] = 50000.0
                elif symbol == 'ETH':
                    prices[symbol] = 3000.0
                elif symbol == 'SOL':
                    prices[symbol] = 100.0
                else:
                    prices[symbol] = 1.0
            
            return prices
            
        except Exception as e:
            logger.error(f"Error getting real-time prices: {e}")
            return {}
    
    def create_price_alert(self, user_address: str, symbol: str, target_price: float, 
                           alert_type: str = 'above'):
        """Create price alert using Avantis SDK"""
        try:
            # This would use the actual Avantis SDK method
            # return self.sdk.create_price_alert(user_address, symbol, target_price, alert_type)
            
            # For now, return mock alert ID
            alert_id = f"alert_{symbol}_{target_price}_{alert_type}"
            return alert_id
            
        except Exception as e:
            logger.error(f"Error creating price alert: {e}")
            return None

# Global instance
avantis_client = AvantisClient()
