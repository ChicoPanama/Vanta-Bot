# Avantis Trader SDK Integration

This document describes the complete integration of the Avantis Trader SDK into the Vanta-Bot project.

## Overview

The integration adds comprehensive Avantis Protocol trading capabilities to the existing Telegram bot, including:

- Real-time price feeds and market data
- Trade execution (market and limit orders)
- Position management and portfolio tracking
- Risk management and loss protection
- USDC allowance management
- Comprehensive trading parameters and analytics

## Architecture

### Core Components

1. **SDK Client Wrapper** (`src/integrations/avantis/sdk_client.py`)
   - Factory pattern for TraderClient initialization
   - Signer management (private key or AWS KMS)
   - USDC allowance handling
   - Web3 integration utilities

2. **Feed Client** (`src/integrations/avantis/feed_client.py`)
   - Real-time price feed integration
   - WebSocket connection management
   - Automatic reconnection with exponential backoff
   - Price update callbacks

3. **Price Provider** (`src/services/markets/avantis_price_provider.py`)
   - Trading parameter calculations
   - Fee estimation and loss protection
   - Spread and impact analysis
   - Trade quoting functionality

4. **Trade Executor** (`src/services/trading/avantis_executor.py`)
   - Order execution (market/limit)
   - Transaction building and broadcasting
   - Gas estimation
   - Trade result handling

5. **Position Manager** (`src/services/trading/avantis_positions.py`)
   - Position tracking and analysis
   - Portfolio management
   - Position closing (full/partial)
   - PnL calculations

6. **Telegram Handlers** (`src/bot/handlers/avantis_trade_handlers.py`)
   - `/a_price` - Get price information
   - `/a_open` - Open new positions
   - `/a_trades` - List open trades
   - `/a_close` - Close positions
   - `/a_pairs` - List available pairs
   - `/a_info` - Trader information

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Base Network Configuration
BASE_RPC_URL=https://mainnet.base.org
BASE_CHAIN_ID=8453
USDC_CONTRACT=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913

# Trader Signer (choose ONE)
TRADER_PRIVATE_KEY=0x...  # Your private key (hex, no quotes)
# OR
AWS_KMS_KEY_ID=your-kms-key-id
AWS_REGION=us-east-1

# Optional Price Feed
PYTH_WS_URL=wss://your-ws-endpoint  # Leave blank to skip feeds
```

### Dependencies

The integration adds these dependencies to `requirements.txt`:

```
avantis-trader-sdk>=0.8.4
websockets>=12.0
```

## Usage

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Sanity Check

```bash
python scripts/check_avantis_sdk.py
```

This script verifies:
- SDK connection to Base network
- Signer configuration
- Pairs cache functionality
- Trade parameters and fees
- Asset parameters and spreads
- Trader operations (if signer configured)

### 3. Start the Bot

```bash
python main.py
```

### 4. Use Trading Commands

#### Get Price Information
```
/a_price ETH/USD
```

#### Open a Position
```
/a_open ETH/USD long 25 20 4000 0
```
- `ETH/USD` - Trading pair
- `long` - Position side (long/short)
- `25` - Collateral in USDC
- `20` - Leverage multiplier
- `4000` - Take profit price (optional)
- `0` - Stop loss price (optional)

#### List Open Trades
```
/a_trades
```

#### Close a Position
```
/a_close 1 0 1.0
```
- `1` - Pair index
- `0` - Trade index
- `1.0` - Fraction to close (1.0 = full close)

#### List Available Pairs
```
/a_pairs
```

#### Get Trader Information
```
/a_info
```

## Features

### Trading Operations

- **Market Orders**: Execute trades at current market prices
- **Limit Orders**: Place orders at specific price levels (planned)
- **Position Management**: Open, close, and monitor positions
- **Risk Management**: Built-in loss protection and position sizing

### Price Feeds

- **Real-time Updates**: Live price feeds via WebSocket
- **Market Data**: Bid/ask spreads, price impact, skew analysis
- **Parameter Calculation**: Dynamic fee and protection calculations

### Safety Features

- **USDC Allowance Management**: Automatic allowance checking and approval
- **Input Validation**: Comprehensive parameter validation
- **Error Handling**: Robust error handling and user feedback
- **Dry Run Support**: Safe testing without real transactions

### Analytics

- **Portfolio Tracking**: Real-time PnL and position monitoring
- **Trade History**: Complete trade execution history
- **Performance Metrics**: Portfolio performance analysis
- **Risk Metrics**: Position risk and exposure analysis

## Development

### Testing

Run the unit tests:

```bash
pytest tests/test_avantis_sdk.py -v
```

### Adding New Features

1. **New Trading Commands**: Add handlers to `avantis_trade_handlers.py`
2. **New Price Providers**: Extend `avantis_price_provider.py`
3. **New Position Operations**: Add methods to `avantis_positions.py`
4. **New Execution Types**: Extend `avantis_executor.py`

### Code Structure

```
src/
├── integrations/
│   └── avantis/
│       ├── sdk_client.py      # SDK client wrapper
│       └── feed_client.py     # Real-time price feeds
├── services/
│   ├── markets/
│   │   └── avantis_price_provider.py  # Price and parameter utilities
│   └── trading/
│       ├── avantis_executor.py        # Trade execution
│       └── avantis_positions.py       # Position management
└── bot/
    └── handlers/
        └── avantis_trade_handlers.py  # Telegram commands
```

## Troubleshooting

### Common Issues

1. **SDK Connection Failed**
   - Check `BASE_RPC_URL` is correct
   - Verify network connectivity
   - Ensure Base network is accessible

2. **Signer Not Configured**
   - Set `TRADER_PRIVATE_KEY` or AWS KMS credentials
   - Verify private key format (hex, no 0x prefix)
   - Check AWS credentials if using KMS

3. **USDC Allowance Issues**
   - Ensure sufficient USDC balance
   - Check allowance approval transactions
   - Verify USDC contract address

4. **Price Feed Not Working**
   - Check `PYTH_WS_URL` configuration
   - Verify WebSocket endpoint accessibility
   - Review feed client logs

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python main.py
```

### Support

For issues related to:
- **Avantis Protocol**: Check [Avantis Documentation](https://docs.avantisfi.com)
- **SDK Integration**: Review this documentation
- **Bot Functionality**: Check bot logs and error messages

## Security Considerations

1. **Private Key Storage**: Never commit private keys to version control
2. **Environment Variables**: Use secure environment variable management
3. **AWS KMS**: Prefer AWS KMS for production deployments
4. **Network Security**: Ensure secure RPC endpoint connections
5. **Input Validation**: All user inputs are validated before processing

## Performance

- **Caching**: Price data and parameters are cached for performance
- **Async Operations**: All SDK operations are asynchronous
- **Connection Pooling**: Web3 connections are pooled and reused
- **Rate Limiting**: Built-in rate limiting for API calls

## Future Enhancements

- [ ] Limit order support
- [ ] Advanced order types (stop-loss, take-profit)
- [ ] Portfolio rebalancing
- [ ] Copy trading integration
- [ ] Advanced analytics and reporting
- [ ] Multi-signature wallet support
- [ ] Gas optimization strategies

## License

This integration follows the same license as the main Vanta-Bot project.
