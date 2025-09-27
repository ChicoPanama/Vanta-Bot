from src.database.operations import db
from src.database.models import Position
from datetime import datetime, timedelta

class Analytics:
    def get_user_stats(self, user_id: int):
        """Get user trading statistics"""
        session = db.get_session()
        
        try:
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
            from sqlalchemy import func
            total_pnl = session.query(func.sum(Position.pnl)).filter(
                Position.user_id == user_id,
                Position.status == 'CLOSED'
            ).scalar() or 0
            
            return {
                'total_trades': total_positions,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'winning_trades': winning_trades
            }
            
        finally:
            session.close()
