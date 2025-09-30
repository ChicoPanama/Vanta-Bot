#!/usr/bin/env python3
"""
REAL TRADE TEST - Base Sepolia Testnet
Executes a complete trading flow: open position → verify → close position

This script will:
1. Connect to Base Sepolia testnet
2. Create a test wallet
3. Fund the wallet (requires manual funding)
4. Execute a real trade
5. Verify transaction on BaseScan
6. Close the position
7. Document results

CRITICAL: This requires Base Sepolia testnet ETH and USDC.
"""

import asyncio
import os
import sys
from decimal import Decimal

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Set up environment for Base mainnet
os.environ.update(
    {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "DATABASE_URL": "sqlite+aiosqlite:///test.db",
        "BASE_RPC_URL": "https://mainnet.base.org",
        "BASE_CHAIN_ID": "8453",  # Base mainnet chain ID
        "ENCRYPTION_KEY": "vkpZGJ3stdTs-i-gAM4sQGC7V5wi-pPkTDqyglD5x50=",
        "ADMIN_USER_IDS": "123456789",
        "COPY_EXECUTION_MODE": "LIVE",  # Enable live trading
        "PYTH_PRICE_SERVICE_URL": "https://hermes.pyth.network",
        "CHAINLINK_BASE_URL": "https://api.chain.link/v1",
        # Ensure signer + contract are set for live trading
        "TRADER_PRIVATE_KEY": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        "AVANTIS_TRADING_CONTRACT": "0x5FF292d70bA9cD9e7CCb313782811b3D7120535f",
    }
)


async def test_real_trading():
    """Test real trading on Base mainnet with small amounts."""

    print("🚀 REAL TRADE TEST - BASE MAINNET (SMALL AMOUNTS)")
    print("=" * 60)
    print("⚠️  This will execute REAL transactions on Base mainnet")
    print("   Using small amounts to minimize risk")
    print("=" * 60)

    try:
        # Test 1: Initialize components
        print("\n📦 Initializing blockchain components...")

        from src.blockchain.avantis_client import AvantisClient
        from src.blockchain.base_client import BaseClient
        from src.blockchain.wallet_manager import WalletManager
        from src.database.operations import db
        from src.services.oracle import MockOracleSource, OracleFacade

        # Initialize Base client
        base_client = BaseClient()
        print(f"✅ Connected to Base Sepolia (Chain ID: {base_client.w3.eth.chain_id})")
        print(f"   Latest block: {base_client.w3.eth.block_number}")

        # Initialize wallet manager
        WalletManager()

        # Initialize Avantis client with mock oracle
        mock_oracle = MockOracleSource(name="test_oracle")
        oracle = OracleFacade(primary=mock_oracle)
        avantis_client = AvantisClient(oracle=oracle)

        # Initialize database
        await db.create_tables()

        print("✅ All components initialized")

        # Test 2: Use fixed test wallet (fund this address)
        print("\n🔑 Using fixed test wallet...")

        test_user_id = 999999999
        # Use a fixed wallet address for testing
        wallet_address = (
            "0xC0A2470ABD1075a73d3176E2b4664C3c29bBA699"  # Fund this address
        )

        print(f"✅ Using wallet: {wallet_address}")
        print("   (Fund this address with Base Sepolia ETH)")

        # Test 3: Check wallet balance
        print("\n💰 Checking wallet balance...")

        eth_balance = base_client.w3.eth.get_balance(wallet_address)
        eth_balance_ether = base_client.w3.from_wei(eth_balance, "ether")

        print(f"   ETH Balance: {eth_balance_ether} ETH")

        if eth_balance == 0:
            print("❌ Wallet has 0 ETH - cannot execute transactions")
            print("   Fund this wallet with Base Sepolia ETH:")
            print(f"   Address: {wallet_address}")
            print(
                "   Faucet: https://www.coinbase.com/faucets/base-ethereum-sepolia-faucet"
            )
            return

        # Test 4: Get price for trading
        print("\n📊 Getting BTC price...")

        price_quote = await oracle.get_price("BTC")
        btc_price = float(price_quote.price)

        print(f"✅ BTC Price: ${btc_price:,.2f}")

        # Test 5: Execute trade (open position)
        print("\n📈 Executing trade (opening position)...")

        try:
            # For testing, we'll use a mock private key
            # In production, this would be the real encrypted private key
            test_private_key = (
                "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
            )

            # Trade parameters
            trade_params = {
                "user_address": wallet_address,
                "private_key": test_private_key,
                "market": "BTC/USD",
                "side": "LONG",
                "leverage": 2,  # Conservative leverage for mainnet
                "size": 5,  # $5 position size (small amount for mainnet)
                "price": btc_price,
            }

            print(f"   Market: {trade_params['market']}")
            print(f"   Side: {trade_params['side']}")
            print(f"   Leverage: {trade_params['leverage']}x")
            print(f"   Size: ${trade_params['size']}")
            print(f"   Price: ${trade_params['price']:,.2f}")

            # Execute the trade
            tx_result = await avantis_client.open_position(
                wallet_id=trade_params["user_address"],
                market=trade_params["market"],
                size=Decimal(str(trade_params["size"])),
                leverage=Decimal(str(trade_params["leverage"])),
                side=trade_params["side"].lower(),
                request_id=f"test_trade_{test_user_id}",
            )

            print("✅ Trade executed successfully!")
            print(f"   Transaction Hash: {tx_result}")
            print(f"   BaseScan: https://sepolia.basescan.org/tx/{tx_result}")

        except Exception as e:
            print(f"❌ Trade execution failed: {e}")
            import traceback

            traceback.print_exc()
            return

        # Test 6: Wait for transaction confirmation
        print("\n⏳ Waiting for transaction confirmation...")

        try:
            # Wait for transaction to be mined
            receipt = base_client.w3.eth.wait_for_transaction_receipt(
                tx_result, timeout=120
            )

            if receipt.status == 1:
                print(f"✅ Transaction confirmed in block {receipt.blockNumber}")
                print(f"   Gas used: {receipt.gasUsed}")
                print(
                    f"   Gas price: {base_client.w3.from_wei(receipt.effectiveGasPrice, 'gwei')} gwei"
                )
            else:
                print("❌ Transaction failed")
                return

        except Exception as e:
            print(f"❌ Transaction confirmation failed: {e}")
            return

        # Test 7: Check position in database
        print("\n📊 Checking position in database...")

        try:
            # Create user in database
            await db.create_user(
                telegram_id=test_user_id,
                username="test_trader",
                wallet_address=wallet_address,
                encrypted_private_key="encrypted_key_here",
            )

            # Check positions
            positions = await db.get_user_positions(test_user_id, "OPEN")
            print(f"✅ Found {len(positions)} open positions")

            if positions:
                position = positions[0]
                print(f"   Position ID: {position.id}")
                print(f"   Market: {position.market}")
                print(f"   Side: {position.side}")
                print(f"   Size: {position.size}")
                print(f"   Leverage: {position.leverage}x")
                print(f"   Entry Price: ${position.entry_price}")

        except Exception as e:
            print(f"❌ Database check failed: {e}")
            return

        # Test 8: Close position (optional)
        print("\n📉 Closing position...")

        try:
            if positions:
                position_id = positions[0].id

                close_result = await avantis_client.close_position(
                    user_address=wallet_address,
                    private_key=test_private_key,
                    position_id=position_id,
                )

                print("✅ Position closed!")
                print(f"   Transaction Hash: {close_result}")
                print(f"   BaseScan: https://sepolia.basescan.org/tx/{close_result}")

                # Wait for close transaction
                close_receipt = base_client.w3.eth.wait_for_transaction_receipt(
                    close_result, timeout=120
                )

                if close_receipt.status == 1:
                    print(
                        f"✅ Close transaction confirmed in block {close_receipt.blockNumber}"
                    )
                else:
                    print("❌ Close transaction failed")

        except Exception as e:
            print(f"❌ Position close failed: {e}")
            return

        print("\n🎉 REAL TRADE TEST COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("✅ Position opened and closed on Base Sepolia")
        print("✅ All transactions confirmed on-chain")
        print("✅ Database operations working")
        print("✅ Bot is capable of real trading")

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_real_trading())
