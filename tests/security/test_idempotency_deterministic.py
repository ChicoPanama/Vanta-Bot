"""Tests for deterministic idempotency keys (SEC-001)."""

import time
from unittest.mock import MagicMock

import pytest

from src.blockchain.avantis.service import make_intent_key


class TestDeterministicIdempotency:
    """Test that idempotency keys are deterministic and prevent duplicates."""

    def test_same_parameters_same_key(self):
        """Test that identical requests generate the same key within time bucket."""
        # Same parameters should generate same key
        key1 = make_intent_key(
            user_id=123, action="open", symbol="BTC-USD", side="LONG", qty_1e6=10_000_000
        )
        key2 = make_intent_key(
            user_id=123, action="open", symbol="BTC-USD", side="LONG", qty_1e6=10_000_000
        )

        assert key1 == key2, "Identical requests must generate identical keys"
        assert len(key1) == 64, "SHA256 hash should be 64 hex characters"

    def test_different_parameters_different_keys(self):
        """Test that different requests generate different keys."""
        base_params = {
            "user_id": 123,
            "action": "open",
            "symbol": "BTC-USD",
            "side": "LONG",
            "qty_1e6": 10_000_000,
        }

        key_base = make_intent_key(**base_params)

        # Different user
        key_user = make_intent_key(**{**base_params, "user_id": 456})
        assert key_user != key_base

        # Different symbol
        key_symbol = make_intent_key(**{**base_params, "symbol": "ETH-USD"})
        assert key_symbol != key_base

        # Different side
        key_side = make_intent_key(**{**base_params, "side": "SHORT"})
        assert key_side != key_base

        # Different quantity
        key_qty = make_intent_key(**{**base_params, "qty_1e6": 20_000_000})
        assert key_qty != key_base

    def test_time_bucket_prevents_long_term_collisions(self):
        """Test that time bucketing prevents collisions across time."""
        # Get key at time T
        key1 = make_intent_key(
            user_id=123,
            action="open",
            symbol="BTC-USD",
            side="LONG",
            qty_1e6=10_000_000,
            bucket_s=1,
        )

        # Wait for bucket to change
        time.sleep(1.1)

        # Get key at time T+1
        key2 = make_intent_key(
            user_id=123,
            action="open",
            symbol="BTC-USD",
            side="LONG",
            qty_1e6=10_000_000,
            bucket_s=1,
        )

        assert key1 != key2, "Keys should differ across time buckets"

    def test_close_vs_open_different_keys(self):
        """Test that open and close actions generate different keys."""
        key_open = make_intent_key(
            user_id=123, action="open", symbol="BTC-USD", side="LONG", qty_1e6=10_000_000
        )

        key_close = make_intent_key(
            user_id=123, action="close", symbol="BTC-USD", side=None, qty_1e6=10_000_000
        )

        assert key_open != key_close, "Open and close must have different keys"

    def test_none_values_handled(self):
        """Test that None values are handled correctly."""
        # Close action with no side or price
        key = make_intent_key(
            user_id=123,
            action="close",
            symbol="BTC-USD",
            side=None,
            qty_1e6=5_000_000,
            price_1e6=None,
        )

        assert isinstance(key, str)
        assert len(key) == 64

    def test_idempotency_across_retries(self):
        """Test that retries within same second get deduplicated."""
        # Simulate 3 rapid retries of the same request
        keys = []
        for _ in range(3):
            key = make_intent_key(
                user_id=123,
                action="open",
                symbol="BTC-USD",
                side="LONG",
                qty_1e6=10_000_000,
            )
            keys.append(key)
            # Small delay but within same second
            time.sleep(0.1)

        # All should be identical (within 1s bucket)
        assert (
            len(set(keys)) == 1
        ), "Retries within time bucket should generate same key"

    def test_concurrent_requests_same_key(self):
        """Test that concurrent requests get the same key (no UUID randomness)."""
        # Simulate concurrent requests by generating multiple keys rapidly
        keys = [
            make_intent_key(
                user_id=123,
                action="open",
                symbol="BTC-USD",
                side="LONG",
                qty_1e6=10_000_000,
            )
            for _ in range(10)
        ]

        # All should be identical since parameters and time are same
        assert (
            len(set(keys)) == 1
        ), "Concurrent identical requests must generate same key"


class TestIdempotencyIntegration:
    """Integration test with database to verify no duplicate sends."""

    def test_duplicate_open_creates_one_intent(self):
        """Test that duplicate open calls create only one TxIntent."""
        from unittest.mock import Mock, patch

        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from src.database.models import Base, TxIntent

        # Create in-memory database
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        session = Session(engine)

        # Mock AvantisService with same parameters
        from src.blockchain.avantis.service import make_intent_key

        # Generate key for a specific trade
        key1 = make_intent_key(
            user_id=123, action="open", symbol="BTC-USD", side="LONG", qty_1e6=10_000_000
        )

        key2 = make_intent_key(
            user_id=123, action="open", symbol="BTC-USD", side="LONG", qty_1e6=10_000_000
        )

        # Keys should be identical
        assert key1 == key2

        # Try to create two intents with same key
        intent1 = TxIntent(intent_key=key1, status="CREATED", intent_metadata="{}")
        session.add(intent1)
        session.commit()

        # Second intent with same key should fail due to unique constraint
        intent2 = TxIntent(intent_key=key2, status="CREATED", intent_metadata="{}")
        session.add(intent2)

        with pytest.raises(Exception):  # Should raise IntegrityError
            session.commit()

        session.rollback()

        # Verify only one intent exists
        count = session.query(TxIntent).filter_by(intent_key=key1).count()
        assert count == 1, "Only one intent should exist for duplicate request"

        session.close()

