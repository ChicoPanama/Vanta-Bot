#!/usr/bin/env python3
"""
Debug pairs and parameters test
"""
import sys
import os
import asyncio
from decimal import Decimal

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

async def debug_pairs_and_parameters():
    print('🔍 DEBUG PAIRS AND PARAMETERS TEST')
    print('=' * 60)
    print('⚠️  This will query Avantis pairs and parameters')
    print('   To debug the BELOW_MIN_POS error')
    print('=' * 60)
    
    # Test wallet details
    wallet_address = '0xdCDca231d02F1a8B85B701Ce90fc32c48a673982'
    test_private_key = 'aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87'
    
    try:
        # Test SDK TraderClient
        from avantis_trader_sdk import TraderClient
        print('✅ Avantis SDK TraderClient imported successfully')
        
        # Initialize TraderClient
        trader = TraderClient(
            provider_url="https://mainnet.base.org"
        )
        trader.set_local_signer(private_key=test_private_key)
        print('✅ TraderClient initialized with signer')
        
        # Get available pairs
        print('\n🔄 Querying available pairs...')
        try:
            # Try to get pairs information
            pairs_info = await trader.pairs.get_all_pairs()
            print(f'✅ Found {len(pairs_info)} pairs')
            
            for i, pair in enumerate(pairs_info):
                print(f'  Pair {i}: {pair}')
                
        except Exception as e:
            print(f'⚠️  Could not get pairs via SDK: {e}')
            print('Trying alternative method...')
        
        # Try alternative method to get pairs
        try:
            # Check if there's a pairs cache or different method
            if hasattr(trader, 'pairs_cache'):
                pairs_count = await trader.pairs_cache.get_pairs_count()
                print(f'✅ Pairs count: {pairs_count}')
                
                # Get details for first few pairs
                for i in range(min(5, pairs_count)):
                    try:
                        pair_name = await trader.pairs_cache.get_pair_name_from_index(i)
                        print(f'  Pair {i}: {pair_name}')
                    except Exception as e:
                        print(f'  Pair {i}: Error getting name - {e}')
                        
        except Exception as e:
            print(f'⚠️  Could not get pairs count: {e}')
        
        # Check current open interest for pair 0
        print('\n🔄 Checking open interest for pair 0...')
        try:
            # Try to get open interest information
            if hasattr(trader, 'asset_parameters'):
                oi_info = await trader.asset_parameters.get_pair_oi(0)
                print(f'✅ Open interest for pair 0: {oi_info}')
            else:
                print('⚠️  Asset parameters not available')
        except Exception as e:
            print(f'⚠️  Could not get open interest: {e}')
        
        # Check pair limits
        print('\n🔄 Checking pair limits...')
        try:
            if hasattr(trader, 'asset_parameters'):
                max_oi = await trader.asset_parameters.get_pair_max_oi(0)
                print(f'✅ Max open interest for pair 0: {max_oi}')
            else:
                print('⚠️  Asset parameters not available')
        except Exception as e:
            print(f'⚠️  Could not get pair limits: {e}')
        
        # Test parameter construction
        print('\n🔄 Testing parameter construction...')
        try:
            from avantis_trader_sdk.types import TradeInput, TradeInputOrderType
            
            # Get the ethereum address
            address = trader.get_signer().get_ethereum_address()
            print(f'✅ Trader address: {address}')
            
            # Test different parameter combinations
            test_cases = [
                {'collateral': 10 * 10**6, 'leverage': 2, 'desc': '10 USDC, 2x leverage'},
                {'collateral': 50 * 10**6, 'leverage': 10, 'desc': '50 USDC, 10x leverage'},
                {'collateral': 100 * 10**6, 'leverage': 50, 'desc': '100 USDC, 50x leverage'},
                {'collateral': 1000 * 10**6, 'leverage': 10, 'desc': '1000 USDC, 10x leverage'},
            ]
            
            for i, test_case in enumerate(test_cases):
                print(f'\n  Test case {i+1}: {test_case["desc"]}')
                print(f'    Collateral: {test_case["collateral"]} (wei)')
                print(f'    Leverage: {test_case["leverage"]}x')
                print(f'    Position size: {test_case["collateral"] * test_case["leverage"] / 10**6} USDC')
                
                # Create TradeInput
                trade_input = TradeInput(
                    pair_index=0,
                    is_long=True,
                    open_collateral=test_case['collateral'],
                    leverage=test_case['leverage'],
                    tp=0,
                    sl=0,
                    trader=address
                )
                
                print(f'    TradeInput created successfully')
                
                # Try to build transaction (this will likely fail but show us the error)
                try:
                    trade_tx = await trader.trade.build_trade_open_tx(
                        trade_input=trade_input,
                        trade_input_order_type=TradeInputOrderType.MARKET,
                        slippage_percentage=100  # 1% slippage
                    )
                    print(f'    ✅ Transaction built successfully!')
                    break
                except Exception as e:
                    print(f'    ❌ Failed: {e}')
                    if 'BELOW_MIN_POS' in str(e):
                        print(f'    → Still below minimum position size')
                    else:
                        print(f'    → Different error: {e}')
                        
        except Exception as e:
            print(f'❌ Parameter construction failed: {e}')
            import traceback
            traceback.print_exc()
        
        print('\n✅ DEBUG COMPLETE!')
        print('✅ Check the output above for:')
        print('  - Available pairs and their indexes')
        print('  - Open interest limits')
        print('  - Which parameter combination works')
        
        return True
        
    except Exception as e:
        print(f'❌ Debug failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_pairs_and_parameters())
    if success:
        print('\n🎉 DEBUG TEST COMPLETED!')
        print('✅ Check the output for pair information and working parameters')
    else:
        print('\n💥 DEBUG TEST FAILED')
        print('❌ Check error details above')
        sys.exit(1)
