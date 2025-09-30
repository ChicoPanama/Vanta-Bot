"""
Avantis Indexer (Phase 4)

Backfills from last stored block to `tip - CONFIRMATIONS`, parses trade events into
IndexedFill rows, and updates UserPosition aggregates. Then follows head in a loop.

TODO: Replace EVENT topics/decoders with real Avantis ABI once confirmed.
"""

import logging
import time
from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from web3 import Web3

from src.config.settings import settings
from src.database.models import IndexedFill
from src.repositories.positions_repo import insert_fills, upsert_position
from src.repositories.sync_state_repo import get_block, set_block

logger = logging.getLogger(__name__)

# Configuration
CONFIRMATIONS = 2
SYNC_NAME = "avantis_indexer"
CHUNK = 2_000  # blocks per query (tune per provider limits)

# Placeholder topic signatures (TODO: update with real Avantis events)
# e.g., keccak("PositionIncreased(address indexed user, uint256 marketId, bool isLong, uint256 usd, uint256 collateral)")
TOPIC_OPEN = "0x" + "11" * 32
TOPIC_CLOSE = "0x" + "22" * 32


def _decode_event(w3: Web3, log: dict) -> Iterable[IndexedFill]:
    """Decode log event to IndexedFill records.

    TODO: Replace with real ABI decoding once Avantis event structure is confirmed.
    Use w3.codec or contract.events.YourEvent().processLog(log)

    Args:
        w3: Web3 instance
        log: Raw log dict from eth_getLogs

    Returns:
        Iterable of IndexedFill objects
    """
    # STUB: Return empty list until real decoder is implemented
    # In production, this would parse log topics/data and return IndexedFill objects
    return []


def _apply_fill(db, fill: IndexedFill) -> None:
    """Apply fill to user position aggregate.

    Args:
        db: Database session
        fill: IndexedFill record
    """
    # Positive usd_1e6 means increase; negative means reduction
    is_long = fill.is_long
    size_delta = fill.usd_1e6
    coll_delta = fill.collateral_usdc_1e6

    upsert_position(
        db,
        user_addr=fill.user_address,
        symbol=fill.symbol,
        is_long=is_long,
        size_delta_1e6=size_delta,
        collateral_delta_1e6=coll_delta,
    )


def run_once(w3: Web3, SessionLocal) -> int:
    """Run one indexing iteration.

    Args:
        w3: Web3 instance
        SessionLocal: SQLAlchemy session factory

    Returns:
        Number of blocks processed
    """
    with SessionLocal() as db:
        start = get_block(db, SYNC_NAME)
        tip = w3.eth.block_number
        target = max(0, tip - CONFIRMATIONS)

        if start == 0:
            # First run: start from recent history (adjust as needed)
            start = max(0, target - 1000)  # Last 1000 blocks
            logger.info(f"First run, starting from block {start}")

        if start >= target:
            return 0

        end = min(target, start + CHUNK)

        logger.info(
            f"Indexing blocks {start + 1} to {end} (tip={tip}, target={target})"
        )

        # Get logs (TODO: filter by Avantis contract addresses)
        logs = w3.eth.get_logs({"fromBlock": start + 1, "toBlock": end})

        fills: list[IndexedFill] = []
        for lg in logs:
            # TODO: Filter by Avantis contract addresses
            # if lg["address"].lower() not in allowed_contract_set:
            #     continue

            for fill in _decode_event(w3, lg):
                fills.append(fill)

        if fills:
            logger.info(f"Found {len(fills)} fills in blocks {start + 1}-{end}")
            insert_fills(db, fills)
            for fill in fills:
                _apply_fill(db, fill)

        set_block(db, SYNC_NAME, end)
        return end - start


def main():
    """Main indexer loop."""
    logger.info(
        f"Starting Avantis indexer (confirmations={CONFIRMATIONS}, chunk={CHUNK})"
    )

    w3 = Web3(Web3.HTTPProvider(settings.BASE_RPC_URL))
    if not w3.is_connected():
        logger.error("Web3 not connected, cannot start indexer")
        return

    eng = create_engine(
        settings.DATABASE_URL.replace("sqlite+aiosqlite:", "sqlite:"),
        pool_pre_ping=True,
    )
    SessionLocal = sessionmaker(bind=eng, expire_on_commit=False)

    while True:
        try:
            n = run_once(w3, SessionLocal)
            if n == 0:
                # Caught up, sleep before next poll
                time.sleep(2)
        except KeyboardInterrupt:
            logger.info("Indexer stopped by user")
            break
        except Exception as e:
            logger.error(f"Indexer error: {e}", exc_info=True)
            time.sleep(5)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
    )
    main()
