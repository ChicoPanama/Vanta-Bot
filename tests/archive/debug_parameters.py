#!/usr/bin/env python3
"""
Debug exact parameters being sent to the contract
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

async def debug_exact_parameters():
    print('🔍 DEBUG EXACT PARAMETERS')
    print('=' * 60)
    print('⚠️  This will show EXACTLY what parameters are being sent')
    print('   To identify the real issue')
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
        
        # Get USDC balance
        usdc_balance = await trader.get_usdc_balance()
        print(f'✅ USDC balance: {usdc_balance}')
        
        # 1. Print EXACT parameters being sent
        print(f'\n📊 EXACT PARAMETERS:')
        collateral = 100  # USDC
        leverage = 100    # 100x
        position_size = collateral * leverage
        
        print(f'   Collateral: {collateral} USDC')
        print(f'   Collateral in wei: {collateral * 10**6} (USDC has 6 decimals!)')
        print(f'   Leverage: {leverage}x')
        print(f'   Position size: {position_size} USDC')
        print(f'   Position size in wei: {position_size * 10**6}')
        
        # 2. Query pair details
        print(f'\n🔍 PAIR DETAILS:')
        try:
            pairs_count = await trader.pairs_cache.get_pairs_count()
            print(f'   Total pairs: {pairs_count}')
            
            for i in range(min(10, pairs_count)):
                try:
                    pair_name = await trader.pairs_cache.get_pair_name_from_index(i)
                    print(f'   Pair {i}: {pair_name}')
                except Exception as e:
                    print(f'   Pair {i}: Error - {e}')
        except Exception as e:
            print(f'   Error getting pairs: {e}')
        
        # 3. Check what parameters are actually being sent
        print(f'\n🔍 ACTUAL PARAMETERS BEING SENT:')
        try:
            from avantis_trader_sdk.types import TradeInput, TradeInputOrderType
            
            # Get the ethereum address
            address = trader.get_signer().get_ethereum_address()
            print(f'   Trader address: {address}')
            
            # Create a TradeInput object
            trade_input = TradeInput(
                pair_index=1,  # BTC/USD
                is_long=True,  # LONG position
                open_collateral=collateral * 10**6,  # 100 USDC in wei
                leverage=leverage,  # 100x leverage
                tp=0,  # No take profit
                sl=0,   # No stop loss
                trader=address
            )
            
            print(f'   TradeInput created:')
            print(f'     pair_index: {trade_input.pair_index}')
            print(f'     is_long: {trade_input.is_long}')
            print(f'     open_collateral: {trade_input.open_collateral}')
            print(f'     leverage: {trade_input.leverage}')
            print(f'     tp: {trade_input.tp}')
            print(f'     sl: {trade_input.sl}')
            print(f'     trader: {trade_input.trader}')
            
            # Try to build the transaction to see what happens
            print(f'\n🔄 Building transaction to see exact error...')
            
            try:
                trade_tx = await trader.trade.build_trade_open_tx(
                    trade_input=trade_input,
                    trade_input_order_type=TradeInputOrderType.MARKET,
                    slippage_percentage=200  # 2% slippage
                )
                
                print(f'   ✅ Transaction built successfully!')
                print(f'   📝 Transaction: {trade_tx}')
                
            except Exception as build_error:
                print(f'   ❌ Build failed: {build_error}')
                
                # Try to extract more details from the error
                if hasattr(build_error, 'args') and len(build_error.args) > 0:
                    error_msg = build_error.args[0]
                    print(f'   Error message: {error_msg}')
                    
                    if 'BELOW_MIN_POS' in error_msg:
                        print(f'   → BELOW_MIN_POS error - position size too small')
                        print(f'   → Current position size: {position_size} USDC')
                        print(f'   → This suggests minimum is higher than {position_size} USDC')
                    else:
                        print(f'   → Different error: {error_msg}')
                
        except Exception as e:
            print(f'   ❌ Parameter creation failed: {e}')
            import traceback
            traceback.print_exc()
        
        # 4. Check successful trades on BaseScan
        print(f'\n🔍 CHECK SUCCESSFUL TRADES:')
        print(f'   Go to: https://basescan.org/address/0x44914408af82bC9983bbb330e3578E1105e11d4e')
        print(f'   Look for recent openTrade transactions')
        print(f'   Check what parameters they used')
        print(f'   Compare with our parameters above')
        
        print(f'\n✅ DEBUG COMPLETE!')
        print(f'✅ Check the output above for:')
        print(f'  - Exact parameters being sent')
        print(f'  - Pair details and indexes')
        print(f'  - Build error details')
        print(f'  - Comparison with successful trades')
        
        return True
        
    except Exception as e:
        print(f'❌ Debug failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_exact_parameters())
    if success:
        print('\n🎉 DEBUG COMPLETED!')
        print('✅ Check the output for exact parameters and error details')
    else:
        print('\n💥 DEBUG FAILED')
        print('❌ Check error details above')
        sys.exit(1)
