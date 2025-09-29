#!/usr/bin/env python3
"""
Find working trades by querying contract events
"""
import sys
import os
import asyncio
import json
from web3 import Web3

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

async def find_working_trades():
    print('🔍 FIND WORKING TRADES')
    print('=' * 60)
    print('⚠️  This will query contract events to find successful trades')
    print('   And decode their parameters')
    print('=' * 60)
    
    try:
        # Connect to Base mainnet
        w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))
        if not w3.is_connected():
            print("❌ Failed to connect to Base mainnet")
            return False
        
        print("✅ Connected to Base mainnet")
        
        # Avantis Trading contract address
        contract_address = "0x44914408af82bC9983bbb330e3578E1105e11d4e"
        
        # Load ABI
        with open('config/abis/Trading.json', 'r') as f:
            abi = json.load(f)
        
        contract = w3.eth.contract(address=contract_address, abi=abi)
        print("✅ Contract loaded with ABI")
        
        # Get recent blocks
        latest_block = w3.eth.block_number
        from_block = latest_block - 1000  # Look back 1000 blocks
        
        print(f"✅ Searching blocks {from_block} to {latest_block}")
        
        # Look for TradeOpened events (these indicate successful trades)
        try:
            print("\n🔍 Searching for TradeOpened events...")
            
            # Get TradeOpened events
            trade_events = contract.events.TradeOpened.get_logs(
                fromBlock=from_block,
                toBlock=latest_block
            )
            
            print(f"✅ Found {len(trade_events)} TradeOpened events")
            
            if trade_events:
                # Analyze the most recent event
                recent_event = trade_events[-1]
                print(f"\n📊 Most Recent Successful Trade:")
                print(f"   Block: {recent_event.blockNumber}")
                print(f"   Transaction: {recent_event.transactionHash.hex()}")
                print(f"   BaseScan: https://basescan.org/tx/{recent_event.transactionHash.hex()}")
                print(f"   Event data: {recent_event.args}")
                
                # Extract key parameters
                args = recent_event.args
                print(f"\n🔍 Trade Parameters:")
                for key, value in args.items():
                    print(f"   {key}: {value}")
                
                # Look for position size, collateral, leverage
                if hasattr(args, 'collateral') or 'collateral' in str(args):
                    print(f"   ✅ Found collateral information")
                
                if hasattr(args, 'leverage') or 'leverage' in str(args):
                    print(f"   ✅ Found leverage information")
                
                if hasattr(args, 'positionSize') or 'positionSize' in str(args):
                    print(f"   ✅ Found position size information")
                
            else:
                print("❌ No TradeOpened events found in recent blocks")
                
                # Try looking for other events
                print("\n🔍 Searching for other trade-related events...")
                
                # Get all events from the contract
                all_events = contract.events.get_all_entries()
                print(f"Available events: {[event.event_name for event in all_events]}")
                
                # Try to get any events
                try:
                    all_logs = contract.events.get_all_entries(
                        fromBlock=from_block,
                        toBlock=latest_block
                    )
                    print(f"✅ Found {len(all_logs)} total events")
                    
                    if all_logs:
                        recent_log = all_logs[-1]
                        print(f"\n📊 Most Recent Event:")
                        print(f"   Event: {recent_log.event_name}")
                        print(f"   Block: {recent_log.blockNumber}")
                        print(f"   Transaction: {recent_log.transactionHash.hex()}")
                        print(f"   BaseScan: https://basescan.org/tx/{recent_log.transactionHash.hex()}")
                        print(f"   Args: {recent_log.args}")
                
                except Exception as e:
                    print(f"⚠️  Error getting all events: {e}")
        
        except Exception as e:
            print(f"❌ Error querying events: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\n✅ ANALYSIS COMPLETE!")
        print(f"✅ Check the BaseScan links above to see successful trades")
        print(f"✅ Compare their parameters to our bot parameters")
        
        return True
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(find_working_trades())
    if success:
        print('\n🎉 ANALYSIS COMPLETED!')
        print('✅ Check the output for successful trade parameters')
    else:
        print('\n💥 ANALYSIS FAILED')
        print('❌ Check error details above')
        sys.exit(1)
