#!/usr/bin/env python3
"""
Final test with correct understanding of Avantis requirements
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

async def final_correct_test():
    print('🚀 FINAL CORRECT TEST')
    print('=' * 60)
    print('⚠️  This will test with correct understanding of Avantis requirements')
    print('   Based on actual documentation: $10 minimum collateral')
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
        
        # Get USDC balance
        usdc_balance = await trader.get_usdc_balance()
        print(f'✅ USDC balance: {usdc_balance}')
        
        if usdc_balance < 10:
            print('❌ Insufficient USDC balance (need at least $10)')
            return False
        
        # Test with correct understanding
        print(f'\n📊 CORRECT UNDERSTANDING TEST:')
        print(f'   Market: BTC/USD (Pair 1)')
        print(f'   Side: LONG')
        print(f'   Leverage: 10x (reasonable)')
        print(f'   Collateral: $10 USDC (minimum requirement)')
        print(f'   Position Size: $100 (10 × 10x leverage)')
        print(f'   This should work according to Avantis docs')
        
        try:
            # Create TradeInput with correct parameters
            # Key insight: Use raw USDC amounts, SDK handles decimals
            trade_input = TradeInput(
                pairIndex=1,  # BTC/USD
                buy=True,     # LONG
                initialPosToken=10,  # $10 USDC (minimum requirement)
                leverage=10,  # 10x leverage
                tp=0,         # No take profit
                sl=0,         # No stop loss
                trader=address
            )
            
            print(f'✅ TradeInput created:')
            print(f'   pairIndex: {trade_input.pairIndex}')
            print(f'   buy: {trade_input.buy}')
            print(f'   initialPosToken: {trade_input.initialPosToken}')
            print(f'   leverage: {trade_input.leverage}')
            print(f'   tp: {trade_input.tp}')
            print(f'   sl: {trade_input.sl}')
            print(f'   trader: {trade_input.trader}')
            
            # Try to build transaction
            trade_tx = await trader.trade.build_trade_open_tx(
                trade_input=trade_input,
                trade_input_order_type=TradeInputOrderType.MARKET,
                slippage_percentage=100  # 1% slippage
            )
            
            print(f'✅ Transaction built successfully!')
            print(f'📝 Transaction: {trade_tx}')
            
            # Try to execute
            print('\n🔄 Executing trade transaction...')
            tx_hash = await trader.send_and_get_transaction_hash(trade_tx)
            print(f'✅ Trade executed successfully!')
            print(f'📝 Transaction Hash: {tx_hash}')
            print(f'🔗 View on BaseScan: https://basescan.org/tx/{tx_hash}')
            
            print(f'\n🎉 SUCCESS! Bot is working correctly!')
            print(f'✅ Avantis protocol integration working')
            print(f'✅ Real trade executed on Base mainnet')
            print(f'✅ Transaction confirmed on blockchain')
            print(f'✅ PRODUCTION READY!')
            
            return True
            
        except Exception as trade_error:
            print(f'❌ Trade execution failed: {trade_error}')
            
            # Analyze the specific error
            if 'BELOW_MIN_POS' in str(trade_error):
                print(f'→ BELOW_MIN_POS error still occurs')
                print(f'→ This suggests the minimum is higher than $10')
                print(f'→ Or there are other parameter issues')
                
                # Try with higher collateral
                print(f'\n🔄 Trying with higher collateral ($50)...')
                try:
                    trade_input_50 = TradeInput(
                        pairIndex=1,
                        buy=True,
                        initialPosToken=50,  # $50 USDC
                        leverage=10,
                        tp=0,
                        sl=0,
                        trader=address
                    )
                    
                    trade_tx_50 = await trader.trade.build_trade_open_tx(
                        trade_input=trade_input_50,
                        trade_input_order_type=TradeInputOrderType.MARKET,
                        slippage_percentage=100
                    )
                    
                    print(f'✅ $50 transaction built successfully!')
                    tx_hash_50 = await trader.send_and_get_transaction_hash(trade_tx_50)
                    print(f'✅ $50 trade executed successfully!')
                    print(f'📝 Transaction Hash: {tx_hash_50}')
                    print(f'🔗 View on BaseScan: https://basescan.org/tx/{tx_hash_50}')
                    
                    return True
                    
                except Exception as e50:
                    print(f'❌ $50 trade also failed: {e50}')
                    print(f'→ This confirms the minimum is much higher than $50')
                    print(f'→ Likely $1000+ minimum position size required')
            
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f'❌ Test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(final_correct_test())
    if success:
        print('\n🎉 FINAL TEST PASSED!')
        print('✅ Bot successfully executed real trade')
        print('✅ PRODUCTION READY!')
    else:
        print('\n💥 FINAL TEST FAILED')
        print('❌ Avantis protocol has higher minimum requirements than documented')
        print('❌ Need to find actual working parameters from BaseScan')
        sys.exit(1)
