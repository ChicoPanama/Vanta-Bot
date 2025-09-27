from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(50))
    wallet_address = Column(String(42), unique=True)
    encrypted_private_key = Column(Text)
    created_at = Column(DateTime, default=func.now())
    last_active = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)
    referral_code = Column(String(10), unique=True)
    referred_by = Column(Integer)

class Position(Base):
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    symbol = Column(String(20), nullable=False)  # BTC, ETH, EURUSD, etc.
    side = Column(String(5), nullable=False)     # LONG, SHORT
    size = Column(Float, nullable=False)         # Position size in USDC
    leverage = Column(Integer, nullable=False)
    entry_price = Column(Float)
    current_price = Column(Float)
    pnl = Column(Float, default=0.0)
    liquidation_price = Column(Float)
    status = Column(String(10), default='OPEN')  # OPEN, CLOSED, LIQUIDATED
    opened_at = Column(DateTime, default=func.now())
    closed_at = Column(DateTime)
    tx_hash = Column(String(66))

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    symbol = Column(String(20), nullable=False)
    order_type = Column(String(10), nullable=False)  # MARKET, LIMIT, STOP
    side = Column(String(5), nullable=False)         # LONG, SHORT
    size = Column(Float, nullable=False)
    price = Column(Float)  # For limit orders
    leverage = Column(Integer, nullable=False)
    status = Column(String(10), default='PENDING')   # PENDING, FILLED, CANCELLED
    created_at = Column(DateTime, default=func.now())
    filled_at = Column(DateTime)
    tx_hash = Column(String(66))

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    tx_hash = Column(String(66), unique=True)
    tx_type = Column(String(20))  # DEPOSIT, WITHDRAW, TRADE, etc.
    amount = Column(Float)
    status = Column(String(10))   # PENDING, CONFIRMED, FAILED
    created_at = Column(DateTime, default=func.now())
    confirmed_at = Column(DateTime)
    gas_used = Column(Integer)
    gas_price = Column(Float)
