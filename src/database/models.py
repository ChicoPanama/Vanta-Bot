from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON, BigInteger, Numeric, Index, LargeBinary, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(50))
    wallet_address = Column(String(42), unique=True)
    encrypted_private_key = Column(Text)  # Legacy field - will be deprecated
    created_at = Column(DateTime, default=func.now())
    last_active = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)
    referral_code = Column(String(10), unique=True)
    referred_by = Column(Integer)


class Wallet(Base):
    """Wallet model with envelope encryption support."""
    __tablename__ = "wallets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    address = Column(String(64), unique=True, nullable=False, index=True)
    ciphertext_privkey = Column(LargeBinary, nullable=False)
    dek_wrapped = Column(LargeBinary, nullable=False)
    encryption_version = Column(String(16), default="v2", nullable=False)
    kms_key_id = Column(String(128), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    rotated_at = Column(DateTime, nullable=True)

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

# Copy Trading Models
class Fill(Base):
    __tablename__ = "fills"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    address = Column(String(64), index=True, nullable=False)
    pair = Column(String(64), index=True, nullable=False)
    is_long = Column(Boolean, nullable=False)
    size = Column(Numeric(38,18), nullable=False)
    price = Column(Numeric(38,18), nullable=False)
    notional_usd = Column(Numeric(38,18), nullable=False)
    fee = Column(Numeric(38,18), nullable=False, server_default="0")
    side = Column(String(16), nullable=False)  # OPEN|CLOSE|...
    maker_taker = Column(String(8), nullable=True)
    block_number = Column(BigInteger, index=True, nullable=False)
    block_hash = Column(String(66), nullable=True)
    tx_hash = Column(String(66), index=True, nullable=False)
    ts = Column(BigInteger, index=True, nullable=False)
    
    # Composite indexes for efficient queries
    __table_args__ = (
        Index('idx_fills_address_ts', 'address', 'ts'),
        Index('idx_fills_pair_ts', 'pair', 'ts'),
        Index('idx_fills_address_pair_ts', 'address', 'pair', 'ts'),
    )

class TradingPosition(Base):
    __tablename__ = "trading_positions"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    address = Column(String(64), index=True, nullable=False)
    pair = Column(String(64), index=True, nullable=False)
    is_long = Column(Boolean, nullable=False)
    entry_px = Column(Numeric(38,18), nullable=False)
    size = Column(Numeric(38,18), nullable=False)
    opened_at = Column(BigInteger, index=True, nullable=False)
    closed_at = Column(BigInteger, nullable=True)
    pnl_realized = Column(Numeric(38,18), nullable=False, server_default="0")
    fees = Column(Numeric(38,18), nullable=False, server_default="0")
    funding = Column(Numeric(38,18), nullable=False, server_default="0")
    tx_open = Column(String(66), nullable=False)
    tx_close = Column(String(66), nullable=True)
    
    # Composite indexes for efficient queries
    __table_args__ = (
        Index('idx_trading_positions_address_opened', 'address', 'opened_at'),
        Index('idx_trading_positions_address_closed', 'address', 'closed_at'),
    )

class CopyConfiguration(Base):
    __tablename__ = "copy_configurations"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    leader_address = Column(String(64), index=True, nullable=False)
    sizing_mode = Column(String(32), nullable=False)  # "FIXED_NOTIONAL" or "PCT_EQUITY"
    sizing_value = Column(Numeric(38,18), nullable=False)
    max_slippage_bps = Column(BigInteger, nullable=False)
    max_leverage = Column(Numeric(38,18), nullable=False)
    notional_cap = Column(Numeric(38,18), nullable=False)
    pair_filters = Column(String(512), nullable=True)  # JSON
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(BigInteger, index=True, nullable=False)
    updated_at = Column(BigInteger, index=True, nullable=False)

class CopyPosition(Base):
    __tablename__ = "copy_positions"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    leader_address = Column(String(64), index=True, nullable=False)
    leader_tx_hash = Column(String(66), index=True, nullable=False)
    copy_tx_hash = Column(String(66), index=True, nullable=False)
    pair = Column(String(64), nullable=False)
    is_long = Column(Boolean, nullable=False)
    size = Column(Numeric(38,18), nullable=False)
    entry_price = Column(Numeric(38,18), nullable=False)
    copy_ratio = Column(Numeric(38,18), nullable=False)
    opened_at = Column(BigInteger, index=True, nullable=False)
    closed_at = Column(BigInteger, nullable=True)
    pnl = Column(Numeric(38,18), nullable=False, server_default="0")
    status = Column(String(16), nullable=False)  # "OPEN", "CLOSED", "LIQUIDATED"
    
    __table_args__ = (
        Index('idx_copy_positions_user_leader', 'user_id', 'leader_address'),
        Index('idx_copy_positions_user_status', 'user_id', 'status'),
    )


class SentTransaction(Base):
    """Table for tracking sent transactions to ensure idempotency."""
    __tablename__ = "sent_transactions"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    request_id = Column(String(128), unique=True, nullable=False, index=True)
    tx_hash = Column(String(66), nullable=False, index=True)
    wallet_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    confirmed_at = Column(DateTime, nullable=True)
    status = Column(String(16), default="PENDING", nullable=False)  # PENDING, CONFIRMED, FAILED
