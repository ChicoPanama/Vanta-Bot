#!/usr/bin/env python3
"""DEK rotation script - rewrap all encrypted blobs with current KMS key (Phase 1)."""

import logging
import pickle
import sys
from dataclasses import asdict

from sqlalchemy.orm import Session

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _rewrap_blob(blob_bytes: bytes) -> bytes:
    """Rewrap a single encrypted blob with current KMS key.

    Args:
        blob_bytes: Pickled CipherBlob

    Returns:
        Re-wrapped blob bytes
    """
    from src.security.crypto import CipherBlob, rewrap_encrypted_dek

    blob_dict = pickle.loads(blob_bytes)
    blob = CipherBlob(**blob_dict)

    # Rewrap the DEK
    new_dek_encrypted = rewrap_encrypted_dek(blob.dek_encrypted)

    # Update blob with new wrapped DEK
    blob_dict["dek_encrypted"] = new_dek_encrypted

    return pickle.dumps(blob_dict)


def main() -> None:
    """Rewrap all encrypted database fields with current KMS key."""
    from src.config.settings import settings
    from src.database.models import ApiCredential, Wallet
    from src.database.session import get_engine

    logger.info("🔄 Starting DEK rotation...")
    logger.info(f"Current KMS Key: {settings.KMS_KEY_ID or settings.AWS_KMS_KEY_ID}")

    engine = get_engine()
    with Session(engine) as db:
        # Rewrap ApiCredential secrets
        api_creds = db.query(ApiCredential).all()
        logger.info(f"Found {len(api_creds)} API credentials to rewrap")

        for rec in api_creds:
            if rec.secret_enc:
                rec.secret_enc = _rewrap_blob(rec.secret_enc)
            if rec.meta_enc:
                rec.meta_enc = _rewrap_blob(rec.meta_enc)

        # Rewrap Wallet private keys
        wallets = db.query(Wallet).filter(Wallet.privkey_enc.isnot(None)).all()
        logger.info(f"Found {len(wallets)} wallets with encrypted keys to rewrap")

        for wallet in wallets:
            if wallet.privkey_enc:
                wallet.privkey_enc = _rewrap_blob(wallet.privkey_enc)

        # Commit all changes
        db.commit()
        logger.info("✅ DEK rotation complete")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"❌ DEK rotation failed: {e}")
        sys.exit(1)
