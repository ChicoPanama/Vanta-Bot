"""Bot application bootstrap (Phase 5)."""

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram.ext import ApplicationBuilder
from web3 import Web3

from src.adapters.price.aggregator import PriceAggregator
from src.adapters.price.chainlink_adapter import ChainlinkAdapter
from src.blockchain.avantis.service import AvantisService
from src.bot.handlers.base import register_base
from src.bot.handlers.market_handlers import register_markets
from src.bot.handlers.ops_handlers import register_ops
from src.bot.handlers.positions_handlers import register_positions
from src.bot.handlers.risk_handlers import register_risk
from src.bot.handlers.trade_handlers import register_trades
from src.bot.handlers.wallet_handlers import register_wallet
from src.bot.middlewares.auth import user_context_middleware
from src.bot.middlewares.errors import error_handler
from src.config.settings import settings

logger = logging.getLogger(__name__)


def build_services():
    """Build service factory for dependency injection."""

    def svc_factory():
        """Create Web3, DB session, and AvantisService."""
        w3 = Web3(Web3.HTTPProvider(settings.BASE_RPC_URL))

        # Convert async URL to sync for repositories
        db_url = settings.DATABASE_URL.replace("sqlite+aiosqlite:", "sqlite:")
        eng = create_engine(db_url, pool_pre_ping=True)
        Session = sessionmaker(bind=eng, expire_on_commit=False)
        db = Session()

        # TODO: Add real Chainlink feed addresses when ready
        cl_map = {}  # e.g., {"BTC-USD": "0x64c9119..."}
        price_agg = PriceAggregator([ChainlinkAdapter(w3, cl_map)])

        svc = AvantisService(w3, db, price_agg)
        return w3, db, svc

    return svc_factory


def build_app():
    """Build Telegram application with all handlers."""
    logger.info("Building Telegram application...")

    app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Add error handler
    app.add_error_handler(error_handler)

    # Build services
    svc = build_services()

    # Register all handlers
    register_base(app, svc)
    register_wallet(app, svc)
    register_markets(app, svc)
    register_positions(app, svc)
    register_trades(app, svc)
    register_ops(app, svc)
    register_risk(app, svc)

    logger.info("✅ Telegram application built successfully")
    return app


def main():
    """Main entry point for bot."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    app = build_app()
    logger.info("🤖 Starting Vanta-Bot...")
    app.run_polling()


if __name__ == "__main__":
    main()
