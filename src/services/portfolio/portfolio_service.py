"""
Portfolio Service
Business logic for portfolio management and analytics
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta

from src.services.base_service import BaseService
from src.database.models import Position, User
from src.utils.logging import get_logger

logger = get_logger(__name__)


class PortfolioService(BaseService):
    """Service for portfolio management and analytics"""
    
    def get_portfolio_summary(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive portfolio summary"""
        self.log_operation("get_portfolio_summary", user_id)
        
        def _get_summary(session, user_id: int) -> Dict[str, Any]:
            # Get all positions
            positions = session.query(Position).filter(Position.user_id == user_id).all()
            
            # Separate open and closed positions
            open_positions = [p for p in positions if p.status == 'OPEN']
            closed_positions = [p for p in positions if p.status == 'CLOSED']
            
            # Calculate metrics
            total_trades = len(closed_positions)
            winning_trades = len([p for p in closed_positions if p.pnl > 0])
            losing_trades = len([p for p in closed_positions if p.pnl < 0])
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            total_pnl = sum(p.pnl for p in closed_positions)
            unrealized_pnl = sum(p.pnl for p in open_positions)
            
            total_volume = sum(p.size * p.leverage for p in positions)
            total_exposure = sum(p.size * p.leverage for p in open_positions)
            
            # Calculate average metrics
            avg_win = sum(p.pnl for p in closed_positions if p.pnl > 0) / winning_trades if winning_trades > 0 else 0
            avg_loss = sum(p.pnl for p in closed_positions if p.pnl < 0) / losing_trades if losing_trades > 0 else 0
            
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
            
            # Get best and worst trades
            best_trade = max((p.pnl for p in closed_positions), default=Decimal('0'))
            worst_trade = min((p.pnl for p in closed_positions), default=Decimal('0'))
            
            # Calculate recent performance (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_positions = [p for p in closed_positions if p.created_at >= thirty_days_ago]
            recent_pnl = sum(p.pnl for p in recent_positions)
            recent_trades = len(recent_positions)
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': float(win_rate),
                'total_pnl': float(total_pnl),
                'unrealized_pnl': float(unrealized_pnl),
                'total_volume': float(total_volume),
                'total_exposure': float(total_exposure),
                'avg_win': float(avg_win),
                'avg_loss': float(avg_loss),
                'profit_factor': float(profit_factor),
                'best_trade': float(best_trade),
                'worst_trade': float(worst_trade),
                'recent_trades': recent_trades,
                'recent_pnl': float(recent_pnl),
                'open_positions_count': len(open_positions),
                'positions': [
                    {
                        'id': p.id,
                        'symbol': p.symbol,
                        'side': p.side,
                        'size': float(p.size),
                        'leverage': p.leverage,
                        'entry_price': float(p.entry_price),
                        'current_price': float(p.current_price),
                        'pnl': float(p.pnl),
                        'status': p.status,
                        'created_at': p.created_at.isoformat()
                    }
                    for p in open_positions
                ]
            }
        
        return self.execute_with_session(_get_summary, user_id)
    
    def get_performance_metrics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get performance metrics for a specific period"""
        self.log_operation("get_performance_metrics", user_id, days=days)
        
        def _get_metrics(session, user_id: int, days: int) -> Dict[str, Any]:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            positions = session.query(Position).filter(
                Position.user_id == user_id,
                Position.created_at >= cutoff_date,
                Position.status == 'CLOSED'
            ).all()
            
            if not positions:
                return {
                    'period_days': days,
                    'trades': 0,
                    'total_pnl': 0,
                    'win_rate': 0,
                    'avg_return': 0,
                    'volatility': 0
                }
            
            trades = len(positions)
            total_pnl = sum(p.pnl for p in positions)
            winning_trades = len([p for p in positions if p.pnl > 0])
            win_rate = (winning_trades / trades * 100) if trades > 0 else 0
            
            # Calculate average return per trade
            avg_return = float(total_pnl / trades) if trades > 0 else 0
            
            # Calculate volatility (standard deviation of returns)
            returns = [float(p.pnl) for p in positions]
            if len(returns) > 1:
                mean_return = sum(returns) / len(returns)
                variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
                volatility = variance ** 0.5
            else:
                volatility = 0
            
            return {
                'period_days': days,
                'trades': trades,
                'total_pnl': float(total_pnl),
                'win_rate': float(win_rate),
                'avg_return': avg_return,
                'volatility': volatility,
                'best_trade': float(max(p.pnl for p in positions)),
                'worst_trade': float(min(p.pnl for p in positions))
            }
        
        return self.execute_with_session(_get_metrics, user_id, days)
    
    def get_asset_breakdown(self, user_id: int) -> Dict[str, Any]:
        """Get portfolio breakdown by asset"""
        self.log_operation("get_asset_breakdown", user_id)
        
        def _get_breakdown(session, user_id: int) -> Dict[str, Any]:
            positions = session.query(Position).filter(Position.user_id == user_id).all()
            
            asset_stats = {}
            
            for position in positions:
                symbol = position.symbol
                if symbol not in asset_stats:
                    asset_stats[symbol] = {
                        'total_trades': 0,
                        'winning_trades': 0,
                        'total_pnl': Decimal('0'),
                        'total_volume': Decimal('0'),
                        'avg_leverage': 0
                    }
                
                stats = asset_stats[symbol]
                stats['total_trades'] += 1
                stats['total_pnl'] += position.pnl
                stats['total_volume'] += position.size * position.leverage
                
                if position.status == 'CLOSED' and position.pnl > 0:
                    stats['winning_trades'] += 1
            
            # Calculate averages and win rates
            for symbol, stats in asset_stats.items():
                if stats['total_trades'] > 0:
                    stats['win_rate'] = (stats['winning_trades'] / stats['total_trades'] * 100)
                    stats['avg_leverage'] = float(stats['total_volume'] / stats['total_trades'])
                else:
                    stats['win_rate'] = 0
                    stats['avg_leverage'] = 0
                
                # Convert Decimal to float for JSON serialization
                stats['total_pnl'] = float(stats['total_pnl'])
                stats['total_volume'] = float(stats['total_volume'])
            
            return asset_stats
        
        return self.execute_with_session(_get_breakdown, user_id)
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate portfolio input data"""
        required_fields = ['user_id']
        return all(field in data for field in required_fields) and isinstance(data['user_id'], int)
