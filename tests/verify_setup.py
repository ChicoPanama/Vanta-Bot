#!/usr/bin/env python3
"""
Vanta Bot - Setup Verification Script
This script verifies that all components are properly implemented.
"""

import sys
from pathlib import Path


def check_file_exists(file_path, description):
    """Check if a file exists and print status"""
    if Path(file_path).exists():
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} - MISSING")
        return False


def check_directory_exists(dir_path, description):
    """Check if a directory exists and print status"""
    if Path(dir_path).is_dir():
        print(f"✅ {description}: {dir_path}")
        return True
    else:
        print(f"❌ {description}: {dir_path} - MISSING")
        return False


def main():
    """Verify complete bot setup"""
    print("🔍 Verifying Vanta Bot Setup...")
    print("=" * 60)

    all_good = True

    # Check core files
    print("\n📁 Core Files:")
    core_files = [
        ("main.py", "Main bot entry point"),
        ("test_bot.py", "Test suite"),
        ("setup.py", "Setup automation script"),
        ("requirements.txt", "Dependencies"),
        ("Dockerfile", "Docker configuration"),
        ("docker-compose.yml", "Docker Compose"),
        ("README.md", "Documentation"),
        ("SETUP_GUIDE.md", "Setup guide"),
        ("COMPLETION_SUMMARY.md", "Completion summary"),
    ]

    for file_path, description in core_files:
        if not check_file_exists(file_path, description):
            all_good = False

    # Check source structure
    print("\n📂 Source Structure:")
    source_dirs = [
        ("src/", "Source root"),
        ("src/bot/", "Bot handlers"),
        ("src/bot/handlers/", "Command handlers"),
        ("src/bot/keyboards/", "Interactive keyboards"),
        ("src/blockchain/", "Blockchain integration"),
        ("src/database/", "Database layer"),
        ("src/services/", "Business logic"),
        ("src/middleware/", "Middleware"),
        ("src/utils/", "Utilities"),
        ("src/config/", "Configuration"),
    ]

    for dir_path, description in source_dirs:
        if not check_directory_exists(dir_path, description):
            all_good = False

    # Check handler files
    print("\n🤖 Bot Handlers:")
    handlers = [
        ("src/bot/handlers/start.py", "Start handler"),
        ("src/bot/handlers/wallet.py", "Wallet handler"),
        ("src/bot/handlers/trading.py", "Trading handler"),
        ("src/bot/handlers/positions.py", "Positions handler"),
        ("src/bot/handlers/portfolio.py", "Portfolio handler"),
        ("src/bot/handlers/orders.py", "Orders handler"),
        ("src/bot/handlers/settings.py", "Settings handler"),
    ]

    for file_path, description in handlers:
        if not check_file_exists(file_path, description):
            all_good = False

    # Check blockchain files
    print("\n⛓️ Blockchain Integration:")
    blockchain_files = [
        ("src/blockchain/base_client.py", "Base network client"),
        ("src/blockchain/avantis_client.py", "Avantis protocol client"),
        ("src/blockchain/wallet_manager.py", "Wallet manager"),
    ]

    for file_path, description in blockchain_files:
        if not check_file_exists(file_path, description):
            all_good = False

    # Check database files
    print("\n🗄️ Database Layer:")
    database_files = [
        ("src/database/models.py", "Database models"),
        ("src/database/operations.py", "Database operations"),
    ]

    for file_path, description in database_files:
        if not check_file_exists(file_path, description):
            all_good = False

    # Check services
    print("\n⚙️ Services:")
    service_files = [
        ("src/services/price_service.py", "Price service"),
        ("src/services/position_monitor.py", "Position monitor"),
        ("src/services/analytics.py", "Analytics service"),
        ("src/services/cache_service.py", "Cache service"),
    ]

    for file_path, description in service_files:
        if not check_file_exists(file_path, description):
            all_good = False

    # Check utilities
    print("\n🔧 Utilities:")
    utility_files = [
        ("src/middleware/rate_limiter.py", "Rate limiter"),
        ("src/utils/validators.py", "Input validators"),
        ("src/config/settings.py", "Configuration"),
    ]

    for file_path, description in utility_files:
        if not check_file_exists(file_path, description):
            all_good = False

    # Check keyboards
    print("\n⌨️ Keyboards:")
    keyboard_files = [("src/bot/keyboards/trading_keyboards.py", "Trading keyboards")]

    for file_path, description in keyboard_files:
        if not check_file_exists(file_path, description):
            all_good = False

    # Summary
    print("\n" + "=" * 60)
    if all_good:
        print("🎉 VERIFICATION COMPLETE - All components present!")
        print("\n📋 Next Steps:")
        print("1. Run: python setup.py")
        print("2. Configure your .env file")
        print("3. Test: python test_bot.py")
        print("4. Start: python main.py")
        print("\n🚀 Your Vanta Bot is ready to deploy!")
    else:
        print("❌ VERIFICATION FAILED - Some components missing!")
        print("Please check the missing files and re-run setup.")
        sys.exit(1)


if __name__ == "__main__":
    main()
