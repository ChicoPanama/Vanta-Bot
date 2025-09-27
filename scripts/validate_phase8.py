#!/usr/bin/env python3
"""
Phase 8 Validation Script
Tests copy-trading functionality end-to-end
"""
import asyncio
import os
import sys
import sqlite3
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_database_schema():
    """Test database schema and initialization"""
    print("🔍 Testing database schema...")
    
    db_path = os.getenv("USER_PREFS_DB", "vanta_user_prefs.db")
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return False
    
    con = sqlite3.connect(db_path)
    try:
        # Check schema
        cur = con.execute("SELECT sql FROM sqlite_master WHERE name='user_follow_configs'")
        schema = cur.fetchone()
        if not schema:
            print("❌ user_follow_configs table not found")
            return False
        
        print("✅ user_follow_configs table exists")
        
        # Check for test data
        cur = con.execute("SELECT COUNT(*) FROM user_follow_configs")
        count = cur.fetchone()[0]
        print(f"✅ Found {count} follow configurations")
        
        return True
    finally:
        con.close()

def test_copy_store():
    """Test copy store functionality"""
    print("\n🔍 Testing copy store...")
    
    try:
        from src.services.copytrading.copy_store import init, get, put, remove, list_follows
        
        # Initialize
        init()
        print("✅ Copy store initialized")
        
        # Test basic operations
        test_user = 99999
        test_trader = "test_trader_validation"
        
        # Get defaults
        cfg = get(test_user, test_trader)
        print(f"✅ Default config loaded: {len(cfg)} settings")
        
        # Put configuration
        test_config = {
            "auto_copy": True,
            "notify": True,
            "sizing_mode": "FIXED_USD",
            "fixed_usd": 500.0,
            "max_leverage": 25
        }
        put(test_user, test_trader, test_config)
        print("✅ Configuration stored")
        
        # Retrieve and verify
        retrieved = get(test_user, test_trader)
        assert retrieved["auto_copy"] == True
        assert retrieved["fixed_usd"] == 500.0
        print("✅ Configuration retrieved correctly")
        
        # List follows
        follows = list_follows(test_user)
        assert len(follows) == 1
        assert follows[0][0] == test_trader
        print("✅ List follows works")
        
        # Clean up
        remove(test_user, test_trader)
        follows_after = list_follows(test_user)
        assert len(follows_after) == 0
        print("✅ Remove works")
        
        return True
    except Exception as e:
        print(f"❌ Copy store test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_copy_service():
    """Test copy service functionality"""
    print("\n🔍 Testing copy service...")
    
    try:
        from src.services.copytrading.copy_service import init, get_cfg, set_cfg, unfollow, list_follows
        
        # Initialize
        init()
        print("✅ Copy service initialized")
        
        # Test operations
        test_user = 88888
        test_trader = "service_test_trader"
        
        # Set configuration
        test_config = {
            "auto_copy": False,
            "notify": True,
            "sizing_mode": "MIRROR"
        }
        set_cfg(test_user, test_trader, test_config)
        print("✅ Service set_cfg works")
        
        # Get configuration
        cfg = get_cfg(test_user, test_trader)
        assert cfg["notify"] == True
        print("✅ Service get_cfg works")
        
        # List follows
        follows = list_follows(test_user)
        assert len(follows) == 1
        print("✅ Service list_follows works")
        
        # Unfollow
        unfollow(test_user, test_trader)
        follows_after = list_follows(test_user)
        assert len(follows_after) == 0
        print("✅ Service unfollow works")
        
        return True
    except Exception as e:
        print(f"❌ Copy service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_copy_executor():
    """Test copy executor availability"""
    print("\n🔍 Testing copy executor...")
    
    try:
        from src.services.trading.copy_executor import follow, status
        print("✅ Copy executor module loaded")
        
        # Test that functions exist and are callable
        assert callable(follow)
        assert callable(status)
        print("✅ Copy executor functions available")
        
        return True
    except Exception as e:
        print(f"❌ Copy executor test failed: {e}")
        return False

async def test_signal_flow():
    """Test the complete signal flow"""
    print("\n🔍 Testing signal flow...")
    
    try:
        from src.services.copytrading.alerts import on_trader_signal
        from src.services.copytrading.copy_service import set_cfg
        
        # Set up test configuration
        test_user = 77777
        test_trader = "signal_test_trader"
        
        # Create a mock bot (we won't actually send messages)
        class MockBot:
            async def send_message(self, chat_id, text, parse_mode=None):
                print(f"📱 Mock alert sent to {chat_id}: {text[:50]}...")
                return True
        
        bot = MockBot()
        
        # Set up follow config
        set_cfg(test_user, test_trader, {
            "auto_copy": True,
            "notify": True,
            "sizing_mode": "MIRROR",
            "per_trade_cap_usd": 1000
        })
        
        # Test signal
        signal = {
            "pair": "ETH/USD",
            "side": "LONG",
            "lev": 10,
            "notional_usd": 500,
            "collateral_usdc": 50
        }
        
        await on_trader_signal(bot, test_user, test_trader, signal)
        print("✅ Signal flow completed")
        
        # Clean up
        from src.services.copytrading.copy_service import unfollow
        unfollow(test_user, test_trader)
        
        return True
    except Exception as e:
        print(f"❌ Signal flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_handler_registration():
    """Test that handlers can be imported and registered"""
    print("\n🔍 Testing handler registration...")
    
    try:
        from src.bot.handlers.copy_handlers import register as register_copy
        from src.bot.handlers.alfa_handlers import alfa_handlers
        
        print("✅ Copy handlers import successful")
        print(f"✅ Alfa handlers loaded: {len(alfa_handlers)} handlers")
        
        # Test that register function exists
        assert callable(register_copy)
        print("✅ Handler registration functions available")
        
        return True
    except Exception as e:
        print(f"❌ Handler registration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all validation tests"""
    print("🚀 Phase 8 Validation Suite")
    print("=" * 50)
    
    tests = [
        ("Database Schema", test_database_schema),
        ("Copy Store", test_copy_store),
        ("Copy Service", test_copy_service),
        ("Copy Executor", test_copy_executor),
        ("Signal Flow", test_signal_flow),
        ("Handler Registration", test_handler_registration),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Phase 8 is ready for production.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
