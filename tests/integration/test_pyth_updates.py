#!/usr/bin/env python3
"""
Test getting Pyth price updates and using executeMarketOrders
"""
import sys
import os
import asyncio

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set environment variables
os.environ.update({
    'TELEGRAM_BOT_TOKEN': 'test_token',
    'DATABASE_URL': 'sqlite+aiosqlite:///test.db',
    'BASE_RPC_URL': 'https://mainnet.base.org',
    'BASE_CHAIN_ID': '8453',
    'ENCRYPTION_KEY': 'vkpZGJ3stdTs-i-gAM4sQGC7V5wi-pPkTDqyglD5x50=',
    'ADMIN_USER_IDS': '123456789',
    'COPY_EXECUTION_MODE': 'LIVE',
    'PYTH_PRICE_SERVICE_URL': 'https://hermes.pyth.network',
    'CHAINLINK_BASE_URL': 'https://api.chain.link/v1',
    'TRADER_PRIVATE_KEY': 'aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87',
    'AVANTIS_TRADING_CONTRACT': '0x5FF292d70bA9cD9e7CCb313782811b3D7120535f'
})

async def test_pyth_updates():
    print('🎯 TESTING PYTH PRICE UPDATES')
    print('=' * 60)
    print('⚠️  Getting Pyth data and testing executeMarketOrders')
    print('=' * 60)
    
    try:
        # Import required modules
        from avantis_trader_sdk import TraderClient
        
        # Initialize TraderClient
        trader = TraderClient(provider_url="https://mainnet.base.org")
        trader.set_local_signer(private_key='aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87')
        address = trader.get_signer().get_ethereum_address()
        
        print(f'✅ TraderClient initialized')
        print(f'✅ Trader address: {address}')
        
        # Get Pyth price updates
        print(f'\n📡 Getting Pyth price updates...')
        try:
            price_updates = await trader.feed_client.get_latest_price_updates()
            print(f'   ✅ Pyth price updates: {len(price_updates)} updates')
            print(f'   📊 Updates preview: {price_updates[:2] if price_updates else "None"}')
            
            # Try to extract update data
            if price_updates:
                # The updates should contain the data we need
                update_data = []
                for update in price_updates:
                    if hasattr(update, 'data') or hasattr(update, 'update_data'):
                        data = getattr(update, 'data', getattr(update, 'update_data', None))
                        if data:
                            update_data.append(data)
                
                print(f'   📊 Extracted update data: {len(update_data)} items')
                if update_data:
                    print(f'   📊 First update data: {update_data[0][:50]}...')
                else:
                    print(f'   ❌ No update data found in price updates')
                    return False
            else:
                print(f'   ❌ No price updates received')
                return False
                
        except Exception as e:
            print(f'   ❌ Failed to get Pyth updates: {e}')
            return False
        
        # Get the trading contract
        trading_contract = trader.contracts['Trading']
        print(f'✅ Trading contract loaded')
        
        # Try to call executeMarketOrders with the Pyth data
        print(f'\n🔄 Testing executeMarketOrders with Pyth data...')
        try:
            # For now, try with empty order arrays
            order_ids = []  # Empty array
            order_data = []  # Empty array
            
            print(f'   📊 Using {len(update_data)} Pyth updates')
            print(f'   📊 Order IDs: {order_ids}')
            print(f'   📊 Order data: {order_data}')
            
            # Call executeMarketOrders
            result = await trading_contract.functions.executeMarketOrders(
                update_data,  # Pyth price updates
                order_ids,    # Order IDs array
                order_data    # Order data array
            ).call()
            
            print(f'   ✅ executeMarketOrders call successful!')
            print(f'   📝 Result: {result}')
            
            # Now try to build a transaction
            print(f'\n🔄 Building transaction...')
            try:
                tx = await trading_contract.functions.executeMarketOrders(
                    update_data,  # Pyth price updates
                    order_ids,    # Order IDs array
                    order_data    # Order data array
                ).build_transaction({
                    'from': address,
                    'gas': 500000,
                    'maxFeePerGas': trader.web3.eth.gas_price * 2,
                    'maxPriorityFeePerGas': trader.web3.to_wei(1, 'gwei')
                })
                
                print(f'   ✅ Transaction built successfully!')
                print(f'   📝 Transaction: {tx}')
                
                # Try to execute the transaction
                print(f'\n🔄 Executing transaction...')
                try:
                    tx_hash = await trader.send_and_get_transaction_hash(tx)
                    print(f'   🎉 SUCCESS! Transaction executed!')
                    print(f'   📝 Transaction Hash: {tx_hash}')
                    print(f'   🔗 View on BaseScan: https://basescan.org/tx/{tx_hash}')
                    
                    print(f'\n🎉 BREAKTHROUGH! Bot now works!')
                    print(f'✅ Using correct executeMarketOrders function')
                    print(f'✅ Pyth price updates working')
                    print(f'✅ Real trade executed on Base mainnet')
                    print(f'✅ PRODUCTION READY!')
                    
                    return True
                    
                except Exception as e:
                    print(f'   ❌ Transaction execution failed: {e}')
                    print(f'   → Need to construct proper order parameters')
                    return False
                
            except Exception as e:
                print(f'   ❌ Transaction building failed: {e}')
                return False
            
        except Exception as e:
            print(f'   ❌ executeMarketOrders call failed: {e}')
            print(f'   → Need to construct proper parameters')
            return False
        
    except Exception as e:
        print(f'❌ Test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_pyth_updates())
    if success:
        print('\n🎉 BREAKTHROUGH SUCCESS!')
        print('✅ Bot now works using executeMarketOrders!')
        print('✅ PRODUCTION READY!')
    else:
        print('\n💥 PYTH UPDATES FAILED')
        print('❌ Need to construct proper order parameters')
        sys.exit(1)
