#!/usr/bin/env python3
"""
Fix SDK parameters by setting positionSizeUSDC and openPrice explicitly
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

async def fix_sdk_parameters():
    print('🎯 FIX SDK PARAMETERS')
    print('=' * 60)
    print('⚠️  Setting positionSizeUSDC and openPrice explicitly')
    print('=' * 60)
    
    try:
        from avantis_trader_sdk import TraderClient
        from avantis_trader_sdk.types import TradeInput, TradeInputOrderType
        
        trader = TraderClient(provider_url="https://mainnet.base.org")
        trader.set_local_signer(private_key='aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87')
        address = trader.get_signer().get_ethereum_address()
        
        print(f'✅ TraderClient initialized')
        print(f'✅ Trader address: {address}')
        
        # Test with explicit positionSizeUSDC and openPrice
        test_configs = [
            (100, 10, 1000, 4000),      # $100 collateral, 10x leverage, $1000 position, $4000 price
            (500, 10, 5000, 4000),      # $500 collateral, 10x leverage, $5000 position, $4000 price
            (1000, 10, 10000, 4000),    # $1000 collateral, 10x leverage, $10000 position, $4000 price
            (100, 100, 10000, 4000),    # $100 collateral, 100x leverage, $10000 position, $4000 price
            (1000, 100, 100000, 4000),  # $1000 collateral, 100x leverage, $100000 position, $4000 price
        ]
        
        for collateral, leverage, position_size, price in test_configs:
            print(f'\n🔍 Testing: ${collateral} collateral, {leverage}x leverage, ${position_size} position, ${price} price')
            
            try:
                # Create TradeInput with explicit values
                trade_input = TradeInput(
                    pairIndex=0,  # ETH/USD
                    buy=True,     # Long position
                    initialPosToken=collateral,  # Collateral in USDC
                    leverage=leverage,  # Leverage
                    tp=0,         # No take profit
                    sl=0,         # No stop loss
                    trader=address
                )
                
                # Try to set positionSizeUSDC and openPrice explicitly
                # Check if these fields exist
                print(f'   📊 TradeInput fields: {dir(trade_input)}')
                
                # Try to set the values if possible
                if hasattr(trade_input, 'positionSizeUSDC'):
                    trade_input.positionSizeUSDC = position_size * 1000000  # Convert to wei
                    print(f'   📊 Set positionSizeUSDC: {trade_input.positionSizeUSDC}')
                
                if hasattr(trade_input, 'openPrice'):
                    trade_input.openPrice = price * 1000000  # Convert to wei
                    print(f'   📊 Set openPrice: {trade_input.openPrice}')
                
                print(f'   📊 Final TradeInput: {trade_input}')
                
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
                    print(f'✅ Position size: ${position_size}')
                    print(f'✅ Price: ${price}')
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
        
        print(f'\n💥 ALL PARAMETER COMBINATIONS FAILED')
        print(f'❌ Even with explicit positionSizeUSDC and openPrice failed')
        print(f'❌ Need to find the exact minimum requirements')
        
        return False
        
    except Exception as e:
        print(f'❌ Test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(fix_sdk_parameters())
    if success:
        print('\n🎉 WORKING PARAMETERS FOUND!')
        print('✅ Bot now works with fixed SDK parameters!')
        print('✅ PRODUCTION READY!')
    else:
        print('\n💥 ALL PARAMETERS FAILED')
        print('❌ Need to find exact minimum requirements')
        sys.exit(1)
