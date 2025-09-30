"""Encrypted SQLAlchemy types using envelope encryption (Phase 1)."""

import json
import logging
import pickle
from dataclasses import asdict
from typing import Any, Optional

from sqlalchemy import LargeBinary
from sqlalchemy.types import TypeDecorator

from src.security.crypto import CipherBlob, decrypt_blob, encrypt_blob

logger = logging.getLogger(__name__)


class EncryptedBytes(TypeDecorator):
    """SQLAlchemy type for encrypted bytes using envelope encryption."""

    impl = LargeBinary
    cache_ok = True

    def process_bind_param(
        self, value: Optional[bytes], dialect: Any
    ) -> Optional[bytes]:
        """Encrypt bytes before storing in database."""
        if value is None:
            return None

        try:
            # Encrypt with envelope encryption
            blob = encrypt_blob(value)
            # Serialize CipherBlob to bytes
            return pickle.dumps(asdict(blob))
        except Exception as e:
            logger.error(f"Failed to encrypt bytes: {e}")
            raise

    def process_result_value(
        self, value: Optional[bytes], dialect: Any
    ) -> Optional[bytes]:
        """Decrypt bytes when loading from database."""
        if value is None:
            return None

        try:
            # Deserialize CipherBlob
            blob_dict = pickle.loads(value)
            blob = CipherBlob(**blob_dict)
            # Decrypt
            return decrypt_blob(blob)
        except Exception as e:
            logger.error(f"Failed to decrypt bytes: {e}")
            raise


class EncryptedJSON(TypeDecorator):
    """SQLAlchemy type for encrypted JSON using envelope encryption."""

    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value: Optional[Any], dialect: Any) -> Optional[bytes]:
        """Encrypt JSON before storing in database."""
        if value is None:
            return None

        try:
            # Serialize to JSON bytes
            json_bytes = json.dumps(value).encode("utf-8")
            # Encrypt with envelope encryption
            blob = encrypt_blob(json_bytes)
            # Serialize CipherBlob to bytes
            return pickle.dumps(asdict(blob))
        except Exception as e:
            logger.error(f"Failed to encrypt JSON: {e}")
            raise

    def process_result_value(
        self, value: Optional[bytes], dialect: Any
    ) -> Optional[Any]:
        """Decrypt JSON when loading from database."""
        if value is None:
            return None

        try:
            # Deserialize CipherBlob
            blob_dict = pickle.loads(value)
            blob = CipherBlob(**blob_dict)
            # Decrypt
            json_bytes = decrypt_blob(blob)
            # Parse JSON
            return json.loads(json_bytes.decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to decrypt JSON: {e}")
            raise


class EncryptedString(TypeDecorator):
    """SQLAlchemy type for encrypted strings using envelope encryption."""

    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value: Optional[str], dialect: Any) -> Optional[bytes]:
        """Encrypt string before storing in database."""
        if value is None:
            return None

        try:
            # Convert to bytes
            str_bytes = value.encode("utf-8")
            # Encrypt with envelope encryption
            blob = encrypt_blob(str_bytes)
            # Serialize CipherBlob to bytes
            return pickle.dumps(asdict(blob))
        except Exception as e:
            logger.error(f"Failed to encrypt string: {e}")
            raise

    def process_result_value(
        self, value: Optional[bytes], dialect: Any
    ) -> Optional[str]:
        """Decrypt string when loading from database."""
        if value is None:
            return None

        try:
            # Deserialize CipherBlob
            blob_dict = pickle.loads(value)
            blob = CipherBlob(**blob_dict)
            # Decrypt
            str_bytes = decrypt_blob(blob)
            # Decode to string
            return str_bytes.decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to decrypt string: {e}")
            raise
