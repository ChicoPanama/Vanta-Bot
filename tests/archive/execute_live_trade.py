#!/usr/bin/env python3
"""
Execute Live Trade - Final Test

This script executes a live trade using the correct active proxy and proper parameter formatting.
"""

import json
import logging
from decimal import Decimal

from eth_account import Account
from web3 import Web3

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def execute_live_trade():
    """Execute a live trade with the active proxy."""

    # Configuration
    RPC = "https://mainnet.base.org"
    PROXY = "0x44914408af82bC9983bbb330e3578E1105e11d4e"  # Active proxy
    WALLET = "0xdCDca231d02F1a8B85B701Ce90fc32c48a673982"
    PRIVATE_KEY = "aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87"

    # Initialize
    w3 = Web3(Web3.HTTPProvider(RPC))
    account = Account.from_key(PRIVATE_KEY)

    # Load ABI
    with open("config/abis/Trading.json") as f:
        data = json.load(f)
    abi = data["abi"]

    contract = w3.eth.contract(address=PROXY, abi=abi)

    logger.info("🚀 EXECUTING LIVE TRADE")
    logger.info(f"Proxy: {PROXY}")
    logger.info(f"Wallet: {WALLET}")

    # Check contract status
    paused = contract.functions.paused().call()
    logger.info(f"Contract paused: {paused}")

    if paused:
        logger.error("❌ Contract is paused")
        return

    # Trade parameters
    collateral_usdc = Decimal("10")  # $10 USDC
    leverage = Decimal("2")  # 2x leverage
    slippage_pct = Decimal("1.0")  # 1% slippage
    pair_index = 0
    is_long = True

    logger.info("Trade Parameters:")
    logger.info(f"  Collateral: {collateral_usdc} USDC")
    logger.info(f"  Leverage: {leverage}x")
    logger.info(f"  Slippage: {slippage_pct}%")
    logger.info(f"  Pair: {pair_index}")
    logger.info(f"  Direction: {'LONG' if is_long else 'SHORT'}")

    # Scale parameters
    USDC_6 = Decimal(10) ** 6
    SCALE_1E10 = Decimal(10) ** 10

    initial_pos_token = int(collateral_usdc * USDC_6)
    leverage_scaled = int(leverage * SCALE_1E10)
    position_size_usdc = (initial_pos_token * leverage_scaled) // int(SCALE_1E10)
    slippage_scaled = int((slippage_pct / Decimal("100")) * SCALE_1E10)

    logger.info("Scaled Parameters:")
    logger.info(f"  initialPosToken: {initial_pos_token:,}")
    logger.info(f"  leverage: {leverage_scaled:,}")
    logger.info(f"  positionSizeUSDC: {position_size_usdc:,}")
    logger.info(f"  slippage: {slippage_scaled:,}")

    # Build trade struct as tuple (not dict)
    trade_struct = (
        WALLET,  # trader
        pair_index,  # pairIndex
        0,  # index
        initial_pos_token,  # initialPosToken
        position_size_usdc,  # positionSizeUSDC
        0,  # openPrice (market order)
        is_long,  # buy
        leverage_scaled,  # leverage
        0,  # tp (no take profit)
        0,  # sl (no stop loss)
        0,  # timestamp
    )

    logger.info("Trade struct built as tuple")

    # Execute transaction
    try:
        # Get nonce
        nonce = w3.eth.get_transaction_count(WALLET)

        # Build transaction
        transaction = contract.functions.openTrade(
            trade_struct,
            0,  # MARKET order
            slippage_scaled,
        ).build_transaction(
            {
                "from": WALLET,
                "nonce": nonce,
                "gas": 500000,
                "gasPrice": w3.eth.gas_price,
            }
        )

        # Sign transaction
        signed_txn = account.sign_transaction(transaction)

        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        logger.info("✅ TRANSACTION SUBMITTED")
        logger.info(f"Transaction Hash: {tx_hash.hex()}")
        logger.info(f"BaseScan URL: https://basescan.org/tx/{tx_hash.hex()}")

        # Wait for confirmation
        logger.info("⏳ Waiting for confirmation...")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt.status == 1:
            logger.info("🎉 TRADE EXECUTED SUCCESSFULLY!")
            logger.info(f"Block Number: {receipt.blockNumber}")
            logger.info(f"Gas Used: {receipt.gasUsed:,}")
            logger.info(f"BaseScan: https://basescan.org/tx/{tx_hash.hex()}")

            # Save results
            results = {
                "success": True,
                "transaction_hash": tx_hash.hex(),
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "basescan_url": f"https://basescan.org/tx/{tx_hash.hex()}",
                "trade_parameters": {
                    "collateral_usdc": str(collateral_usdc),
                    "leverage": str(leverage),
                    "slippage_pct": str(slippage_pct),
                    "pair_index": pair_index,
                    "is_long": is_long,
                },
            }

            with open("live_trade_success.json", "w") as f:
                json.dump(results, f, indent=2)

            logger.info("Results saved to: live_trade_success.json")

        else:
            logger.error("❌ Transaction failed")

    except Exception as e:
        logger.error(f"❌ Trade execution failed: {e}")

        # Save error details
        error_results = {
            "success": False,
            "error": str(e),
            "proxy": PROXY,
            "wallet": WALLET,
            "trade_parameters": {
                "collateral_usdc": str(collateral_usdc),
                "leverage": str(leverage),
                "slippage_pct": str(slippage_pct),
                "pair_index": pair_index,
                "is_long": is_long,
            },
        }

        with open("live_trade_error.json", "w") as f:
            json.dump(error_results, f, indent=2)

        logger.info("Error details saved to: live_trade_error.json")


if __name__ == "__main__":
    execute_live_trade()
