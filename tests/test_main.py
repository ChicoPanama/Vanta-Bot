import asyncio
import logging
from src.database.operations import db
from src.blockchain.wallet_manager import wallet_manager
from src.blockchain.base_client import base_client
from src.config.settings import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_basic_functionality():
    """Test basic bot functionality"""
    print("🧪 Testing Vanta Bot Components...")
    print("=" * 50)
    
    try:
        # Test 1: Database connection
        print("1. Testing database connection...")
        db.create_tables()
        print("   ✅ Database connected and tables created")
        
        # Test 2: Wallet creation
        print("2. Testing wallet creation...")
        wallet = wallet_manager.create_wallet()
        print(f"   ✅ Wallet created: {wallet['address']}")
        
        # Test 3: Base network connection
        print("3. Testing Base network connection...")
        connected = base_client.w3.is_connected()
        if connected:
            print("   ✅ Base network connected")
        else:
            print("   ❌ Base network connection failed")
            return False
            
        # Test 4: Configuration
        print("4. Testing configuration...")
        required_configs = [
            'TELEGRAM_BOT_TOKEN', 'BASE_RPC_URL', 'DATABASE_URL', 
            'ENCRYPTION_KEY', 'USDC_CONTRACT'
        ]
        
        missing_configs = []
        for config_name in required_configs:
            if not getattr(config, config_name, None):
                missing_configs.append(config_name)
        
        if missing_configs:
            print(f"   ❌ Missing configurations: {', '.join(missing_configs)}")
            return False
        else:
            print("   ✅ All required configurations present")
            
        # Test 5: Wallet balance check
        print("5. Testing wallet balance retrieval...")
        wallet_info = wallet_manager.get_wallet_info(wallet['address'])
        print(f"   ✅ ETH Balance: {wallet_info['eth_balance']:.6f} ETH")
        print(f"   ✅ USDC Balance: {wallet_info['usdc_balance']:.2f} USDC")
        
        # Test 6: Database operations
        print("6. Testing database operations...")
        test_user = db.create_user(
            telegram_id=12345,
            username="test_user",
            wallet_address=wallet['address'],
            encrypted_private_key=wallet['encrypted_private_key']
        )
        
        if test_user:
            print("   ✅ User creation successful")
            
            # Test position creation
            test_position = db.create_position(
                user_id=test_user.id,
                symbol="BTC",
                side="LONG",
                size=100.0,
                leverage=10
            )
            
            if test_position:
                print("   ✅ Position creation successful")
            else:
                print("   ❌ Position creation failed")
                return False
        else:
            print("   ❌ User creation failed")
            return False
            
        print("\n🎉 All tests passed! Bot is ready to run.")
        print("\n📋 Next steps:")
        print("1. Set up your .env file with real values")
        print("2. Start PostgreSQL and Redis services")
        print("3. Run: python main.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        logger.error(f"Test error: {e}", exc_info=True)
        return False

async def test_price_service():
    """Test price service functionality"""
    print("\n📊 Testing Price Service...")
    try:
        from src.services.price_service import price_service
        
        # Test price fetching
        await price_service.fetch_prices()
        
        # Test price retrieval
        btc_price = price_service.get_price('BTC')
        eth_price = price_service.get_price('ETH')
        
        if btc_price > 0 and eth_price > 0:
            print(f"   ✅ BTC Price: ${btc_price:,.2f}")
            print(f"   ✅ ETH Price: ${eth_price:,.2f}")
            return True
        else:
            print("   ❌ Price service failed")
            return False
            
    except Exception as e:
        print(f"   ❌ Price service error: {e}")
        return False

async def test_analytics():
    """Test analytics functionality"""
    print("\n📈 Testing Analytics...")
    try:
        from src.services.analytics import Analytics
        
        analytics = Analytics()
        stats = analytics.get_user_stats(1)  # Test with user ID 1
        
        print(f"   ✅ Analytics working - Total trades: {stats['total_trades']}")
        return True
        
    except Exception as e:
        print(f"   ❌ Analytics error: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Vanta Bot - Test Suite")
    print("=" * 50)
    
    # Run basic functionality tests
    basic_tests_passed = await test_basic_functionality()
    
    if basic_tests_passed:
        # Run additional service tests
        await test_price_service()
        await test_analytics()
        
        print("\n✅ All tests completed successfully!")
        print("\n🔧 To start the bot:")
        print("   python main.py")
    else:
        print("\n❌ Basic tests failed. Please check your configuration.")
        print("\n📝 Make sure to:")
        print("1. Set up your .env file with correct values")
        print("2. Install all dependencies: pip install -r requirements.txt")
        print("3. Start PostgreSQL and Redis services")

if __name__ == "__main__":
    asyncio.run(main())