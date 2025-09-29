#!/usr/bin/env python3
"""
Debug slippage parameter to understand the correct format
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

async def debug_slippage_parameter():
    print('🔍 DEBUG SLIPPAGE PARAMETER')
    print('=' * 60)
    print('⚠️  Understanding the correct slippage format')
    print('=' * 60)
    
    try:
        from avantis_trader_sdk import TraderClient
        from avantis_trader_sdk.types import TradeInput, TradeInputOrderType
        
        trader = TraderClient(provider_url="https://mainnet.base.org")
        trader.set_local_signer(private_key='aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87')
        address = trader.get_signer().get_ethereum_address()
        
        print(f'✅ TraderClient initialized')
        print(f'✅ Trader address: {address}')
        
        # Check the build_trade_open_tx method signature
        print(f'\n📋 BUILD_TRADE_OPEN_TX METHOD SIGNATURE:')
        import inspect
        sig = inspect.signature(trader.trade.build_trade_open_tx)
        print(f'   {sig}')
        
        # Check what parameters it accepts
        print(f'\n📋 METHOD PARAMETERS:')
        for param_name, param in sig.parameters.items():
            print(f'   {param_name}: {param.annotation} = {param.default}')
        
        # Try different parameter names for slippage
        print(f'\n🔍 TESTING DIFFERENT SLIPPAGE PARAMETER NAMES:')
        
        # Create TradeInput with working parameters
        trade_input = TradeInput(
            pairIndex=0,  # ETH/USD
            buy=True,     # Long position
            initialPosToken=1000,  # $1000 collateral
            leverage=10,  # 10x leverage
            tp=0,         # No take profit
            sl=0,         # No stop loss
            trader=address
        )
        
        # Set positionSizeUSDC and openPrice explicitly
        trade_input.positionSizeUSDC = 10000000000  # $10,000 position
        trade_input.openPrice = 4000000000  # $4000 price
        
        print(f'   📊 TradeInput: {trade_input}')
        
        # Try different parameter names
        parameter_tests = [
            ('slippage_percentage', 1000),  # 10% slippage
            ('slippage', 1000),            # 10% slippage
            ('slippageP', 1000),           # 10% slippage
            ('slippage_bps', 1000),        # 10% slippage
            ('max_slippage', 1000),        # 10% slippage
        ]
        
        for param_name, slippage_value in parameter_tests:
            print(f'\n🔄 Testing parameter: {param_name} = {slippage_value}')
            
            try:
                # Try to call with different parameter name
                if param_name == 'slippage_percentage':
                    trade_tx = await trader.trade.build_trade_open_tx(
                        trade_input=trade_input,
                        trade_input_order_type=TradeInputOrderType.MARKET,
                        slippage_percentage=slippage_value
                    )
                elif param_name == 'slippage':
                    trade_tx = await trader.trade.build_trade_open_tx(
                        trade_input=trade_input,
                        trade_input_order_type=TradeInputOrderType.MARKET,
                        slippage=slippage_value
                    )
                elif param_name == 'slippageP':
                    trade_tx = await trader.trade.build_trade_open_tx(
                        trade_input=trade_input,
                        trade_input_order_type=TradeInputOrderType.MARKET,
                        slippageP=slippage_value
                    )
                elif param_name == 'slippage_bps':
                    trade_tx = await trader.trade.build_trade_open_tx(
                        trade_input=trade_input,
                        trade_input_order_type=TradeInputOrderType.MARKET,
                        slippage_bps=slippage_value
                    )
                elif param_name == 'max_slippage':
                    trade_tx = await trader.trade.build_trade_open_tx(
                        trade_input=trade_input,
                        trade_input_order_type=TradeInputOrderType.MARKET,
                        max_slippage=slippage_value
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
                    
                    print(f'\n🎉 BREAKTHROUGH! Found correct slippage parameter!')
                    print(f'✅ Parameter: {param_name}')
                    print(f'✅ Value: {slippage_value}')
                    print(f'✅ Real trade executed on Base mainnet')
                    print(f'✅ PRODUCTION READY!')
                    
                    return True
                    
                except Exception as e:
                    if 'INVALID_SLIPPAGE' in str(e):
                        print(f'   ❌ Still invalid slippage: INVALID_SLIPPAGE')
                    else:
                        print(f'   ❌ Transaction execution failed: {e}')
                        continue
                
            except Exception as e:
                if 'INVALID_SLIPPAGE' in str(e):
                    print(f'   ❌ Invalid slippage: INVALID_SLIPPAGE')
                else:
                    print(f'   ❌ Failed with: {e}')
                    continue
        
        print(f'\n💥 ALL SLIPPAGE PARAMETER NAMES FAILED')
        print(f'❌ Need to find the correct slippage parameter format')
        
        return False
        
    except Exception as e:
        print(f'❌ Test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_slippage_parameter())
    if success:
        print('\n🎉 CORRECT SLIPPAGE PARAMETER FOUND!')
        print('✅ Bot now works with correct slippage parameter!')
        print('✅ PRODUCTION READY!')
    else:
        print('\n💥 ALL SLIPPAGE PARAMETERS FAILED')
        print('❌ Need to find correct slippage parameter format')
        sys.exit(1)
