#!/usr/bin/env python3
"""
Debug the actual values being sent
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

async def debug_actual_values():
    print('🔍 DEBUG ACTUAL VALUES')
    print('=' * 60)
    print('⚠️  This will show the exact values being sent to the contract')
    print('   To identify why BELOW_MIN_POS error occurs')
    print('=' * 60)
    
    try:
        # Import required modules
        from avantis_trader_sdk import TraderClient
        from avantis_trader_sdk.types import TradeInput, TradeInputOrderType
        
        # Initialize TraderClient
        trader = TraderClient(provider_url="https://mainnet.base.org")
        trader.set_local_signer(private_key='aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87')
        address = trader.get_signer().get_ethereum_address()
        
        print(f'✅ TraderClient initialized')
        print(f'✅ Trader address: {address}')
        
        # Test different parameter combinations
        test_cases = [
            {
                'name': '100 USDC, 10x leverage',
                'initialPosToken': 100 * 10**6,  # 100 USDC in wei
                'leverage': 10,  # 10x leverage
                'expected_position': 100 * 10 * 10**6  # 1000 USDC in wei
            },
            {
                'name': '100 USDC, 100x leverage',
                'initialPosToken': 100 * 10**6,  # 100 USDC in wei
                'leverage': 100,  # 100x leverage
                'expected_position': 100 * 100 * 10**6  # 10000 USDC in wei
            },
            {
                'name': '1000 USDC, 10x leverage',
                'initialPosToken': 1000 * 10**6,  # 1000 USDC in wei
                'leverage': 10,  # 10x leverage
                'expected_position': 1000 * 10 * 10**6  # 10000 USDC in wei
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            print(f'\n🔄 Test case {i+1}: {test_case["name"]}')
            print(f'   initialPosToken: {test_case["initialPosToken"]} (wei)')
            print(f'   leverage: {test_case["leverage"]}x')
            print(f'   Expected position: {test_case["expected_position"]} (wei)')
            print(f'   Expected position: {test_case["expected_position"] / 10**6} USDC')
            
            try:
                # Create TradeInput
                trade_input = TradeInput(
                    pairIndex=1,  # BTC/USD
                    buy=True,     # LONG
                    initialPosToken=test_case['initialPosToken'],
                    leverage=test_case['leverage'],
                    tp=0,
                    sl=0,
                    trader=address
                )
                
                print(f'   ✅ TradeInput created successfully')
                print(f'   Actual initialPosToken: {trade_input.initialPosToken}')
                print(f'   Actual leverage: {trade_input.leverage}')
                
                # Try to build transaction
                trade_tx = await trader.trade.build_trade_open_tx(
                    trade_input=trade_input,
                    trade_input_order_type=TradeInputOrderType.MARKET,
                    slippage_percentage=100
                )
                
                print(f'   ✅ Transaction built successfully!')
                print(f'   📝 Transaction: {trade_tx}')
                
                # Try to execute
                tx_hash = await trader.send_and_get_transaction_hash(trade_tx)
                print(f'   ✅ Trade executed successfully!')
                print(f'   📝 Transaction Hash: {tx_hash}')
                print(f'   🔗 View on BaseScan: https://basescan.org/tx/{tx_hash}')
                
                print(f'\n🎉 SUCCESS! {test_case["name"]} worked!')
                return True
                
            except Exception as e:
                if 'BELOW_MIN_POS' in str(e):
                    print(f'   ❌ Still below minimum position size')
                    print(f'   → Current position: {test_case["expected_position"] / 10**6} USDC')
                    print(f'   → This suggests minimum is higher than {test_case["expected_position"] / 10**6} USDC')
                else:
                    print(f'   ❌ Different error: {e}')
                continue
        
        print(f'\n❌ All test cases failed with BELOW_MIN_POS error')
        print(f'This suggests the Avantis protocol has extremely high minimum position requirements')
        print(f'Possibly $50,000+ or more for any pair')
        
        return False
        
    except Exception as e:
        print(f'❌ Debug failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_actual_values())
    if success:
        print('\n🎉 DEBUG COMPLETED!')
        print('✅ Found working parameters')
    else:
        print('\n💥 DEBUG FAILED')
        print('❌ All test cases failed')
        sys.exit(1)
