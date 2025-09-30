"""Integration tests for credentials repository (Phase 1)."""

import pytest
from moto import mock_aws
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.database.models import ApiCredential, Base


@mock_aws
class TestCredentialsRepository:
    """Test credentials repository with real DB and mocked KMS."""

    @pytest.fixture
    def db_session(self, monkeypatch):
        """Create in-memory SQLite session."""
        import sys

        import boto3

        # Setup mocked KMS
        kms = boto3.client("kms", region_name="us-east-1")
        key = kms.create_key()["KeyMetadata"]["KeyId"]

        monkeypatch.setenv("KMS_KEY_ID", key)
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("ENCRYPTION_CONTEXT_APP", "test-app")
        monkeypatch.setenv("ENCRYPTION_DEK_BYTES", "32")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
        monkeypatch.setenv("BASE_RPC_URL", "https://test.rpc")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

        # Reload modules to pick up env vars
        for mod in [
            "src.config.settings",
            "src.security.crypto",
            "src.database.types",
            "src.database.models",
        ]:
            if mod in sys.modules:
                del sys.modules[mod]

        # Now import models with fresh settings
        from src.database.models import Base

        # Create in-memory database
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        session = Session(engine)
        yield session
        session.close()

    def test_upsert_new_credential(self, db_session):
        """Test creating new API credential."""
        from src.repositories.credentials_repo import upsert_api_secret

        secret = {"api_key": "secret123", "api_secret": "verysecret"}
        meta = {"environment": "production"}

        result = upsert_api_secret(
            db=db_session,
            user_id=123,
            provider="test_exchange",
            secret=secret,
            meta=meta,
        )

        db_session.commit()

        assert result.id is not None
        assert result.user_id == 123
        assert result.provider == "test_exchange"
        # Verify encryption/decryption works
        assert result.secret_enc == secret
        assert result.meta_enc == meta

    def test_upsert_update_existing(self, db_session):
        """Test updating existing API credential."""
        from src.repositories.credentials_repo import upsert_api_secret

        # Create initial
        secret1 = {"api_key": "old_key"}
        upsert_api_secret(db_session, 123, "test_provider", secret1)
        db_session.commit()

        # Update
        secret2 = {"api_key": "new_key", "additional": "data"}
        result = upsert_api_secret(db_session, 123, "test_provider", secret2)
        db_session.commit()

        # Verify update
        assert result.secret_enc == secret2

        # Verify only one record exists
        count = db_session.query(ApiCredential).filter_by(user_id=123).count()
        assert count == 1

    def test_get_api_secret(self, db_session):
        """Test retrieving API secret."""
        from src.repositories.credentials_repo import get_api_secret, upsert_api_secret

        secret = {"token": "secret_token"}
        upsert_api_secret(db_session, 456, "test_api", secret)
        db_session.commit()

        retrieved = get_api_secret(db_session, 456, "test_api")
        assert retrieved == secret

    def test_get_nonexistent_secret(self, db_session):
        """Test retrieving nonexistent secret returns None."""
        from src.repositories.credentials_repo import get_api_secret

        result = get_api_secret(db_session, 999, "nonexistent")
        assert result is None

    def test_delete_api_secret(self, db_session):
        """Test deleting API secret."""
        from src.repositories.credentials_repo import (
            delete_api_secret,
            get_api_secret,
            upsert_api_secret,
        )

        # Create
        upsert_api_secret(db_session, 789, "test_provider", {"key": "value"})
        db_session.commit()

        # Delete
        deleted = delete_api_secret(db_session, 789, "test_provider")
        db_session.commit()

        assert deleted is True

        # Verify deleted
        result = get_api_secret(db_session, 789, "test_provider")
        assert result is None

    def test_delete_nonexistent_returns_false(self, db_session):
        """Test deleting nonexistent secret returns False."""
        from src.repositories.credentials_repo import delete_api_secret

        result = delete_api_secret(db_session, 999, "nonexistent")
        assert result is False
