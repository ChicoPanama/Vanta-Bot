from __future__ import annotations

import asyncio
import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.services.indexers.avantis_indexer import AvantisIndexer

logger = logging.getLogger(__name__)


async def main():
    """Main indexer runner - backfill then tail follow"""
    logger.info("🚀 Starting Avantis Indexer...")

    # --- DB session factory ---
    database_url = os.getenv("DATABASE_URL", "sqlite:///vanta_bot.db")
    engine = create_engine(database_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    logger.info(f"📊 Connected to database: {database_url}")

    # Initialize indexer
    idx = AvantisIndexer()
    idx.set_db_session_factory(Session)

    # Get Web3 connection
    w3 = idx.w3_http
    latest = w3.eth.block_number
    logger.info(f"🔗 Connected to blockchain, latest block: {latest}")

    # Choose a safe backfill window (configurable via INDEXER_BACKFILL_RANGE)
    backfill_range = int(os.getenv("INDEXER_BACKFILL_RANGE", "50000"))
    from_block = max(0, latest - backfill_range)
    to_block = latest

    logger.info(f"📥 Backfilling from block {from_block} to {to_block}")

    try:
        # Backfill then tail
        await idx.backfill(from_block, to_block)
        logger.info("✅ Backfill completed, starting tail following...")

        await idx.tail_follow(start_block=to_block)

    except KeyboardInterrupt:
        logger.info("🛑 Indexer stopped by user")
    except Exception as e:
        logger.error(f"❌ Indexer error: {e}")
        raise


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Check required environment variables
    required_env = ["BASE_RPC_URL", "AVANTIS_TRADING_CONTRACT"]

    missing_env = [var for var in required_env if not os.getenv(var)]
    if missing_env:
        logger.error(f"❌ Missing required environment variables: {missing_env}")
        logger.error("Please set:")
        for var in missing_env:
            logger.error(f"  export {var}=...")
        exit(1)

    asyncio.run(main())
