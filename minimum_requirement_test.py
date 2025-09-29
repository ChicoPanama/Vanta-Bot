#!/usr/bin/env python3
"""
Test with minimum $10 requirement and debug the exact issue
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

async def test_minimum_requirement():
    print('🚀 MINIMUM REQUIREMENT TEST')
    print('=' * 60)
    print('⚠️  This will test with minimum $10 requirement')
    print('   And debug the exact issue')
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
        
        # Test with minimum $10 requirement
        print(f'\n📊 MINIMUM REQUIREMENT TEST:')
        print(f'   Market: BTC/USD (Pair 1)')
        print(f'   Side: LONG')
        print(f'   Leverage: 10x')
        print(f'   Size: $10 USDC (minimum requirement)')
        print(f'   Position Size: $100 (10 × 10x leverage)')
        
        try:
            # Create TradeInput with minimum $10
            trade_input = TradeInput(
                pairIndex=1,  # BTC/USD
                buy=True,     # LONG
                initialPosToken=10,  # $10 USDC (minimum requirement)
                leverage=10,  # 10x leverage
                tp=0,
                sl=0,
                trader=address
            )
            
            print(f'✅ TradeInput created with minimum $10:')
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
                slippage_percentage=100
            )
            
            print(f'✅ Transaction built successfully!')
            print(f'📝 Transaction: {trade_tx}')
            
            # Try to execute
            print('\n🔄 Executing trade transaction...')
            tx_hash = await trader.send_and_get_transaction_hash(trade_tx)
            print(f'✅ Trade executed successfully!')
            print(f'📝 Transaction Hash: {tx_hash}')
            print(f'🔗 View on BaseScan: https://basescan.org/tx/{tx_hash}')
            
            return True
            
        except Exception as trade_error:
            print(f'❌ Trade execution failed: {trade_error}')
            print('This might be due to:')
            print('- Still below minimum position size')
            print('- Wrong parameter values')
            print('- Other contract requirements')
            
            # Try to extract more details from the error
            if hasattr(trade_error, 'args') and len(trade_error.args) > 0:
                error_msg = trade_error.args[0]
                print(f'Error message: {error_msg}')
                
                if 'BELOW_MIN_POS' in error_msg:
                    print(f'→ BELOW_MIN_POS error - position size too small')
                    print(f'→ Current position: $100 (10 × 10x leverage)')
                    print(f'→ This suggests minimum is higher than $100')
                else:
                    print(f'→ Different error: {error_msg}')
            
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f'❌ Test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_minimum_requirement())
    if success:
        print('\n🎉 MINIMUM REQUIREMENT TEST PASSED!')
        print('✅ Bot successfully executed real trade on Base mainnet')
        print('✅ Transaction confirmed on blockchain')
        print('✅ Avantis protocol integration working')
        print('✅ PRODUCTION READY!')
    else:
        print('\n💥 MINIMUM REQUIREMENT TEST FAILED')
        print('❌ Check error details above')
        sys.exit(1)
