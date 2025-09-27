from typing import Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.database.models import Position
from src.services.base_service import BaseService
from src.services.cache_service import cache_service, CacheKeys, cached
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AnalyticsService(BaseService):
    """Enhanced analytics service with proper abstraction"""
    
    @cached(ttl=300, key_prefix="analytics")
    def get_user_stats(self, user_id: int) -> Dict[str, any]:
        """Get comprehensive user trading statistics"""
        self.log_operation("get_user_stats", user_id)
        
        def _get_stats(session: Session, user_id: int) -> Dict[str, any]:
            # Total trades
            total_positions = session.query(Position).filter(
                Position.user_id == user_id
            ).count()
            
            # Winning trades
            winning_trades = session.query(Position).filter(
                Position.user_id == user_id,
                Position.pnl > 0,
                Position.status == 'CLOSED'
            ).count()
            
            # Win rate
            win_rate = (winning_trades / total_positions * 100) if total_positions > 0 else 0
            
            # Total PnL
            total_pnl = session.query(func.sum(Position.pnl)).filter(
                Position.user_id == user_id,
                Position.status == 'CLOSED'
            ).scalar() or 0
            
            # Additional metrics
            losing_trades = session.query(Position).filter(
                Position.user_id == user_id,
                Position.pnl < 0,
                Position.status == 'CLOSED'
            ).count()
            
            avg_win = session.query(func.avg(Position.pnl)).filter(
                Position.user_id == user_id,
                Position.pnl > 0,
                Position.status == 'CLOSED'
            ).scalar() or 0
            
            avg_loss = session.query(func.avg(Position.pnl)).filter(
                Position.user_id == user_id,
                Position.pnl < 0,
                Position.status == 'CLOSED'
            ).scalar() or 0
            
            return {
                'total_trades': total_positions,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0
            }
        
        return self.execute_with_session(_get_stats, user_id)
    
    @cached(ttl=180, key_prefix="portfolio")
    def get_portfolio_summary(self, user_id: int) -> Dict[str, any]:
        """Get portfolio summary with current positions"""
        self.log_operation("get_portfolio_summary", user_id)
        
        def _get_portfolio(session: Session, user_id: int) -> Dict[str, any]:
            # Get open positions
            open_positions = session.query(Position).filter(
                Position.user_id == user_id,
                Position.status == 'OPEN'
            ).all()
            
            total_unrealized_pnl = sum(pos.pnl for pos in open_positions)
            total_exposure = sum(pos.size * pos.leverage for pos in open_positions)
            
            return {
                'open_positions': len(open_positions),
                'total_unrealized_pnl': total_unrealized_pnl,
                'total_exposure': total_exposure,
                'positions': [
                    {
                        'symbol': pos.symbol,
                        'side': pos.side,
                        'size': pos.size,
                        'leverage': pos.leverage,
                        'pnl': pos.pnl,
                        'entry_price': pos.entry_price,
                        'current_price': pos.current_price
                    }
                    for pos in open_positions
                ]
            }
        
        return self.execute_with_session(_get_portfolio, user_id)
    
    def validate_input(self, data: Dict[str, any]) -> bool:
        """Validate input data"""
        return 'user_id' in data and isinstance(data['user_id'], int)


# Backward compatibility
class Analytics(AnalyticsService):
    """Backward compatibility wrapper"""
    pass
