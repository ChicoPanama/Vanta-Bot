#!/usr/bin/env python3
"""
Test script for the validation module.

This script tests the validation functions with various scenarios.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.config.validate import (
    validate_all,
    validate_encryption_key,
    validate_database_url,
    validate_telegram_token,
    validate_private_key,
)


def test_encryption_key_validation():
    """Test encryption key validation"""
    print("Testing encryption key validation...")
    
    # Test valid key
    os.environ["ENCRYPTION_KEY"] = "test_key_that_is_32_bytes_long_!"
    try:
        validate_encryption_key()
        print("❌ Should have failed with invalid key")
        return False
    except RuntimeError:
        print("✅ Correctly rejected invalid key")
    
    # Test missing key (should pass if not required)
    del os.environ["ENCRYPTION_KEY"]
    try:
        validate_encryption_key()
        print("✅ Correctly handled missing key")
        return True
    except RuntimeError as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_database_url_validation():
    """Test database URL validation"""
    print("Testing database URL validation...")
    
    # Test valid URL
    os.environ["DATABASE_URL"] = "postgresql://user:pass@host:5432/db"
    try:
        validate_database_url()
        print("✅ Valid URL accepted")
    except RuntimeError as e:
        print(f"❌ Valid URL rejected: {e}")
        return False
    
    # Test invalid URL
    os.environ["DATABASE_URL"] = "invalid://url"
    try:
        validate_database_url()
        print("❌ Should have rejected invalid URL")
        return False
    except RuntimeError:
        print("✅ Correctly rejected invalid URL")
    
    # Test missing URL (should pass if not required)
    del os.environ["DATABASE_URL"]
    try:
        validate_database_url()
        print("✅ Correctly handled missing URL")
        return True
    except RuntimeError as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_telegram_token_validation():
    """Test Telegram token validation"""
    print("Testing Telegram token validation...")
    
    # Test valid token
    os.environ["TELEGRAM_BOT_TOKEN"] = "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567"
    try:
        validate_telegram_token()
        print("✅ Valid token accepted")
    except RuntimeError as e:
        print(f"❌ Valid token rejected: {e}")
        return False
    
    # Test invalid token
    os.environ["TELEGRAM_BOT_TOKEN"] = "invalid_token"
    try:
        validate_telegram_token()
        print("❌ Should have rejected invalid token")
        return False
    except RuntimeError:
        print("✅ Correctly rejected invalid token")
    
    # Test missing token (should pass if not required)
    del os.environ["TELEGRAM_BOT_TOKEN"]
    try:
        validate_telegram_token()
        print("✅ Correctly handled missing token")
        return True
    except RuntimeError as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_private_key_validation():
    """Test private key validation"""
    print("Testing private key validation...")
    
    # Test valid key with 0x prefix
    os.environ["TRADER_PRIVATE_KEY"] = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    try:
        validate_private_key()
        print("✅ Valid key with 0x prefix accepted")
    except RuntimeError as e:
        print(f"❌ Valid key rejected: {e}")
        return False
    
    # Test valid key without 0x prefix
    os.environ["TRADER_PRIVATE_KEY"] = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    try:
        validate_private_key()
        print("✅ Valid key without 0x prefix accepted")
    except RuntimeError as e:
        print(f"❌ Valid key rejected: {e}")
        return False
    
    # Test invalid key
    os.environ["TRADER_PRIVATE_KEY"] = "invalid_key"
    try:
        validate_private_key()
        print("❌ Should have rejected invalid key")
        return False
    except RuntimeError:
        print("✅ Correctly rejected invalid key")
    
    # Test missing key (should pass if not required)
    del os.environ["TRADER_PRIVATE_KEY"]
    try:
        validate_private_key()
        print("✅ Correctly handled missing key")
        return True
    except RuntimeError as e:
        print(f"❌ Unexpected error: {e}")
        return False


def main():
    """Run all validation tests"""
    print("🧪 Testing validation module...\n")
    
    tests = [
        test_encryption_key_validation,
        test_database_url_validation,
        test_telegram_token_validation,
        test_private_key_validation,
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All validation tests passed!")
        return 0
    else:
        print("❌ Some validation tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
