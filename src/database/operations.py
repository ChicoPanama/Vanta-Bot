"""
Database Operations
Database management and operations for the Vanta Bot
"""

import logging
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from .models import Base, User, Position, Order, Transaction
from ..config.settings import config

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database manager for handling all database operations"""
    
    def __init__(self):
        try:
            self.engine = create_engine(config.DATABASE_URL)
            self.SessionLocal = sessionmaker(bind=self.engine)
        except Exception as e:
            logger.warning(f"Database connection failed: {e}. Using in-memory SQLite for testing.")
            # Fallback to SQLite for testing
            self.engine = create_engine("sqlite:///:memory:")
            self.SessionLocal = sessionmaker(bind=self.engine)
        
    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)
        
    def get_session(self) -> Session:
        return self.SessionLocal()
        
    def create_user(self, telegram_id: int, username: str = None, 
                   wallet_address: str = None, encrypted_private_key: str = None):
        session = self.get_session()
        try:
            user = User(
                telegram_id=telegram_id,
                username=username,
                wallet_address=wallet_address,
                encrypted_private_key=encrypted_private_key
            )
            session.add(user)
            session.commit()
            return user
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating user: {e}")
            return None
        finally:
            session.close()
            
    def get_user(self, telegram_id: int):
        session = self.get_session()
        try:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            return user
        finally:
            session.close()
            
    def get_user_by_id(self, user_id: int):
        session = self.get_session()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            return user
        finally:
            session.close()
            
    def create_position(self, user_id: int, symbol: str, side: str, 
                       size: float, leverage: int, entry_price: float = None):
        session = self.get_session()
        try:
            position = Position(
                user_id=user_id,
                symbol=symbol,
                side=side,
                size=size,
                leverage=leverage,
                entry_price=entry_price
            )
            session.add(position)
            session.commit()
            return position
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating position: {e}")
            return None
        finally:
            session.close()
            
    def get_user_positions(self, user_id: int, status: str = 'OPEN'):
        session = self.get_session()
        try:
            positions = session.query(Position).filter(
                Position.user_id == user_id,
                Position.status == status
            ).all()
            return positions
        finally:
            session.close()
            
    def update_position(self, position_id: int, **kwargs):
        session = self.get_session()
        try:
            position = session.query(Position).filter(Position.id == position_id).first()
            if position:
                for key, value in kwargs.items():
                    setattr(position, key, value)
                session.commit()
                return position
            return None
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating position: {e}")
            return None
        finally:
            session.close()
            
    def create_order(self, user_id: int, symbol: str, order_type: str, side: str,
                    size: float, leverage: int, price: float = None):
        session = self.get_session()
        try:
            order = Order(
                user_id=user_id,
                symbol=symbol,
                order_type=order_type,
                side=side,
                size=size,
                leverage=leverage,
                price=price
            )
            session.add(order)
            session.commit()
            return order
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating order: {e}")
            return None
        finally:
            session.close()
            
    def create_transaction(self, user_id: int, tx_hash: str, tx_type: str,
                          amount: float = None, status: str = 'PENDING'):
        session = self.get_session()
        try:
            transaction = Transaction(
                user_id=user_id,
                tx_hash=tx_hash,
                tx_type=tx_type,
                amount=amount,
                status=status
            )
            session.add(transaction)
            session.commit()
            return transaction
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating transaction: {e}")
            return None
        finally:
            session.close()

# Global instance
db = DatabaseManager()
