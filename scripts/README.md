# 🔧 Scripts

This directory contains utility scripts for the Vanta Bot.

## 📋 Script Files

### Deployment Scripts
- **[deploy.sh](deploy.sh)** - Automated deployment script
- **[setup.py](setup.py)** - Project setup and installation script

### Utility Scripts
- **[generate_key.py](generate_key.py)** - Generate encryption keys

## 🚀 Script Usage

### 1. Deployment Script

The `deploy.sh` script automates the deployment process:

```bash
# Make executable
chmod +x scripts/deploy.sh

# Run deployment
./scripts/deploy.sh
```

**What it does:**
- Checks for `.env` file
- Validates Python version
- Installs dependencies
- Runs basic tests
- Provides deployment instructions

### 2. Setup Script

The `setup.py` script handles project setup:

```bash
# Run setup
python scripts/setup.py
```

**What it does:**
- Creates necessary directories
- Generates encryption keys
- Sets up environment files
- Validates configuration
- Tests basic functionality

### 3. Key Generation

The `generate_key.py` script generates secure encryption keys:

```bash
# Generate new encryption key
python scripts/generate_key.py
```

**What it does:**
- Generates 32-byte encryption key
- Outputs key in base64 format
- Provides security recommendations

## 🔧 Script Configuration

### Environment Variables

Scripts use the same environment variables as the main bot:
```env
TELEGRAM_BOT_TOKEN=your_bot_token
BASE_RPC_URL=your_rpc_url
DATABASE_URL=your_database_url
REDIS_URL=your_redis_url
```

### Script Permissions

Ensure scripts are executable:
```bash
chmod +x scripts/*.sh
```

## 📊 Script Output

### Deployment Script Output
```
🚀 Deploying Vanta Bot...
==================================
✅ .env file found
✅ Python version 3.11 is compatible
📦 Installing dependencies...
✅ Dependencies installed successfully
🧪 Testing bot structure...
✅ Bot structure test passed

🎉 Deployment completed successfully!

📋 Next Steps:
1. Configure your .env file with real values
2. Set up PostgreSQL and Redis
3. Start the bot: python3 main.py
4. Test with real Avantis SDK integration

🚀 Your Vanta Bot is ready!
```

### Setup Script Output
```
🚀 Vanta Bot Setup
============================
✅ Creating directories...
✅ Generating encryption key...
✅ Setting up environment...
✅ Validating configuration...
✅ Testing basic functionality...

🎉 Setup completed successfully!
```

### Key Generation Output
```
🔐 Encryption Key Generator
===========================
Generated 32-byte encryption key:
fKs1CbDZigeFo7K-IcIAgJKPHgHZM8n3O2Nz9sGXCWA

📋 Security Recommendations:
- Store this key securely
- Never commit to version control
- Use environment variables
- Rotate keys regularly
```

## 🛠️ Customizing Scripts

### Adding New Scripts

1. Create new script file
2. Add appropriate shebang
3. Include error handling
4. Add usage documentation
5. Update this README

### Script Template

```bash
#!/bin/bash

echo "🚀 Script Name"
echo "=============="

# Check prerequisites
if [ ! -f ".env" ]; then
    echo "❌ .env file not found"
    exit 1
fi

# Main script logic
echo "✅ Performing action..."

# Success message
echo "🎉 Script completed successfully!"
```

## 🚨 Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   chmod +x scripts/deploy.sh
   ```

2. **Python Not Found**
   ```bash
   # Use python3 explicitly
   python3 scripts/setup.py
   ```

3. **Missing Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Script Debugging

Enable verbose output:
```bash
bash -x scripts/deploy.sh
```

Check script syntax:
```bash
bash -n scripts/deploy.sh
```

## 📝 Script Maintenance

### Regular Updates
- Update scripts when adding new features
- Test scripts in different environments
- Keep scripts simple and focused
- Document any changes

### Best Practices
- Use clear error messages
- Check prerequisites
- Provide helpful output
- Handle edge cases
- Keep scripts portable

## 🔄 Integration

### CI/CD Integration
Scripts are designed to work in CI/CD pipelines:
- No interactive prompts
- Clear exit codes
- Comprehensive logging
- Error handling

### Docker Integration
Scripts work with Docker containers:
- Environment variable support
- Volume mounting compatibility
- Container-friendly paths
- Minimal dependencies
