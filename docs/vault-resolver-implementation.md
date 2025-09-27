# Avantis Vault Resolver Implementation

## Overview

This document describes the implementation of the Avantis vault contract resolver, which attempts to dynamically resolve the USDC Vault contract address from the Trading Proxy contract on Base network.

## Implementation Details

### 1. Contract Registry Service

**File**: `src/services/contracts/avantis_registry.py`

The `AvantisRegistry` class provides:
- Dynamic vault address resolution from Trading Proxy
- Multiple candidate function selectors
- Graceful fallback when vault cannot be resolved
- Contract information retrieval for debugging

### 2. Configuration Updates

**Files**: 
- `env.example` - Updated with confirmed Trading contract address
- `src/config/settings.py` - Made vault contract optional in validation

### 3. Bot Integration

**File**: `main.py`
- Vault resolution during startup
- Non-blocking operation (bot continues without vault)
- Environment variable setting for resolved address

### 4. Debug Command

**File**: `src/bot/handlers/alfa_handlers.py`
- Added `/alfa debug:contracts` command
- Displays resolved contract addresses and status

## Current Status

### ✅ Confirmed
- **Trading Contract**: `0x5FF292d70bA9cD9e7CCb313782811b3D7120535f`
- **Network**: Base Mainnet (Chain ID: 8453)
- **Label**: "Avantis: Trading Proxy" on BaseScan

### ⚠️ Vault Resolution
- **Status**: Cannot be resolved from Trading Proxy
- **Reason**: Trading contract does not expose vault getter functions
- **Impact**: Bot continues to function without vault contract
- **Trading Features**: Fully operational (all events come from Trading contract)

## Function Selectors Tested

The resolver attempts the following function selectors in order:
1. `vault()`
2. `getVault()`
3. `usdcVault()`
4. `USDC_VAULT()`
5. `getUSDCVault()`
6. `vaultAddress()`
7. `getVaultAddress()`
8. `collateralVault()`
9. `getCollateralVault()`
10. `treasury()`
11. `getTreasury()`
12. `usdc()`
13. `USDC()`
14. `collateral()`
15. `getCollateral()`

## Usage

### Environment Configuration
```env
AVANTIS_TRADING_CONTRACT=0x5FF292d70bA9cD9e7CCb313782811b3D7120535f
# AVANTIS_VAULT_CONTRACT will be resolved at runtime
```

### Debug Command
```
/alfa debug:contracts
```

### Test Script
```bash
python3 scripts/test_vault_resolver.py
```

## Future Considerations

1. **Manual Vault Address**: If the vault address becomes available through other means, it can be set manually using `registry.set_vault_address(address)`

2. **Registry Contract**: Future versions of Avantis might introduce a registry contract that exposes the vault address

3. **Documentation Updates**: Monitor Avantis documentation for official vault address publication

## Safety & Compatibility

- **Non-blocking**: Bot startup is not affected by vault resolution failure
- **Trading Features**: All trading functionality works with just the Trading contract
- **Future-proof**: Resolver can be easily updated when vault address becomes available
- **Debugging**: Built-in debug command for monitoring contract status

## Files Modified

1. `env.example` - Updated Trading contract address
2. `src/config/settings.py` - Made vault contract optional
3. `src/services/contracts/avantis_registry.py` - New vault resolver service
4. `src/bot/handlers/alfa_handlers.py` - Added debug command
5. `main.py` - Integrated vault resolution into startup
6. `scripts/test_vault_resolver.py` - Test script for verification

## Conclusion

The vault resolver implementation provides a robust, future-proof solution for dynamically resolving the Avantis vault contract address. While the current Trading contract does not expose the vault address, the implementation gracefully handles this scenario and allows the bot to continue operating with full trading functionality.
