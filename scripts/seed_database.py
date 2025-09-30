#!/usr/bin/env python3
"""Database seeding script for development and testing.

Creates minimal test data for local development:
- Test users
- Sample trades
- Market positions
- Risk policies

Run this after migrations to populate a clean database with test data.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config.settings import settings
from src.database.models import (
    Credential,
    IndexedFill,
    RiskPolicy,
    Signal,
    TpSlOrder,
    Trade,
    UserPosition,
)

# Test data constants
TEST_USER_ID = 123456789
TEST_USER_ADDRESS = "0x1234567890123456789012345678901234567890"
TEST_SYMBOLS = ["BTC", "ETH", "SOL"]


def create_test_users(db):
    """Create test users with credentials."""
    print("Creating test users...")

    # Test user credential
    cred = Credential(
        tg_user_id=TEST_USER_ID,
        wallet_address=TEST_USER_ADDRESS,
        encrypted_private_key=b"test_encrypted_key",  # Not real, for testing only
        kek_id="test_kek",
        created_at=datetime.utcnow(),
    )
    db.add(cred)

    print(f"  ✅ Created test user {TEST_USER_ID}")


def create_risk_policies(db):
    """Create test risk policies."""
    print("Creating risk policies...")

    policy = RiskPolicy(
        tg_user_id=TEST_USER_ID,
        max_position_usd=Decimal("10000"),
        max_leverage=100,
        circuit_breaker_enabled=True,
        daily_loss_limit_pct=Decimal("0.20"),
        created_at=datetime.utcnow(),
    )
    db.add(policy)

    print(f"  ✅ Created risk policy for user {TEST_USER_ID}")


def create_sample_positions(db):
    """Create sample positions."""
    print("Creating sample positions...")

    positions = [
        UserPosition(
            user_address=TEST_USER_ADDRESS,
            symbol="BTC",
            is_long=True,
            size_usd_1e6=50_000_000_000,  # $50,000
            collateral_usdc_1e6=1_000_000_000,  # $1,000
            entry_price=Decimal("65000.00"),
            liquidation_price=Decimal("60000.00"),
            last_updated=datetime.utcnow(),
        ),
        UserPosition(
            user_address=TEST_USER_ADDRESS,
            symbol="ETH",
            is_long=False,
            size_usd_1e6=20_000_000_000,  # $20,000
            collateral_usdc_1e6=500_000_000,  # $500
            entry_price=Decimal("3500.00"),
            liquidation_price=Decimal("3800.00"),
            last_updated=datetime.utcnow(),
        ),
    ]

    for pos in positions:
        db.add(pos)
        print(
            f"  ✅ Created {pos.symbol} position ({'LONG' if pos.is_long else 'SHORT'})"
        )


def create_sample_trades(db):
    """Create sample trade history."""
    print("Creating sample trades...")

    trades = [
        Trade(
            tg_user_id=TEST_USER_ID,
            intent_key="test_trade_1",
            symbol="BTC",
            side="LONG",
            collateral_usdc=Decimal("1000"),
            leverage_x=Decimal("50"),
            slippage_pct=Decimal("0.5"),
            status="SENT",
            tx_hash="0xabc123...",
            created_at=datetime.utcnow() - timedelta(hours=2),
        ),
        Trade(
            tg_user_id=TEST_USER_ID,
            intent_key="test_trade_2",
            symbol="ETH",
            side="SHORT",
            collateral_usdc=Decimal("500"),
            leverage_x=Decimal("40"),
            slippage_pct=Decimal("0.5"),
            status="CONFIRMED",
            tx_hash="0xdef456...",
            created_at=datetime.utcnow() - timedelta(hours=1),
        ),
    ]

    for trade in trades:
        db.add(trade)
        print(f"  ✅ Created {trade.symbol} {trade.side} trade")


def create_sample_signals(db):
    """Create sample signals."""
    print("Creating sample signals...")

    signal = Signal(
        intent_key="test_signal_1",
        tg_user_id=TEST_USER_ID,
        symbol="SOL",
        side="LONG",
        collateral_usdc=Decimal("300"),
        leverage_x=Decimal("30"),
        slippage_pct=Decimal("0.5"),
        reduce_usdc=None,
        status="APPROVED",
        source="test",
        created_at=datetime.utcnow(),
    )
    db.add(signal)

    print(f"  ✅ Created test signal for {signal.symbol}")


def create_sample_tpsl_orders(db):
    """Create sample TP/SL orders."""
    print("Creating TP/SL orders...")

    tpsl = TpSlOrder(
        tg_user_id=TEST_USER_ID,
        symbol="BTC",
        is_long=True,
        take_profit_price=Decimal("70000.00"),
        stop_loss_price=Decimal("63000.00"),
        active=True,
        created_at=datetime.utcnow(),
    )
    db.add(tpsl)

    print(f"  ✅ Created TP/SL order for {tpsl.symbol}")


def main():
    """Main seeding function."""
    print("\n" + "=" * 60)
    print("Database Seeding Script")
    print("=" * 60 + "\n")

    # Connect to database
    db_url = settings.DATABASE_URL.replace("sqlite+aiosqlite:", "sqlite:")
    engine = create_engine(db_url, echo=False)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Check if data already exists
        existing_cred = db.query(Credential).filter_by(tg_user_id=TEST_USER_ID).first()
        if existing_cred:
            print(f"\n⚠️  Test data already exists for user {TEST_USER_ID}")
            response = input("Clear existing data and reseed? (y/N): ")
            if response.lower() != "y":
                print("Aborted.")
                return

            # Clear existing test data
            print("\nClearing existing test data...")
            db.query(TpSlOrder).filter_by(tg_user_id=TEST_USER_ID).delete()
            db.query(Signal).filter_by(tg_user_id=TEST_USER_ID).delete()
            db.query(Trade).filter_by(tg_user_id=TEST_USER_ID).delete()
            db.query(UserPosition).filter_by(user_address=TEST_USER_ADDRESS).delete()
            db.query(RiskPolicy).filter_by(tg_user_id=TEST_USER_ID).delete()
            db.query(Credential).filter_by(tg_user_id=TEST_USER_ID).delete()
            db.commit()
            print("  ✅ Cleared existing data\n")

        # Create test data
        create_test_users(db)
        create_risk_policies(db)
        create_sample_positions(db)
        create_sample_trades(db)
        create_sample_signals(db)
        create_sample_tpsl_orders(db)

        # Commit all changes
        db.commit()

        print("\n" + "=" * 60)
        print("✅ Database seeding completed successfully!")
        print("=" * 60)
        print(f"\nTest User ID: {TEST_USER_ID}")
        print(f"Test Wallet:  {TEST_USER_ADDRESS}")
        print("\n⚠️  NOTE: This is test data for development only!")
        print("    Do not use in production!\n")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
