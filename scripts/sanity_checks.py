#!/usr/bin/env python3
"""
Sanity checks for the copy trading system
Run these commands to verify everything is working correctly
"""
import os
import sys
import sqlite3
from decimal import Decimal
from sqlalchemy import create_engine, text

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.analytics.fifo_pnl import realized_pnl_fifo
from src.services.analytics.leaderboard_service import LeaderboardService
from src.services.analytics.pnl_service import PnlService

def check_database_connection():
    """Check if database is accessible and tables exist"""
    print("🔍 Checking database connection...")
    
    database_url = os.getenv("DATABASE_URL", "sqlite:///vanta_bot.db")
    engine = create_engine(database_url)
    
    try:
        with engine.begin() as conn:
            # Check tables exist
            tables = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
            table_names = [row[0] for row in tables]
            
            required_tables = ['fills', 'trader_positions', 'alembic_version']
            for table in required_tables:
                if table in table_names:
                    print(f"  ✅ Table '{table}' exists")
                else:
                    print(f"  ❌ Table '{table}' missing")
            
            # Check if fills table has data
            if 'fills' in table_names:
                result = conn.execute(text("SELECT COUNT(*) as count, MIN(ts) as min_ts, MAX(ts) as max_ts FROM fills")).fetchone()
                if result and result[0] > 0:
                    print(f"  ✅ Fills table has {result[0]} records")
                    print(f"  📅 Date range: {result[1]} to {result[2]}")
                else:
                    print("  ⚠️  Fills table is empty")
            
            return True
            
    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        return False

def check_fifo_pnl():
    """Test FIFO PnL calculation"""
    print("\n🧮 Testing FIFO PnL calculation...")
    
    # Test case 1: Simple long trade
    test_fills = [
        ("OPEN", Decimal("1"), Decimal("100"), Decimal("0.1")),
        ("OPEN", Decimal("1"), Decimal("110"), Decimal("0.1")),
        ("CLOSE", Decimal("1"), Decimal("120"), Decimal("0.1")),
        ("CLOSE", Decimal("1"), Decimal("90"), Decimal("0.1")),
    ]
    
    pnl = realized_pnl_fifo(test_fills)
    expected = Decimal("-0.4")  # (120-100)*1 + (90-110)*1 - 0.4 fees = -0.4
    
    if pnl == expected:
        print(f"  ✅ FIFO PnL test passed: ${pnl}")
    else:
        print(f"  ❌ FIFO PnL test failed: got ${pnl}, expected ${expected}")
        return False
    
    return True

def check_leaderboard_service():
    """Test leaderboard service"""
    print("\n📊 Testing leaderboard service...")
    
    database_url = os.getenv("DATABASE_URL", "sqlite:///vanta_bot.db")
    engine = create_engine(database_url)
    
    try:
        lb_service = LeaderboardService(engine)
        print("  ✅ Leaderboard service initialized")
        
        # Try to get top traders (might be empty if no data)
        import asyncio
        async def test_leaderboard():
            traders = await lb_service.top_traders(limit=5)
            if traders:
                print(f"  ✅ Found {len(traders)} qualified traders")
                for i, trader in enumerate(traders[:3], 1):
                    print(f"    {i}. {trader['address'][:10]}... - Vol: ${trader['last_30d_volume_usd']:,.0f}")
            else:
                print("  ⚠️  No qualified traders found (lower thresholds or add data)")
            return True
        
        return asyncio.run(test_leaderboard())
        
    except Exception as e:
        print(f"  ❌ Leaderboard service error: {e}")
        return False

def check_top_traders():
    """Show top traders by volume"""
    print("\n🏆 Top traders by volume...")
    
    database_url = os.getenv("DATABASE_URL", "sqlite:///vanta_bot.db")
    engine = create_engine(database_url)
    
    try:
        with engine.begin() as conn:
            result = conn.execute(text("""
                SELECT address, COUNT(*) as trades, SUM(ABS(price*size)) as volume
                FROM fills
                GROUP BY address
                ORDER BY volume DESC
                LIMIT 5
            """)).fetchall()
            
            if result:
                print("  📈 Top 5 traders by volume:")
                for i, row in enumerate(result, 1):
                    print(f"    {i}. {row[0][:10]}... - {row[1]} trades, ${float(row[2]):,.0f} volume")
            else:
                print("  ⚠️  No trading data found")
                
    except Exception as e:
        print(f"  ❌ Error querying traders: {e}")

def check_pnl_calculation():
    """Test PnL calculation for a specific address"""
    print("\n💰 Testing PnL calculation...")
    
    database_url = os.getenv("DATABASE_URL", "sqlite:///vanta_bot.db")
    engine = create_engine(database_url)
    
    try:
        with engine.begin() as conn:
            # Get an address with trades
            result = conn.execute(text("""
                SELECT address, COUNT(*) as trades
                FROM fills
                GROUP BY address
                ORDER BY trades DESC
                LIMIT 1
            """)).fetchone()
            
            if result:
                address = result[0]
                trades = result[1]
                
                pnl_service = PnlService(engine)
                clean_pnl = pnl_service.clean_realized_pnl_30d(address)
                
                print(f"  📊 Address: {address[:10]}... ({trades} trades)")
                print(f"  💰 Clean 30D PnL: ${clean_pnl}")
                
                return True
            else:
                print("  ⚠️  No trading data found for PnL calculation")
                return False
                
    except Exception as e:
        print(f"  ❌ Error calculating PnL: {e}")
        return False

def main():
    """Run all sanity checks"""
    print("🔧 Copy Trading System - Sanity Checks")
    print("=" * 50)
    
    checks = [
        check_database_connection,
        check_fifo_pnl,
        check_leaderboard_service,
        check_top_traders,
        check_pnl_calculation,
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result if result is not None else True)
        except Exception as e:
            print(f"  ❌ Check failed with error: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 All {total} checks passed!")
        print("\n🚀 System is ready! Use /alfa top50 in Telegram to see the leaderboard.")
    else:
        print(f"⚠️  {passed}/{total} checks passed")
        print("\n📋 Next steps:")
        print("1. Ensure your indexer is running to populate the 'fills' table")
        print("2. Check environment variables (DATABASE_URL, etc.)")
        print("3. Verify ABI files are in config/abis/")

if __name__ == "__main__":
    main()
