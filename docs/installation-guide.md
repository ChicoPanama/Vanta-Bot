# Avantis SDK Integration - Installation Guide

## Quick Start

Follow these steps to get the Avantis Trader SDK integration up and running:

### 1. Install Dependencies

```bash
# Install the new dependencies
pip install -r requirements.txt
```

The integration adds these new dependencies:
- `avantis-trader-sdk>=0.8.4` - Official Avantis Trader SDK
- `websockets>=12.0` - WebSocket support for price feeds

### 2. Configure Environment

Copy the example environment file and configure it:

```bash
cp env.example .env
```

Edit `.env` and add your configuration:

```bash
# Required: Base Network Configuration
BASE_RPC_URL=https://mainnet.base.org
BASE_CHAIN_ID=8453
USDC_CONTRACT=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913

# Required: Trader Signer (choose ONE)
TRADER_PRIVATE_KEY=0x...  # Your private key (hex, no quotes)
# OR
AWS_KMS_KEY_ID=your-kms-key-id
AWS_REGION=us-east-1

# Optional: Price Feed
PYTH_WS_URL=wss://your-ws-endpoint  # Leave blank to skip feeds
```

### 3. Test the Integration

Run the sanity check script to verify everything is working:

```bash
python scripts/check_avantis_sdk.py
```

This will test:
- ✅ SDK connection to Base network
- ✅ Signer configuration
- ✅ Pairs cache functionality
- ✅ Trade parameters and fees
- ✅ Asset parameters and spreads
- ✅ Trader operations

### 4. Start the Bot

```bash
python main.py
```

### 5. Test Trading Commands

In your Telegram bot, try these commands:

```
/a_pairs          # List available trading pairs
/a_price ETH/USD  # Get ETH/USD price information
/a_info           # Get your trader information
```

## New Trading Commands

The integration adds these new commands to your bot:

| Command | Description | Example |
|---------|-------------|---------|
| `/a_price <PAIR>` | Get price information | `/a_price ETH/USD` |
| `/a_open <PAIR> <side> <collateral> <leverage> [tp] [sl]` | Open a position | `/a_open ETH/USD long 25 20 4000 0` |
| `/a_trades` | List open trades | `/a_trades` |
| `/a_close <pair_index> <trade_index> [fraction]` | Close a position | `/a_close 1 0 1.0` |
| `/a_pairs` | List available pairs | `/a_pairs` |
| `/a_info` | Get trader information | `/a_info` |

## File Structure

The integration adds these new files:

```
src/
├── integrations/
│   └── avantis/
│       ├── __init__.py
│       ├── sdk_client.py      # SDK client wrapper
│       └── feed_client.py     # Real-time price feeds
├── services/
│   ├── markets/
│   │   └── avantis_price_provider.py  # Price and parameter utilities
│   └── trading/
│       ├── __init__.py
│       ├── avantis_executor.py        # Trade execution
│       └── avantis_positions.py       # Position management
└── bot/
    └── handlers/
        └── avantis_trade_handlers.py  # Telegram commands

scripts/
└── check_avantis_sdk.py               # Sanity check script

tests/
└── test_avantis_sdk.py                # Unit tests

AVANTIS_SDK_INTEGRATION.md             # Complete documentation
```

## Configuration Details

### Trader Signer Options

**Option 1: Private Key**
```bash
TRADER_PRIVATE_KEY=0x1234567890abcdef...  # Your private key
```

**Option 2: AWS KMS**
```bash
AWS_KMS_KEY_ID=your-kms-key-id
AWS_REGION=us-east-1
```

### Price Feed Configuration

For real-time price feeds, configure a Pyth WebSocket endpoint:

```bash
PYTH_WS_URL=wss://your-pyth-endpoint
```

Leave blank to skip price feeds (trading will still work).

### USDC Configuration

The integration uses Base native USDC:
- **Contract**: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- **Decimals**: 6
- **Network**: Base Mainnet

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError: No module named 'avantis_trader_sdk'**
   ```bash
   pip install avantis-trader-sdk>=0.8.4
   ```

2. **SDK connection failed**
   - Check `BASE_RPC_URL` is correct
   - Verify network connectivity

3. **No trader address available**
   - Configure `TRADER_PRIVATE_KEY` or AWS KMS
   - Verify private key format (hex, no 0x prefix)

4. **USDC allowance issues**
   - Ensure sufficient USDC balance
   - Check allowance approval transactions

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python main.py
```

### Testing

Run the unit tests:

```bash
pytest tests/test_avantis_sdk.py -v
```

## Security Notes

- Never commit private keys to version control
- Use environment variables for sensitive data
- Prefer AWS KMS for production deployments
- Ensure secure RPC endpoint connections

## Support

- **Avantis Protocol**: [Avantis Documentation](https://docs.avantisfi.com)
- **SDK Integration**: Review `AVANTIS_SDK_INTEGRATION.md`
- **Bot Issues**: Check bot logs and error messages

## Next Steps

After successful installation:

1. Test the sanity check script
2. Try the basic trading commands
3. Review the complete documentation in `AVANTIS_SDK_INTEGRATION.md`
4. Set up price feeds if desired
5. Configure your trading parameters

The integration is now ready for use! 🚀
