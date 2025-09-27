#!/bin/bash

echo "🚀 Deploying Vanta Bot..."
echo "=================================="

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp env.example .env
    echo "📝 Please edit .env file with your configuration values"
    echo "   - TELEGRAM_BOT_TOKEN"
    echo "   - BASE_RPC_URL" 
    echo "   - DATABASE_URL"
    echo "   - ENCRYPTION_KEY"
    echo ""
    echo "Then run this script again."
    exit 1
fi

echo "✅ .env file found"

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✅ Python version $python_version is compatible"
else
    echo "❌ Python 3.9+ required, found $python_version"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Test bot structure
echo "🧪 Testing bot structure..."
python3 test_simple.py

if [ $? -eq 0 ]; then
    echo "✅ Bot structure test passed"
else
    echo "❌ Bot structure test failed"
    exit 1
fi

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📋 Next Steps:"
echo "1. Configure your .env file with real values"
echo "2. Set up PostgreSQL and Redis"
echo "3. Start the bot: python3 main.py"
echo "4. Test with real Avantis SDK integration"
echo ""
echo "🚀 Your Vanta Bot is ready!"
