"""Production startup checks (Phase 9)."""

import logging

from web3 import Web3

logger = logging.getLogger(__name__)


def check_rpc(w3: Web3) -> None:
    """Verify RPC connectivity."""
    try:
        block = w3.eth.block_number
        logger.info(f"✅ RPC check passed (block: {block})")
    except Exception as e:
        raise RuntimeError(f"RPC check failed: {e}")


def check_redis(redis_client) -> None:
    """Verify Redis connectivity."""
    try:
        redis_client.ping()
        logger.info("✅ Redis check passed")
    except Exception as e:
        raise RuntimeError(f"Redis check failed: {e}")
