"""
Avantis Indexer (Phase 4)

Backfills from last stored block to `tip - CONFIRMATIONS`, parses trade events into
IndexedFill rows, and updates UserPosition aggregates. Then follows head in a loop.

This indexer uses the Avantis Trading contract ABI from config/abis/Trading.json
to decode events. The contract address is loaded from config/addresses/base.mainnet.json.
"""

import json
import logging
import time
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

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

# Load contract address from config
_CONFIG_ROOT = Path(__file__).parent.parent.parent.parent / "config"
_ADDRESSES_PATH = _CONFIG_ROOT / "addresses" / "base.mainnet.json"

with open(_ADDRESSES_PATH) as f:
    _addresses_config = json.load(f)
    TRADING_CONTRACT = _addresses_config["contracts"]["trading"]["address"].lower()

logger.info(f"Avantis Trading Contract: {TRADING_CONTRACT}")


def _load_trading_contract(w3: Web3):
    """Load Avantis Trading contract with ABI.

    Args:
        w3: Web3 instance

    Returns:
        Contract instance
    """
    abi_path = _CONFIG_ROOT / "abis" / "Trading.json"
    with open(abi_path) as f:
        abi = json.load(f)

    return w3.eth.contract(address=Web3.to_checksum_address(TRADING_CONTRACT), abi=abi)


def _decode_event(w3: Web3, contract, log: dict) -> Iterable[IndexedFill]:
    """Decode log event to IndexedFill records.

    This function uses the Trading contract ABI to decode events like:
    - MarketExecuted
    - PositionModified
    - TradeClosed

    Args:
        w3: Web3 instance
        contract: Trading contract instance
        log: Raw log dict from eth_getLogs

    Returns:
        Iterable of IndexedFill objects
    """
    # NOTE: This is a stub implementation. To fully implement:
    # 1. Identify the exact event names from the Trading ABI
    # 2. Use contract.events.EventName().process_log(log) to decode
    # 3. Map decoded event data to IndexedFill fields
    #
    # Example:
    #   try:
    #       event = contract.events.MarketExecuted().process_log(log)
    #       return [IndexedFill(
    #           user_address=event.args.trader.lower(),
    #           symbol=_market_id_to_symbol(event.args.marketId),
    #           is_long=event.args.long,
    #           usd_1e6=event.args.notional,
    #           collateral_usdc_1e6=event.args.collateral,
    #           tx_hash=log["transactionHash"].hex(),
    #           block_number=log["blockNumber"],
    #           ...
    #       )]
    #   except Exception:
    #       return []

    # For now, return empty to avoid errors until events are mapped
    return []


def _apply_fill(db, fill: IndexedFill) -> None:
    """Apply fill to user position aggregate and invalidate cache.

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

    # Invalidate cache immediately so users see fresh positions
    try:
        from src.services.cache.positions_cache import PositionsCache

        PositionsCache().invalidate(fill.user_address)
    except Exception as e:
        logger.warning(f"Failed to invalidate cache for {fill.user_address}: {e}")


def run_once(w3: Web3, contract, SessionLocal) -> int:
    """Run one indexing iteration.

    Args:
        w3: Web3 instance
        contract: Trading contract instance
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

        # Get logs filtered by Avantis Trading contract address
        logs = w3.eth.get_logs(
            {
                "fromBlock": start + 1,
                "toBlock": end,
                "address": Web3.to_checksum_address(TRADING_CONTRACT),
            }
        )

        fills: list[IndexedFill] = []
        for lg in logs:
            # Only process logs from the Trading contract
            if lg["address"].lower() != TRADING_CONTRACT:
                continue

            for fill in _decode_event(w3, contract, lg):
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

    # Load Trading contract with ABI
    contract = _load_trading_contract(w3)
    logger.info(f"Loaded Trading contract at {TRADING_CONTRACT}")

    eng = create_engine(
        settings.DATABASE_URL.replace("sqlite+aiosqlite:", "sqlite:"),
        pool_pre_ping=True,
    )
    SessionLocal = sessionmaker(bind=eng, expire_on_commit=False)

    while True:
        try:
            n = run_once(w3, contract, SessionLocal)
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
