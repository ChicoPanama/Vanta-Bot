"""TP/SL executor daemon (Phase 7)."""

import logging
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from web3 import Web3

from src.adapters.price.aggregator import PriceAggregator
from src.adapters.price.chainlink_adapter import ChainlinkAdapter
from src.blockchain.avantis.service import AvantisService
from src.config.settings import settings
from src.repositories.tpsl_repo import deactivate_tpsl, list_tpsl

logger = logging.getLogger(__name__)


def run_loop():
    """Main TP/SL executor loop."""
    logger.info("Starting TP/SL executor...")

    w3 = Web3(Web3.HTTPProvider(settings.BASE_RPC_URL))
    db_url = settings.DATABASE_URL.replace("sqlite+aiosqlite:", "sqlite:")
    eng = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=eng, expire_on_commit=False)

    # TODO: Add real Chainlink feeds
    cl_map = {}
    price_agg = PriceAggregator([ChainlinkAdapter(w3, cl_map)])

    while True:
        db = Session()
        try:
            for rec in list_tpsl(db, tg_user_id=None):  # Check all active orders
                try:
                    quote = price_agg.get_price(rec.symbol)
                    if not quote:
                        continue

                    current_price = quote.price / (10**quote.decimals)

                    # Check take-profit trigger
                    if rec.take_profit_price and current_price >= rec.take_profit_price:
                        logger.info(
                            f"TP triggered: {rec.symbol} @ {current_price} >= {rec.take_profit_price}"
                        )
                        svc = AvantisService(w3, db, price_agg)
                        # Close 100% of position
                        svc.close_market(
                            rec.tg_user_id,
                            rec.symbol,
                            reduce_usdc=999999,
                            slippage_pct=0.5,
                        )
                        deactivate_tpsl(db, rec.id)
                        continue

                    # Check stop-loss trigger
                    if rec.stop_loss_price and current_price <= rec.stop_loss_price:
                        logger.info(
                            f"SL triggered: {rec.symbol} @ {current_price} <= {rec.stop_loss_price}"
                        )
                        svc = AvantisService(w3, db, price_agg)
                        # Close 100% of position
                        svc.close_market(
                            rec.tg_user_id,
                            rec.symbol,
                            reduce_usdc=999999,
                            slippage_pct=0.5,
                        )
                        deactivate_tpsl(db, rec.id)

                except Exception as e:
                    logger.error(f"Failed to process TP/SL {rec.id}: {e}")

        except KeyboardInterrupt:
            logger.info("TP/SL executor stopped by user")
            break
        except Exception as e:
            logger.error(f"TP/SL executor error: {e}", exc_info=True)
        finally:
            db.close()

        time.sleep(10)  # Check every 10 seconds


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    run_loop()
