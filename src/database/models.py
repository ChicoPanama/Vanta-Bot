import uuid

from sqlalchemy import (
    UUID,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

# Import encrypted types (Phase 1)
try:
    from src.database.types import EncryptedBytes, EncryptedJSON, EncryptedString
except ImportError:
    # Fallback if types not yet created
    EncryptedBytes = LargeBinary  # type: ignore
    EncryptedJSON = LargeBinary  # type: ignore
    EncryptedString = LargeBinary  # type: ignore

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

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
    # Phase 1: New envelope-encrypted private key field
    privkey_enc = Column(EncryptedBytes, nullable=True)


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    symbol = Column(String(20), nullable=False)  # BTC, ETH, EURUSD, etc.
    side = Column(String(5), nullable=False)  # LONG, SHORT
    size = Column(Float, nullable=False)  # Position size in USDC
    leverage = Column(Integer, nullable=False)
    entry_price = Column(Float)
    current_price = Column(Float)
    pnl = Column(Float, default=0.0)
    liquidation_price = Column(Float)
    status = Column(String(10), default="OPEN")  # OPEN, CLOSED, LIQUIDATED
    opened_at = Column(DateTime, default=func.now())
    closed_at = Column(DateTime)
    tx_hash = Column(String(66))


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    symbol = Column(String(20), nullable=False)
    order_type = Column(String(10), nullable=False)  # MARKET, LIMIT, STOP
    side = Column(String(5), nullable=False)  # LONG, SHORT
    size = Column(Float, nullable=False)
    price = Column(Float)  # For limit orders
    leverage = Column(Integer, nullable=False)
    status = Column(String(10), default="PENDING")  # PENDING, FILLED, CANCELLED
    created_at = Column(DateTime, default=func.now())
    filled_at = Column(DateTime)
    tx_hash = Column(String(66))


class Transaction(Base):
    """Transaction audit trail for idempotency."""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    request_id = Column(String(255), nullable=False, unique=True)
    tx_hash = Column(String(66), nullable=False)
    payload_hash = Column(String(64), nullable=False)  # SHA256 of tx params
    created_at = Column(DateTime, default=func.now())

    # Unique constraint on request_id + payload_hash for idempotency
    __table_args__ = (
        Index("idx_request_payload", "request_id", "payload_hash", unique=True),
    )

    gas_price = Column(Float)


# Copy Trading Models
class Fill(Base):
    __tablename__ = "fills"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    address = Column(String(64), index=True, nullable=False)
    pair = Column(String(64), index=True, nullable=False)
    is_long = Column(Boolean, nullable=False)
    size = Column(Numeric(38, 18), nullable=False)
    price = Column(Numeric(38, 18), nullable=False)
    notional_usd = Column(Numeric(38, 18), nullable=False)
    fee = Column(Numeric(38, 18), nullable=False, server_default="0")
    side = Column(String(16), nullable=False)  # OPEN|CLOSE|...
    maker_taker = Column(String(8), nullable=True)
    block_number = Column(BigInteger, index=True, nullable=False)
    block_hash = Column(String(66), nullable=True)
    tx_hash = Column(String(66), index=True, nullable=False)
    ts = Column(BigInteger, index=True, nullable=False)

    # Composite indexes for efficient queries
    __table_args__ = (
        Index("idx_fills_address_ts", "address", "ts"),
        Index("idx_fills_pair_ts", "pair", "ts"),
        Index("idx_fills_address_pair_ts", "address", "pair", "ts"),
    )


class TradingPosition(Base):
    __tablename__ = "trading_positions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    address = Column(String(64), index=True, nullable=False)
    pair = Column(String(64), index=True, nullable=False)
    is_long = Column(Boolean, nullable=False)
    entry_px = Column(Numeric(38, 18), nullable=False)
    size = Column(Numeric(38, 18), nullable=False)
    opened_at = Column(BigInteger, index=True, nullable=False)
    closed_at = Column(BigInteger, nullable=True)
    pnl_realized = Column(Numeric(38, 18), nullable=False, server_default="0")
    fees = Column(Numeric(38, 18), nullable=False, server_default="0")
    funding = Column(Numeric(38, 18), nullable=False, server_default="0")
    tx_open = Column(String(66), nullable=False)
    tx_close = Column(String(66), nullable=True)

    # Composite indexes for efficient queries
    __table_args__ = (
        Index("idx_trading_positions_address_opened", "address", "opened_at"),
        Index("idx_trading_positions_address_closed", "address", "closed_at"),
    )


class CopyConfiguration(Base):
    __tablename__ = "copy_configurations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    leader_address = Column(String(64), index=True, nullable=False)
    sizing_mode = Column(String(32), nullable=False)  # "FIXED_NOTIONAL" or "PCT_EQUITY"
    sizing_value = Column(Numeric(38, 18), nullable=False)
    max_slippage_bps = Column(BigInteger, nullable=False)
    max_leverage = Column(Numeric(38, 18), nullable=False)
    notional_cap = Column(Numeric(38, 18), nullable=False)
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
    size = Column(Numeric(38, 18), nullable=False)
    entry_price = Column(Numeric(38, 18), nullable=False)
    copy_ratio = Column(Numeric(38, 18), nullable=False)
    opened_at = Column(BigInteger, index=True, nullable=False)
    closed_at = Column(BigInteger, nullable=True)
    pnl = Column(Numeric(38, 18), nullable=False, server_default="0")
    status = Column(String(16), nullable=False)  # "OPEN", "CLOSED", "LIQUIDATED"

    __table_args__ = (
        Index("idx_copy_positions_user_leader", "user_id", "leader_address"),
        Index("idx_copy_positions_user_status", "user_id", "status"),
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
    status = Column(
        String(16), default="PENDING", nullable=False
    )  # PENDING, CONFIRMED, FAILED


class ApiCredential(Base):
    """API credentials with envelope encryption (Phase 1)."""

    __tablename__ = "api_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    provider = Column(String(64), nullable=False)  # e.g., "telegram", "exchange"
    secret_enc = Column(EncryptedJSON, nullable=True)  # Encrypted API secret
    meta_enc = Column(EncryptedJSON, nullable=True)  # Encrypted metadata
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)

    __table_args__ = (Index("idx_api_creds_user_provider", "user_id", "provider"),)


class TxIntent(Base):
    """Transaction intent with idempotency key (Phase 2)."""

    __tablename__ = "tx_intents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    intent_key = Column(
        String(128), unique=True, nullable=False, index=True
    )  # e.g., "open:USER:UUID"
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    status = Column(
        String(32), nullable=False, default="CREATED"
    )  # CREATED|BUILT|SENT|MINED|FAILED|REPLACED
    intent_metadata = Column(Text, nullable=True)  # JSON metadata (market, side, size)

    __table_args__ = (Index("ix_txintent_status_created", "status", "created_at"),)


class TxSend(Base):
    """Transaction send record (Phase 2)."""

    __tablename__ = "tx_sends"

    id = Column(Integer, primary_key=True, autoincrement=True)
    intent_id = Column(Integer, ForeignKey("tx_intents.id"), nullable=False, index=True)
    chain_id = Column(Integer, nullable=False)
    nonce = Column(Integer, nullable=False)
    max_fee_per_gas = Column(BigInteger, nullable=False)
    max_priority_fee_per_gas = Column(BigInteger, nullable=False)
    gas_limit = Column(BigInteger, nullable=False)
    raw_tx = Column(LargeBinary, nullable=True)  # Optional: can be large
    tx_hash = Column(String(66), nullable=False, unique=True, index=True)
    sent_at = Column(DateTime, server_default=func.now(), nullable=False)
    replaced_by = Column(String(66), nullable=True)  # New tx hash if replaced via RBF


class TxReceipt(Base):
    """Transaction receipt (Phase 2)."""

    __tablename__ = "tx_receipts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tx_hash = Column(String(66), nullable=False, unique=True, index=True)
    status = Column(Integer, nullable=False)  # 1=success, 0=failed
    block_number = Column(Integer, nullable=False)
    gas_used = Column(BigInteger, nullable=False)
    effective_gas_price = Column(BigInteger, nullable=False)
    mined_at = Column(DateTime, server_default=func.now(), nullable=False)


# ========== Phase 4: Persistence & Indexing ==========


class SyncState(Base):
    """Sync state for indexers (Phase 4)."""

    __tablename__ = "sync_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), unique=True, nullable=False)  # e.g., "avantis_indexer"
    last_block = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=func.now(), nullable=False)


class IndexedFill(Base):
    """Indexed trade fill/execution record (Phase 4)."""

    __tablename__ = "indexed_fills"
    __table_args__ = (
        Index("ix_ifills_user_sym_block", "user_address", "symbol", "block_number"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_address = Column(String(42), index=True, nullable=False)
    symbol = Column(String(32), index=True, nullable=False)  # "BTC-USD"
    is_long = Column(Boolean, nullable=False)
    usd_1e6 = Column(BigInteger, nullable=False)  # +open/-close notionals
    collateral_usdc_1e6 = Column(BigInteger, default=0, nullable=False)
    tx_hash = Column(String(66), index=True, nullable=False)
    block_number = Column(Integer, index=True, nullable=False)
    ts = Column(DateTime, default=func.now(), nullable=False)
    meta = Column(Text, default="{}", nullable=False)  # JSON as TEXT for SQLite compat


class UserPosition(Base):
    """Aggregated user position state (Phase 4)."""

    __tablename__ = "user_positions"

    __table_args__ = (
        Index("ix_user_pos_user_symbol", "user_address", "symbol", unique=True),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_address = Column(String(42), index=True, nullable=False)
    symbol = Column(String(32), index=True, nullable=False, default="BTC-USD")
    is_long = Column(Boolean, nullable=False)
    size_usd_1e6 = Column(
        BigInteger, default=0, nullable=False
    )  # signed notionals; 0 = flat
    entry_collateral_1e6 = Column(BigInteger, default=0, nullable=False)
    realized_pnl_1e6 = Column(BigInteger, default=0, nullable=False)
    updated_at = Column(DateTime, default=func.now(), nullable=False)
