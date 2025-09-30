"""Tests for key vault security."""

import os

import pytest

from src.security.key_vault import LocalFernetKeyVault, WalletEncryption


class TestLocalFernetKeyVault:
    """Test local Fernet key vault."""

    def test_generate_wrapped_dek(self):
        """Test DEK generation and wrapping."""
        # Generate a test wrapping key
        wrapping_key = os.urandom(32)
        wrapping_key_b64 = wrapping_key.hex()

        vault = LocalFernetKeyVault(wrapping_key_b64)

        # Generate wrapped DEK
        wrapped_dek, dek_plaintext = vault.generate_wrapped_dek()

        # Verify we got bytes
        assert isinstance(wrapped_dek, bytes)
        assert isinstance(dek_plaintext, bytes)
        assert len(dek_plaintext) == 32  # 256-bit DEK

        # Verify we can unwrap
        unwrapped_dek = vault.unwrap_dek(wrapped_dek)
        assert unwrapped_dek == dek_plaintext

    def test_wrap_unwrap_roundtrip(self):
        """Test wrapping and unwrapping roundtrip."""
        wrapping_key = os.urandom(32)
        wrapping_key_b64 = wrapping_key.hex()

        vault = LocalFernetKeyVault(wrapping_key_b64)

        # Generate and unwrap multiple times
        for _ in range(5):
            wrapped_dek, dek_plaintext = vault.generate_wrapped_dek()
            unwrapped_dek = vault.unwrap_dek(wrapped_dek)
            assert unwrapped_dek == dek_plaintext

    def test_different_keys_produce_different_wrapped_deks(self):
        """Test that different wrapping keys produce different wrapped DEKs."""
        key1 = os.urandom(32).hex()
        key2 = os.urandom(32).hex()

        vault1 = LocalFernetKeyVault(key1)
        vault2 = LocalFernetKeyVault(key2)

        wrapped1, _ = vault1.generate_wrapped_dek()
        wrapped2, _ = vault2.generate_wrapped_dek()

        assert wrapped1 != wrapped2


class TestWalletEncryption:
    """Test wallet encryption with envelope encryption."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test encryption and decryption roundtrip."""
        # Create test vault
        wrapping_key = os.urandom(32).hex()
        vault = LocalFernetKeyVault(wrapping_key)
        encryption = WalletEncryption(vault)

        # Test private key
        private_key_hex = "1234567890abcdef" * 8  # 64 hex chars = 32 bytes

        # Encrypt
        wrapped_dek, encrypted_privkey = encryption.create_encrypted_wallet(
            private_key_hex
        )

        # Verify we got bytes
        assert isinstance(wrapped_dek, bytes)
        assert isinstance(encrypted_privkey, bytes)

        # Decrypt
        decrypted_privkey = encryption.decrypt_wallet(wrapped_dek, encrypted_privkey)

        # Verify roundtrip
        assert decrypted_privkey == private_key_hex

    def test_different_private_keys_produce_different_ciphertexts(self):
        """Test that different private keys produce different ciphertexts."""
        wrapping_key = os.urandom(32).hex()
        vault = LocalFernetKeyVault(wrapping_key)
        encryption = WalletEncryption(vault)

        privkey1 = "1234567890abcdef" * 8
        privkey2 = "fedcba0987654321" * 8

        _, encrypted1 = encryption.create_encrypted_wallet(privkey1)
        _, encrypted2 = encryption.create_encrypted_wallet(privkey2)

        assert encrypted1 != encrypted2

    def test_tampered_ciphertext_fails(self):
        """Test that tampered ciphertext fails to decrypt."""
        wrapping_key = os.urandom(32).hex()
        vault = LocalFernetKeyVault(wrapping_key)
        encryption = WalletEncryption(vault)

        private_key_hex = "1234567890abcdef" * 8
        wrapped_dek, encrypted_privkey = encryption.create_encrypted_wallet(
            private_key_hex
        )

        # Tamper with ciphertext
        tampered_ciphertext = encrypted_privkey[:-1] + b"X"

        # Should raise exception
        with pytest.raises(Exception):
            encryption.decrypt_wallet(wrapped_dek, tampered_ciphertext)
