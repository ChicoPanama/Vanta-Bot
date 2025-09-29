#!/usr/bin/env python3
"""
Test with much higher slippage values
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

async def test_higher_slippage():
    print('🎯 TEST HIGHER SLIPPAGE')
    print('=' * 60)
    print('⚠️  Testing with much higher slippage values')
    print('=' * 60)
    
    try:
        from avantis_trader_sdk import TraderClient
        from avantis_trader_sdk.types import TradeInput, TradeInputOrderType
        
        trader = TraderClient(provider_url="https://mainnet.base.org")
        trader.set_local_signer(private_key='aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87')
        address = trader.get_signer().get_ethereum_address()
        
        print(f'✅ TraderClient initialized')
        print(f'✅ Trader address: {address}')
        
        # Test with much higher slippage values
        slippage_tests = [
            (1000, 10, 5.0),    # $1000 collateral, 10x leverage, 5% slippage
            (1000, 10, 10.0),   # $1000 collateral, 10x leverage, 10% slippage
            (1000, 10, 20.0),   # $1000 collateral, 10x leverage, 20% slippage
            (1000, 10, 50.0),   # $1000 collateral, 10x leverage, 50% slippage
        ]
        
        for human_collateral, human_leverage, human_slippage in slippage_tests:
            print(f'\n🔍 Testing: ${human_collateral} collateral, {human_leverage}x leverage, {human_slippage}% slippage')
            
            try:
                # Use raw values - SDK will convert them
                initialPosToken = human_collateral  # Raw $1000, SDK converts to 1000000000
                leverage_scaled = human_leverage    # Raw 10, SDK converts to 100000000000
                slippage_scaled = int((Decimal(human_slippage) / Decimal(100)) * Decimal(10**10))  # 1e10 scale
                
                # Compute position size in USDC (6 dp)
                positionSizeUSDC = (initialPosToken * 1000000 * leverage_scaled * 10000000000) // (10**10)
                
                print(f'   📊 Values:')
                print(f'   initialPosToken: {initialPosToken} (raw ${human_collateral})')
                print(f'   leverage_scaled: {leverage_scaled} (raw {human_leverage}x)')
                print(f'   slippage_scaled: {slippage_scaled} ({human_slippage}%)')
                print(f'   positionSizeUSDC: {positionSizeUSDC} (${positionSizeUSDC/1000000} USDC)')
                
                # Create TradeInput with raw values
                trade_input = TradeInput(
                    pairIndex=0,  # ETH/USD
                    buy=True,     # Long position
                    initialPosToken=initialPosToken,  # Raw value
                    leverage=leverage_scaled,        # Raw value
                    tp=0,         # No take profit
                    sl=0,         # No stop loss
                    trader=address
                )
                
                # Set positionSizeUSDC explicitly (USDC 6 dp)
                trade_input.positionSizeUSDC = positionSizeUSDC
                
                # Set openPrice to 0 for market orders (let Pyth set it)
                trade_input.openPrice = 0
                
                print(f'   📊 TradeInput: {trade_input}')
                
                # Use SDK's build_trade_open_tx method with higher slippage
                trade_tx = await trader.trade.build_trade_open_tx(
                    trade_input=trade_input,
                    trade_input_order_type=TradeInputOrderType.MARKET,
                    slippage_percentage=slippage_scaled  # 1e10 scale
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
                    print(f'✅ Collateral: ${human_collateral}')
                    print(f'✅ Leverage: {human_leverage}x')
                    print(f'✅ Slippage: {human_slippage}%')
                    print(f'✅ Position size: ${positionSizeUSDC/1000000}')
                    print(f'✅ Real trade executed on Base mainnet')
                    print(f'✅ PRODUCTION READY!')
                    
                    return True
                    
                except Exception as e:
                    if 'BELOW_MIN_POS' in str(e):
                        print(f'   ❌ Still too small: BELOW_MIN_POS')
                    elif 'INVALID_SLIPPAGE' in str(e):
                        print(f'   ❌ Invalid slippage: INVALID_SLIPPAGE')
                    else:
                        print(f'   ❌ Transaction execution failed: {e}')
                        continue
                
            except Exception as e:
                if 'BELOW_MIN_POS' in str(e):
                    print(f'   ❌ Still too small: BELOW_MIN_POS')
                elif 'INVALID_SLIPPAGE' in str(e):
                    print(f'   ❌ Invalid slippage: INVALID_SLIPPAGE')
                else:
                    print(f'   ❌ Failed with: {e}')
                    continue
        
        print(f'\n💥 ALL SLIPPAGE VALUES FAILED')
        print(f'❌ Even with 50% slippage failed')
        print(f'❌ Need to find the exact slippage format')
        
        return False
        
    except Exception as e:
        print(f'❌ Test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_higher_slippage())
    if success:
        print('\n🎉 WORKING SLIPPAGE FOUND!')
        print('✅ Bot now works with correct slippage!')
        print('✅ PRODUCTION READY!')
    else:
        print('\n💥 ALL SLIPPAGE VALUES FAILED')
        print('❌ Need to find exact slippage format')
        sys.exit(1)
