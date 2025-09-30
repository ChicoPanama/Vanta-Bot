#!/usr/bin/env python3
"""
Close Position - Return Funds to Wallet

This script closes the position we just opened and returns the funds to the wallet.
"""

import json
import logging

from eth_account import Account
from web3 import Web3

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def close_position():
    """Close the position and return funds to wallet."""

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

    logger.info("🔒 CLOSING POSITION")
    logger.info(f"Proxy: {PROXY}")
    logger.info(f"Wallet: {WALLET}")

    # Check contract status
    paused = contract.functions.paused().call()
    logger.info(f"Contract paused: {paused}")

    if paused:
        logger.error("❌ Contract is paused")
        return

    # Position details from our trade
    pair_index = 0
    position_index = 0  # This should be 0 for the first position
    close_amount = 10_000_000  # Close full position (10 USDC in 6dp)

    logger.info("Position Details:")
    logger.info(f"  Pair Index: {pair_index}")
    logger.info(f"  Position Index: {position_index}")
    logger.info(f"  Close Amount: {close_amount:,} (10 USDC)")

    # Execute close transaction
    try:
        # Get nonce
        nonce = w3.eth.get_transaction_count(WALLET)

        logger.info("Building close transaction...")

        # Build close transaction
        transaction = contract.functions.closeTradeMarket(
            pair_index, position_index, close_amount
        ).build_transaction(
            {
                "from": WALLET,
                "nonce": nonce,
                "gas": 500000,
                "gasPrice": w3.eth.gas_price,
                "value": 0,  # No ETH value needed
            }
        )

        # Sign transaction
        signed_txn = account.sign_transaction(transaction)

        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        logger.info("✅ CLOSE TRANSACTION SUBMITTED")
        logger.info(f"Transaction Hash: {tx_hash.hex()}")
        logger.info(f"BaseScan URL: https://basescan.org/tx/{tx_hash.hex()}")

        # Wait for confirmation
        logger.info("⏳ Waiting for confirmation...")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt.status == 1:
            logger.info("🎉 POSITION CLOSED SUCCESSFULLY!")
            logger.info(f"Block Number: {receipt.blockNumber}")
            logger.info(f"Gas Used: {receipt.gasUsed:,}")
            logger.info(f"BaseScan: https://basescan.org/tx/{tx_hash.hex()}")

            # Save results
            results = {
                "success": True,
                "action": "close_position",
                "transaction_hash": tx_hash.hex(),
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "basescan_url": f"https://basescan.org/tx/{tx_hash.hex()}",
                "position_details": {
                    "pair_index": pair_index,
                    "position_index": position_index,
                    "close_amount": close_amount,
                },
            }

            with open("close_position_success.json", "w") as f:
                json.dump(results, f, indent=2)

            logger.info("Results saved to: close_position_success.json")
            logger.info("💰 Funds should now be returned to your wallet!")

        else:
            logger.error("❌ Close transaction failed")

    except Exception as e:
        logger.error(f"❌ Close position failed: {e}")

        # Try to get more info about the error
        if "BELOW_MIN_POS" in str(e):
            logger.error("Position might be too small to close")
        elif "INVALID_POS" in str(e):
            logger.error("Position might not exist or already closed")
        elif "execution reverted" in str(e):
            logger.error("Transaction reverted - check position details")

        # Save error details
        error_results = {
            "success": False,
            "action": "close_position",
            "error": str(e),
            "proxy": PROXY,
            "wallet": WALLET,
            "position_details": {
                "pair_index": pair_index,
                "position_index": position_index,
                "close_amount": close_amount,
            },
        }

        with open("close_position_error.json", "w") as f:
            json.dump(error_results, f, indent=2)

        logger.info("Error details saved to: close_position_error.json")


if __name__ == "__main__":
    close_position()
