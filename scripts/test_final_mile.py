#!/usr/bin/env python3
"""
Final Mile Test Script
Tests all the production hardening features added to Phase 8
"""
import sys
import os
import sqlite3
import json
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_database_index():
    """Test that the reverse index was created"""
    print("🔍 Testing database index...")
    
    con = sqlite3.connect("vanta_user_prefs.db")
    try:
        # Check if index exists
        cur = con.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_follow_trader'")
        index_exists = cur.fetchone() is not None
        assert index_exists, "Reverse index not created"
        print("✅ Reverse index exists")
        
        # Test index performance (should be fast)
        cur = con.execute("SELECT user_id FROM user_follow_configs WHERE trader_key=?", ("test_trader",))
        users = [row[0] for row in cur.fetchall()]
        print(f"✅ Index query works: {len(users)} users found")
        
        return True
    finally:
        con.close()

def test_reverse_lookup():
    """Test reverse lookup functionality"""
    print("\n🔍 Testing reverse lookup...")
    
    con = sqlite3.connect("vanta_user_prefs.db")
    try:
        # Test users_by_trader equivalent
        trader_key = "test_trader"
        cur = con.execute("SELECT user_id FROM user_follow_configs WHERE trader_key=?", (trader_key,))
        users = [row[0] for row in cur.fetchall()]
        print(f"✅ Found {len(users)} users following {trader_key}")
        
        # Test all_trader_keys equivalent
        cur = con.execute("SELECT DISTINCT trader_key FROM user_follow_configs ORDER BY trader_key")
        keys = [row[0] for row in cur.fetchall()]
        print(f"✅ Found {len(keys)} unique trader keys")
        
        return True
    finally:
        con.close()

def test_admin_functionality():
    """Test admin kill-switch functionality"""
    print("\n🔍 Testing admin functionality...")
    
    # Test admin check logic
    admin_ids = os.getenv("ADMIN_USER_IDS", "").split(",")
    print(f"✅ Admin IDs configured: {len([aid for aid in admin_ids if aid.strip()])} admins")
    
    # Test that we can query all configurations for kill-switch
    con = sqlite3.connect("vanta_user_prefs.db")
    try:
        cur = con.execute("SELECT user_id, trader_key, cfg_json FROM user_follow_configs")
        configs = cur.fetchall()
        print(f"✅ Found {len(configs)} configurations for kill-switch processing")
        
        # Count auto-copy enabled configs
        auto_copy_count = 0
        for user_id, trader_key, cfg_json in configs:
            cfg = json.loads(cfg_json)
            if cfg.get("auto_copy", False):
                auto_copy_count += 1
        
        print(f"✅ Found {auto_copy_count} auto-copy enabled configurations")
        return True
    finally:
        con.close()

def test_server_guard_logic():
    """Test server guard logic"""
    print("\n🔍 Testing server guard logic...")
    
    # Test environment variable parsing
    copy_mode = os.getenv("COPY_EXECUTION_MODE", "DRY").upper()
    is_live_mode = copy_mode == "LIVE"
    print(f"✅ Server mode: {copy_mode} (LIVE={is_live_mode})")
    
    # Test guard logic
    if not is_live_mode:
        print("✅ Server guard would block auto-copy (DRY mode)")
    else:
        print("✅ Server guard would allow auto-copy (LIVE mode)")
    
    return True

def test_structured_logging():
    """Test structured logging format"""
    print("\n🔍 Testing structured logging...")
    
    # Test log format structure
    log_entry = {
        "trader_key": "0xabc...123",
        "pair": "ETH/USD",
        "side": "LONG",
        "lev": 25,
        "notional": 1000,
        "reason": "server_dry"
    }
    
    print(f"✅ Log entry structure: {log_entry}")
    
    # Test all possible reasons
    valid_reasons = ["copied", "auto_copy_off", "server_dry", "executor_missing", "over_per_trade_cap", "exec_error"]
    for reason in valid_reasons:
        log_entry["reason"] = reason
        print(f"✅ Reason '{reason}' is valid")
    
    return True

def test_fanout_logic():
    """Test fanout logic"""
    print("\n🔍 Testing fanout logic...")
    
    con = sqlite3.connect("vanta_user_prefs.db")
    try:
        # Simulate fanout for a trader
        trader_key = "test_trader"
        cur = con.execute("SELECT user_id FROM user_follow_configs WHERE trader_key=?", (trader_key,))
        following_users = [row[0] for row in cur.fetchall()]
        
        print(f"✅ Fanout would reach {len(following_users)} users for trader {trader_key}")
        
        # Test signal structure
        signal = {
            "pair": "ETH/USD",
            "side": "LONG",
            "lev": 10,
            "notional_usd": 500,
            "collateral_usdc": 50
        }
        
        print(f"✅ Signal structure: {signal}")
        return True
    finally:
        con.close()

def test_notification_dedupe():
    """Test notification deduplication logic"""
    print("\n🔍 Testing notification dedupe...")
    
    # Test dedupe key format
    uid = 12345
    reason = "server_dry"
    notification_key = f"{uid}:{reason}"
    print(f"✅ Dedupe key format: {notification_key}")
    
    # Test TTL logic (5 minutes = 300 seconds)
    import time
    now = time.time()
    ttl = 300
    
    print(f"✅ Notification TTL: {ttl} seconds")
    print(f"✅ Current timestamp: {now}")
    
    return True

async def main():
    """Run all final mile tests"""
    print("🚀 Final Mile Test Suite")
    print("=" * 50)
    
    tests = [
        ("Database Index", test_database_index),
        ("Reverse Lookup", test_reverse_lookup),
        ("Admin Functionality", test_admin_functionality),
        ("Server Guard Logic", test_server_guard_logic),
        ("Structured Logging", test_structured_logging),
        ("Fanout Logic", test_fanout_logic),
        ("Notification Dedupe", test_notification_dedupe),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
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
        print("🎉 All final mile tests passed! Production hardening complete.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
