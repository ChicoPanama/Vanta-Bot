#!/usr/bin/env python3
"""
Database optimization scripts for production performance
"""

import os
import sys

from sqlalchemy import create_engine, text

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config.settings import settings


def create_performance_indexes():
    """Create additional indexes for better query performance"""
    print("🔧 Creating performance indexes...")

    database_url = settings.DATABASE_URL
    engine = create_engine(database_url)

    indexes = [
        # Composite index for address + timestamp (leaderboard queries)
        "CREATE INDEX IF NOT EXISTS idx_fills_address_ts ON fills (address, ts)",
        # Index for 30-day window queries
        "CREATE INDEX IF NOT EXISTS idx_fills_ts_address ON fills (ts, address)",
        # Index for pair-based queries
        "CREATE INDEX IF NOT EXISTS idx_fills_pair_ts ON fills (pair, ts)",
        # Index for side-based filtering
        "CREATE INDEX IF NOT EXISTS idx_fills_side_ts ON fills (side, ts)",
        # Index for trader positions
        "CREATE INDEX IF NOT EXISTS idx_trader_positions_address_opened ON trader_positions (address, opened_at)",
        # Index for closed positions
        "CREATE INDEX IF NOT EXISTS idx_trader_positions_closed ON trader_positions (closed_at) WHERE closed_at IS NOT NULL",
    ]

    try:
        with engine.begin() as conn:
            for idx_sql in indexes:
                try:
                    conn.execute(text(idx_sql))
                    print(
                        f"  ✅ Created index: {idx_sql.split('idx_')[1].split(' ')[0]}"
                    )
                except Exception as e:
                    print(f"  ⚠️  Index may already exist: {e}")

        print("✅ Performance indexes created successfully")
        return True

    except Exception as e:
        print(f"❌ Error creating indexes: {e}")
        return False


def analyze_query_performance():
    """Analyze query performance and suggest optimizations"""
    print("\n📊 Analyzing query performance...")

    database_url = settings.DATABASE_URL

    if "postgresql" in database_url:
        print("  🐘 PostgreSQL detected - using EXPLAIN ANALYZE")
        analyze_postgresql_performance(database_url)
    else:
        print("  🗄️  SQLite detected - using EXPLAIN QUERY PLAN")
        analyze_sqlite_performance(database_url)


def analyze_sqlite_performance(database_url):
    """Analyze SQLite query performance"""
    engine = create_engine(database_url)

    # Key queries to analyze
    queries = [
        {
            "name": "Leaderboard query",
            "sql": """
                SELECT address, COUNT(*) as trades, SUM(ABS(price*size)) as volume
                FROM fills
                WHERE ts >= (strftime('%s', 'now') - 30 * 24 * 60 * 60)
                GROUP BY address
                ORDER BY volume DESC
                LIMIT 10
            """,
        },
        {
            "name": "PnL calculation query",
            "sql": """
                SELECT side, is_long, size, price, fee
                FROM fills
                WHERE address = '0x1234567890123456789012345678901234567890'
                  AND ts >= (strftime('%s', 'now') - 30 * 24 * 60 * 60)
                ORDER BY ts ASC
            """,
        },
    ]

    try:
        with engine.begin() as conn:
            for query in queries:
                print(f"\n  📋 {query['name']}:")
                result = conn.execute(text(f"EXPLAIN QUERY PLAN {query['sql']}"))
                for row in result:
                    print(f"    {row[3]}")  # SQLite EXPLAIN QUERY PLAN format

    except Exception as e:
        print(f"  ❌ Error analyzing queries: {e}")


def analyze_postgresql_performance(database_url):
    """Analyze PostgreSQL query performance"""
    engine = create_engine(database_url)

    queries = [
        {
            "name": "Leaderboard query",
            "sql": """
                SELECT address, COUNT(*) as trades, SUM(ABS(price*size)) as volume
                FROM fills
                WHERE ts >= extract(epoch from now() - interval '30 days')
                GROUP BY address
                ORDER BY volume DESC
                LIMIT 10
            """,
        }
    ]

    try:
        with engine.begin() as conn:
            for query in queries:
                print(f"\n  📋 {query['name']}:")
                result = conn.execute(text(f"EXPLAIN ANALYZE {query['sql']}"))
                for row in result:
                    print(f"    {row[0]}")

    except Exception as e:
        print(f"  ❌ Error analyzing queries: {e}")


def vacuum_and_analyze():
    """Run VACUUM and ANALYZE for PostgreSQL optimization"""
    database_url = settings.DATABASE_URL

    if "postgresql" not in database_url:
        print("  ℹ️  VACUUM/ANALYZE only applies to PostgreSQL")
        return

    print("\n🧹 Running PostgreSQL maintenance...")

    engine = create_engine(database_url)

    try:
        with engine.begin() as conn:
            # ANALYZE to update statistics
            conn.execute(text("ANALYZE fills"))
            conn.execute(text("ANALYZE trader_positions"))
            print("  ✅ ANALYZE completed")

            # VACUUM to reclaim space (requires exclusive lock)
            print(
                "  ⚠️  VACUUM requires exclusive lock - run manually during maintenance window:"
            )
            print("  VACUUM ANALYZE fills;")
            print("  VACUUM ANALYZE trader_positions;")

    except Exception as e:
        print(f"  ❌ Error running maintenance: {e}")


def get_table_stats():
    """Get table statistics for monitoring"""
    print("\n📈 Table Statistics:")

    database_url = settings.DATABASE_URL
    engine = create_engine(database_url)

    try:
        with engine.begin() as conn:
            # Get row counts
            tables = ["fills", "trader_positions", "users"]
            for table in tables:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"  📊 {table}: {count:,} rows")

            # Get table sizes (PostgreSQL only)
            if "postgresql" in database_url:
                size_query = """
                    SELECT
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                    FROM pg_tables
                    WHERE tablename IN ('fills', 'trader_positions', 'users')
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                """
                result = conn.execute(text(size_query))
                print("\n  💾 Table Sizes:")
                for row in result:
                    print(f"    {row[1]}: {row[2]}")

    except Exception as e:
        print(f"  ❌ Error getting stats: {e}")


def main():
    """Run all optimization tasks"""
    print("🚀 Database Optimization Script")
    print("=" * 50)

    # Create indexes
    if not create_performance_indexes():
        print("❌ Failed to create indexes")
        return

    # Get statistics
    get_table_stats()

    # Analyze performance
    analyze_query_performance()

    # PostgreSQL maintenance
    vacuum_and_analyze()

    print("\n✅ Database optimization complete!")
    print("\n📋 Performance Tips:")
    print("1. Monitor query performance with EXPLAIN ANALYZE")
    print("2. Run VACUUM ANALYZE weekly during maintenance windows")
    print("3. Consider partitioning fills table by date for large datasets")
    print("4. Use connection pooling in production")
    print("5. Monitor index usage and remove unused indexes")


if __name__ == "__main__":
    main()
