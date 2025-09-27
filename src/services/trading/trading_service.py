"""
Trading Service
Business logic for trading operations
"""

from typing import Dict, Any, Optional, List
from decimal import Decimal

from src.services.base_service import BaseService
from src.database.models import Position, User
from src.blockchain.avantis_client import avantis_client
from src.blockchain.wallet_manager import wallet_manager
from src.utils.validators import validate_position_data, validate_trade_size, validate_leverage
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TradingService(BaseService):
    """Service for trading operations"""
    
    def create_position(self, user_id: int, position_data: Dict[str, Any]) -> Position:
        """Create a new trading position"""
        self.log_operation("create_position", user_id, **position_data)
        
        # Validate position data
        validated_data = validate_position_data(position_data)
        
        def _create_position(session, user_id: int, data: Dict[str, Any]) -> Position:
            # Get user
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("User not found")
            
            # Check wallet balance
            wallet_info = wallet_manager.get_wallet_info(user.wallet_address)
            required_balance = data['size']
            
            if wallet_info['usdc_balance'] < required_balance:
                raise ValueError(f"Insufficient balance. Required: ${required_balance}, Available: ${wallet_info['usdc_balance']:.2f}")
            
            # Create position record
            position = Position(
                user_id=user_id,
                symbol=data['symbol'],
                side=data['side'],
                size=Decimal(str(data['size'])),
                leverage=data['leverage'],
                entry_price=Decimal('0'),  # Will be updated after execution
                current_price=Decimal('0'),
                pnl=Decimal('0'),
                status='PENDING'
            )
            
            session.add(position)
            session.flush()  # Get the ID
            
            return position
        
        return self.execute_with_session(_create_position, user_id, validated_data)
    
    def execute_position(self, position_id: int, tx_hash: str) -> Position:
        """Execute a pending position"""
        self.log_operation("execute_position", position_id=position_id, tx_hash=tx_hash)
        
        def _execute_position(session, position_id: int, tx_hash: str) -> Position:
            position = session.query(Position).filter(Position.id == position_id).first()
            if not position:
                raise ValueError("Position not found")
            
            if position.status != 'PENDING':
                raise ValueError("Position is not in pending status")
            
            # Update position status and transaction hash
            position.status = 'OPEN'
            position.tx_hash = tx_hash
            # Note: entry_price and current_price should be updated from blockchain data
            
            return position
        
        return self.execute_with_session(_execute_position, position_id, tx_hash)
    
    def get_user_positions(self, user_id: int, status: Optional[str] = None) -> List[Position]:
        """Get user positions with optional status filter"""
        self.log_operation("get_user_positions", user_id, status=status)
        
        def _get_positions(session, user_id: int, status: Optional[str] = None) -> List[Position]:
            query = session.query(Position).filter(Position.user_id == user_id)
            
            if status:
                query = query.filter(Position.status == status)
            
            return query.order_by(Position.created_at.desc()).all()
        
        return self.execute_with_session(_get_positions, user_id, status)
    
    def update_position_pnl(self, position_id: int, current_price: Decimal, pnl: Decimal) -> Position:
        """Update position PnL"""
        self.log_operation("update_position_pnl", position_id=position_id, current_price=current_price, pnl=pnl)
        
        def _update_pnl(session, position_id: int, current_price: Decimal, pnl: Decimal) -> Position:
            position = session.query(Position).filter(Position.id == position_id).first()
            if not position:
                raise ValueError("Position not found")
            
            position.current_price = current_price
            position.pnl = pnl
            
            return position
        
        return self.execute_with_session(_update_pnl, position_id, current_price, pnl)
    
    def close_position(self, position_id: int, close_price: Decimal, pnl: Decimal) -> Position:
        """Close a position"""
        self.log_operation("close_position", position_id=position_id, close_price=close_price, pnl=pnl)
        
        def _close_position(session, position_id: int, close_price: Decimal, pnl: Decimal) -> Position:
            position = session.query(Position).filter(Position.id == position_id).first()
            if not position:
                raise ValueError("Position not found")
            
            if position.status != 'OPEN':
                raise ValueError("Position is not open")
            
            position.status = 'CLOSED'
            position.close_price = close_price
            position.pnl = pnl
            
            return position
        
        return self.execute_with_session(_close_position, position_id, close_price, pnl)
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate trading input data"""
        try:
            validate_position_data(data)
            return True
        except Exception:
            return False
