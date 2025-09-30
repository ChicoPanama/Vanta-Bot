"""Calldata builders for Avantis actions (Phase 3)."""

import logging

from eth_abi import encode
from web3 import Web3

from .abi import CLOSE_POSITION_ABI, OPEN_POSITION_ABI
from .units import NormalizedOrder

logger = logging.getLogger(__name__)


def _get_function_selector(abi: dict) -> bytes:
    """Get 4-byte function selector from ABI."""
    from eth_utils import keccak

    # Build function signature
    inputs = ",".join([inp["type"] for inp in abi["inputs"]])
    signature = f"{abi['name']}({inputs})"

    # Hash and take first 4 bytes
    return keccak(text=signature)[:4]


def encode_open(
    w3: Web3, contract_addr: str, order: NormalizedOrder, market_id: int
) -> tuple[str, bytes]:
    """Encode openPosition calldata.

    Args:
        w3: Web3 instance
        contract_addr: Perpetual contract address
        order: Normalized order
        market_id: Avantis market ID

    Returns:
        Tuple of (to_address, calldata_bytes)
    """
    try:
        # Get function selector
        selector = _get_function_selector(OPEN_POSITION_ABI)

        # Encode arguments
        encoded_args = encode(
            ["uint256", "bool", "uint256", "uint256"],
            [
                market_id,
                order.side == "LONG",
                int(order.size_usd),
                int(order.slippage_bps),
            ],
        )

        # Combine selector + args
        data = selector + encoded_args

        logger.debug(
            f"Encoded openPosition: market={market_id}, side={order.side}, "
            f"size={order.size_usd}, slippage={order.slippage_bps}bps"
        )

        return contract_addr, data

    except Exception as e:
        logger.error(f"Failed to encode openPosition: {e}")
        raise


def encode_close(
    w3: Web3,
    contract_addr: str,
    market_id: int,
    reduce_usd_1e6: int,
    slippage_bps: int,
) -> tuple[str, bytes]:
    """Encode closePosition calldata.

    Args:
        w3: Web3 instance
        contract_addr: Perpetual contract address
        market_id: Avantis market ID
        reduce_usd_1e6: Amount to reduce in 1e6 USD
        slippage_bps: Slippage in basis points

    Returns:
        Tuple of (to_address, calldata_bytes)
    """
    try:
        # Get function selector
        selector = _get_function_selector(CLOSE_POSITION_ABI)

        # Encode arguments
        encoded_args = encode(
            ["uint256", "uint256", "uint256"],
            [market_id, int(reduce_usd_1e6), int(slippage_bps)],
        )

        # Combine selector + args
        data = selector + encoded_args

        logger.debug(
            f"Encoded closePosition: market={market_id}, reduce={reduce_usd_1e6}, slippage={slippage_bps}bps"
        )

        return contract_addr, data

    except Exception as e:
        logger.error(f"Failed to encode closePosition: {e}")
        raise
