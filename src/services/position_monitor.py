import asyncio
from src.database.operations import db
from src.database.models import Position
from src.services.price_service import price_service
from telegram import Bot
from src.config.settings import config
import logging

logger = logging.getLogger(__name__)

class PositionMonitor:
    def __init__(self):
        self.bot = Bot(config.TELEGRAM_BOT_TOKEN)
        self.check_interval = 30  # seconds
        
    async def monitor_positions(self):
        """Monitor all open positions"""
        while True:
            try:
                # This is a simplified version - you'd get all users
                # For now, just monitoring logic
                session = db.get_session()
                positions = session.query(Position).filter(
                    Position.status == 'OPEN'
                ).all()
                
                for position in positions:
                    await self.check_position(position)
                    
                session.close()
                
            except Exception as e:
                logger.error(f"Error monitoring positions: {e}")
                
            await asyncio.sleep(self.check_interval)
            
    async def check_position(self, position):
        """Check individual position for updates"""
        try:
            current_price = price_service.get_price(position.symbol)
            if not current_price:
                return
                
            # Update current price
            position.current_price = current_price
            
            # Calculate PnL
            if position.side == 'LONG':
                pnl_ratio = (current_price - position.entry_price) / position.entry_price
            else:  # SHORT
                pnl_ratio = (position.entry_price - current_price) / position.entry_price
                
            position.pnl = position.size * position.leverage * pnl_ratio
            
            # Check for liquidation
            liquidation_threshold = -0.95  # 95% loss triggers liquidation
            if pnl_ratio <= liquidation_threshold:
                await self.liquidate_position(position)
                
            # Save updates
            session = db.get_session()
            session.merge(position)
            session.commit()
            session.close()
            
        except Exception as e:
            logger.error(f"Error checking position {position.id}: {e}")
            
    async def liquidate_position(self, position):
        """Handle position liquidation"""
        try:
            position.status = 'LIQUIDATED'
            
            # Notify user
            user = db.get_user_by_id(position.user_id)
            if user:
                liquidation_msg = f"""
🚨 **Position Liquidated!**

Asset: {position.symbol}
Side: {position.side}
Size: ${position.size:,.2f}
Loss: ${position.pnl:,.2f}
                """
                
                await self.bot.send_message(
                    chat_id=user.telegram_id,
                    text=liquidation_msg,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error liquidating position: {e}")

# Global instance
position_monitor = PositionMonitor()
