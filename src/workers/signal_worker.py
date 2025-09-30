"""Signal worker - processes queued signals (Phase 6)."""

import json
import logging
import time

import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from web3 import Web3

from src.adapters.price.aggregator import PriceAggregator
from src.adapters.price.chainlink_adapter import ChainlinkAdapter
from src.blockchain.avantis.service import AvantisService
from src.config.settings import settings
from src.database.models import Signal
from src.repositories.signals_repo import update_execution
from src.signals.rules import evaluate_close, evaluate_open

logger = logging.getLogger(__name__)


def _get_queue():
    """Get Redis queue client."""
    return redis.from_url(settings.REDIS_URL)


def build_services():
    """Build Web3, DB, and service layer."""
    w3 = Web3(Web3.HTTPProvider(settings.BASE_RPC_URL))
    db_url = settings.DATABASE_URL.replace("sqlite+aiosqlite:", "sqlite:")
    eng = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=eng, expire_on_commit=False)

    # TODO: Add real Chainlink feed addresses
    cl_map = {}
    price_agg = PriceAggregator([ChainlinkAdapter(w3, cl_map)])

    return w3, Session, price_agg


def process_one(w3, Session, price_agg) -> bool:
    """Process one signal from queue.

    Returns:
        True if processed something, False if queue empty
    """
    q = _get_queue()
    item = q.lpop(settings.SIGNALS_QUEUE)

    if not item:
        return False

    payload = json.loads(item.decode())
    intent_key = payload["intent_key"]

    db = Session()
    try:
        sig = db.query(Signal).filter_by(intent_key=intent_key).one_or_none()
        if not sig:
            update_execution(
                db, intent_key, status="REJECTED", reason="missing signal row"
            )
            logger.warning(f"Signal not found: {intent_key}")
            return True

        # Gate on master switches
        if not settings.SIGNALS_ENABLED or settings.AUTOMATION_PAUSED:
            update_execution(
                db, intent_key, status="REJECTED", reason="automation paused"
            )
            logger.info(f"Signal rejected (paused): {intent_key}")
            return True

        # Evaluate rules
        if sig.side == "CLOSE":
            decision = evaluate_close(db, sig.tg_user_id, sig.symbol, sig.reduce_usdc)
        else:
            decision = evaluate_open(
                db,
                sig.tg_user_id,
                sig.symbol,
                sig.side,
                sig.collateral_usdc,
                sig.leverage_x,
            )

        if not decision.allow:
            update_execution(db, intent_key, status="REJECTED", reason=decision.reason)
            logger.info(f"Signal rejected: {intent_key} | {decision.reason}")
            return True

        update_execution(db, intent_key, status="APPROVED")

        # Execute via service
        svc = AvantisService(w3, db, price_agg)

        if sig.side == "CLOSE":
            txh = svc.close_market(
                sig.tg_user_id, sig.symbol, sig.reduce_usdc, sig.slippage_pct
            )
        else:
            txh = svc.open_market(
                sig.tg_user_id,
                sig.symbol,
                sig.side,
                sig.collateral_usdc,
                sig.leverage_x,
                sig.slippage_pct,
            )

        update_execution(db, intent_key, status="SENT", tx_hash=txh)
        logger.info(f"Signal executed: {intent_key} | tx={txh}")
        return True

    except Exception as e:
        update_execution(db, intent_key, status="FAILED", reason=str(e))
        logger.error(f"Signal failed: {intent_key} | {e}", exc_info=True)
        return True
    finally:
        db.close()


def main():
    """Main worker loop."""
    logger.info("Starting signal worker...")

    w3, Session, price_agg = build_services()

    while True:
        try:
            processed = process_one(w3, Session, price_agg)
            if not processed:
                time.sleep(0.5)  # Idle sleep
        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
            break
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            time.sleep(5)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    main()
