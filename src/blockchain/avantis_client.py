from src.blockchain.base_client import base_client
from src.config.settings import config
import logging
import json

logger = logging.getLogger(__name__)

class AvantisClient:
    def __init__(self):
        self.base_client = base_client
        
        # Simplified ABI - you'll need the actual Avantis contract ABIs
        self.trading_abi = [
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
        
        self.trading_contract = self.base_client.w3.eth.contract(
            address=config.AVANTIS_TRADING_CONTRACT,
            abi=self.trading_abi
        )
        
    def open_position(self, user_address: str, private_key: str, 
                     symbol: str, size: float, is_long: bool, leverage: int):
        """Open position on Avantis"""
        try:
            # Convert size to wei (assuming 6 decimals for USDC)
            size_wei = int(size * 10**6)
            
            # Build transaction
            transaction = self.trading_contract.functions.openPosition(
                symbol,
                size_wei,
                is_long,
                leverage
            ).build_transaction({
                'from': user_address,
                'nonce': self.base_client.w3.eth.get_transaction_count(user_address),
                'chainId': config.BASE_CHAIN_ID
            })
            
            # Send transaction
            tx_hash = self.base_client.send_transaction(transaction, private_key)
            
            return tx_hash
            
        except Exception as e:
            logger.error(f"Error opening position: {e}")
            raise e
            
    def close_position(self, user_address: str, private_key: str, position_id: int):
        """Close position on Avantis"""
        try:
            transaction = self.trading_contract.functions.closePosition(
                position_id
            ).build_transaction({
                'from': user_address,
                'nonce': self.base_client.w3.eth.get_transaction_count(user_address),
                'chainId': config.BASE_CHAIN_ID
            })
            
            tx_hash = self.base_client.send_transaction(transaction, private_key)
            
            return tx_hash
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            raise e
            
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
