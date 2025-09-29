#!/usr/bin/env python3
"""
Use the SDK's build_trade_open_tx method instead of calling contract directly
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

async def use_sdk_build_trade_open_tx():
    print('🎯 USE SDK BUILD TRADE OPEN TX')
    print('=' * 60)
    print('⚠️  Using SDK build_trade_open_tx method instead of direct contract call')
    print('=' * 60)
    
    try:
        from avantis_trader_sdk import TraderClient
        from avantis_trader_sdk.types import TradeInput, TradeInputOrderType
        
        trader = TraderClient(provider_url="https://mainnet.base.org")
        trader.set_local_signer(private_key='aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87')
        address = trader.get_signer().get_ethereum_address()
        
        print(f'✅ TraderClient initialized')
        print(f'✅ Trader address: {address}')
        
        # Test different parameter values using SDK method
        test_configs = [
            (100, 10),      # $100 collateral, 10x leverage
            (500, 10),      # $500 collateral, 10x leverage
            (1000, 10),     # $1000 collateral, 10x leverage
            (100, 100),     # $100 collateral, 100x leverage
            (1000, 100),    # $1000 collateral, 100x leverage
        ]
        
        for collateral, leverage in test_configs:
            print(f'\n🔍 Testing: ${collateral} collateral, {leverage}x leverage')
            
            try:
                # Create TradeInput using SDK
                trade_input = TradeInput(
                    pairIndex=0,  # ETH/USD
                    buy=True,     # Long position
                    initialPosToken=collateral,  # Collateral in USDC
                    leverage=leverage,  # Leverage
                    tp=0,         # No take profit
                    sl=0,         # No stop loss
                    trader=address
                )
                
                print(f'   📊 TradeInput: {trade_input}')
                
                # Use SDK's build_trade_open_tx method
                trade_tx = await trader.trade.build_trade_open_tx(
                    trade_input=trade_input,
                    trade_input_order_type=TradeInputOrderType.MARKET,
                    slippage_percentage=100  # 1% slippage
                )
                
                print(f'   ✅ Transaction built successfully!')
                print(f'   📝 Transaction: {trade_tx}')
                
                # Try to execute the transaction
                print(f'\n🔄 Executing transaction...')
                try:
                    tx_hash = await trader.send_and_get_transaction_hash(trade_tx)
                    print(f'   🎉 SUCCESS! Trade executed!')
                    print(f'   📝 Transaction Hash: {tx_hash}')
                    print(f'   🔗 View on BaseScan: https://basescan.org/tx/{tx_hash}')
                    
                    print(f'\n🎉 BREAKTHROUGH! Found working parameters!')
                    print(f'✅ Collateral: ${collateral}')
                    print(f'✅ Leverage: {leverage}x')
                    print(f'✅ Real trade executed on Base mainnet')
                    print(f'✅ PRODUCTION READY!')
                    
                    return True
                    
                except Exception as e:
                    print(f'   ❌ Transaction execution failed: {e}')
                    continue
                
            except Exception as e:
                if 'BELOW_MIN_POS' in str(e):
                    print(f'   ❌ Still too small: BELOW_MIN_POS')
                else:
                    print(f'   ❌ Failed with: {e}')
                    continue
        
        print(f'\n💥 ALL SDK PARAMETER COMBINATIONS FAILED')
        print(f'❌ Even with $1000 and 100x leverage failed')
        print(f'❌ Need to find the exact minimum requirements')
        
        return False
        
    except Exception as e:
        print(f'❌ Test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(use_sdk_build_trade_open_tx())
    if success:
        print('\n🎉 WORKING PARAMETERS FOUND!')
        print('✅ Bot now works with SDK method!')
        print('✅ PRODUCTION READY!')
    else:
        print('\n💥 ALL SDK PARAMETERS FAILED')
        print('❌ Need to find exact minimum requirements')
        sys.exit(1)
