# GitHub Actions Workflow Configuration

## Required Secrets

For integration tests to run, the following secrets must be configured in your GitHub repository settings:

### Repository Secrets Setup

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add:

#### `BASE_RPC_URL`
- **Value**: `https://mainnet.base.org`
- **Description**: Base mainnet RPC endpoint for integration tests

#### `TRADER_PRIVATE_KEY`
- **Value**: Your test wallet private key (for integration tests only)
- **Description**: Private key for the test wallet used in integration tests

### Workflow Behavior

- **With Secrets**: Integration tests will run automatically on pull requests
- **Without Secrets**: Integration tests will be skipped with a clear message

### Security Note

⚠️ **Important**: Only use test wallets with minimal funds for the `TRADER_PRIVATE_KEY` secret. Never use production wallets or main trading accounts.

### Environment Variables

The workflow automatically sets these environment variables for integration tests:
- `BASE_RPC_URL`: RPC endpoint
- `TRADER_PRIVATE_KEY`: Test wallet private key
- `BASE_CHAIN_ID`: "8453" (Base mainnet)
- `AVANTIS_TRADING_CONTRACT`: "0x44914408af82bC9983bbb330e3578E1105e11d4e" (Active proxy)

### Testing the Workflow

To test the workflow locally without secrets:

```bash
# Run unit tests only
pytest tests/unit -v

# Run integration tests (requires environment variables)
BASE_RPC_URL=https://mainnet.base.org \
TRADER_PRIVATE_KEY=your_test_private_key \
BASE_CHAIN_ID=8453 \
AVANTIS_TRADING_CONTRACT=0x44914408af82bC9983bbb330e3578E1105e11d4e \
pytest -m integration -v
```
