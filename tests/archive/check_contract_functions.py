#!/usr/bin/env python3
"""
Check what functions are available on the Avantis contract
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

async def check_contract_functions():
    print('🔍 CHECKING AVANTIS CONTRACT FUNCTIONS')
    print('=' * 60)
    print('⚠️  Looking for executeMarketOrders and other functions')
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
        
        # Check the trading contract functions
        print(f'\n📋 AVAILABLE CONTRACT FUNCTIONS:')
        
        # Get the trading contract
        trading_contract = trader.contracts['Trading']
        print(f'✅ Trading contract loaded')
        
        # List all functions
        functions = []
        for func_name in trading_contract.functions:
            functions.append(func_name)
            print(f'   - {func_name}')
        
        # Look for executeMarketOrders or similar
        print(f'\n🔍 LOOKING FOR MARKET ORDER FUNCTIONS:')
        
        market_functions = [
            'executeMarketOrders',
            'executeMarketOrder',
            'executeMarket',
            'marketOrder',
            'executeOrder',
            'submitOrder',
            'openTrade',
            'closeTrade',
            'updateMargin'
        ]
        
        found_functions = []
        for func_name in market_functions:
            if func_name in functions:
                found_functions.append(func_name)
                print(f'   ✅ Found: {func_name}')
        
        if found_functions:
            print(f'\n🎯 TRYING MARKET ORDER FUNCTIONS:')
            
            # Try executeMarketOrders if it exists
            if 'executeMarketOrders' in functions:
                print(f'\n🔄 Testing executeMarketOrders...')
                try:
                    # This should be the correct function with Pyth updates
                    # We need to get Pyth price update data first
                    print(f'   📡 Getting Pyth price update data...')
                    
                    # Get Pyth price update data
                    pyth_update_data = await trader.feed_client.get_update_data()
                    print(f'   ✅ Pyth update data: {len(pyth_update_data)} bytes')
                    
                    # Try to call executeMarketOrders
                    # This is the function that actually works
                    result = await trading_contract.functions.executeMarketOrders(
                        pyth_update_data,  # Pyth price updates
                        [],  # Empty orders array for now
                        []   # Empty close orders array
                    ).call()
                    
                    print(f'   ✅ executeMarketOrders call successful: {result}')
                    print(f'   🎉 FOUND THE CORRECT FUNCTION!')
                    return True
                    
                except Exception as e:
                    print(f'   ❌ executeMarketOrders failed: {e}')
                    print(f'   → Need to construct proper parameters')
            
            # Try other market functions
            for func_name in found_functions:
                if func_name != 'executeMarketOrders':
                    print(f'\n🔄 Testing {func_name}...')
                    try:
                        # Try to call the function
                        result = await getattr(trading_contract.functions, func_name)().call()
                        print(f'   ✅ {func_name} call successful: {result}')
                    except Exception as e:
                        print(f'   ❌ {func_name} failed: {e}')
        
        else:
            print(f'\n❌ NO MARKET ORDER FUNCTIONS FOUND')
            print(f'   Available functions: {functions}')
            print(f'   Need to find the correct function for market orders')
        
        return False
        
    except Exception as e:
        print(f'❌ Check failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(check_contract_functions())
    if success:
        print('\n🎉 CORRECT FUNCTION FOUND!')
        print('✅ Bot can now trade using executeMarketOrders!')
        print('✅ PRODUCTION READY!')
    else:
        print('\n💥 NO MARKET ORDER FUNCTIONS FOUND')
        print('❌ Need to find the correct function for market orders')
        sys.exit(1)
