# Vanta Bot Enterprise Deployment Guide

This guide covers the complete enterprise deployment of Vanta Bot with all security, monitoring, and production-ready features.

## 🚀 Quick Start

```bash
# 1. Clone and setup
git clone <repository>
cd avantis-telegram-bot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp env.example .env
# Edit .env with your configuration

# 4. Run enterprise deployment
python scripts/deploy_enterprise.py
```

## 🔧 Configuration

### Required Environment Variables

```bash
# Core Configuration
TELEGRAM_BOT_TOKEN=your_bot_token
DATABASE_URL=postgresql://user:pass@localhost/vanta_bot
REDIS_URL=redis://localhost:6379/0
BASE_RPC_URL=https://mainnet.base.org

# Security (Choose one)
# Option 1: AWS KMS (Production)
AWS_KMS_KEY_ID=arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012
AWS_REGION=us-east-1

# Option 2: Local Key Vault (Development)
LOCAL_WRAP_KEY_B64=your_base64_encoded_key

# Feature Flags
KEY_ENVELOPE_ENABLED=true
TX_PIPELINE_V2=true
AVANTIS_V2=true
STRICT_HANDLERS_ENABLED=true
STRUCTURED_LOGS_ENABLED=true

# Monitoring
ENABLE_METRICS=true
HEALTH_PORT=8080
LOG_LEVEL=INFO
LOG_JSON=true
```

### Optional Configuration

```bash
# Avantis Integration
AVANTIS_TRADING_CONTRACT=0x...
AVANTIS_VAULT_CONTRACT=0x...
USDC_CONTRACT=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913

# Admin Users
ADMIN_USER_IDS=123456789,987654321
SUPER_ADMIN_IDS=123456789

# Rate Limiting
COPY_EXECUTION_RATE_LIMIT=10
TELEGRAM_MESSAGE_RATE_LIMIT=30

# Trading Limits
MAX_LEVERAGE=500
MAX_POSITION_SIZE=100000
MIN_POSITION_SIZE=1
DEFAULT_SLIPPAGE_PCT=1.0
```

## 🏗️ Architecture Overview

### Security Layer
- **Envelope Encryption**: Per-wallet DEKs protected by KMS
- **Key Rotation**: Automated key rotation with zero downtime
- **Access Control**: Role-based permissions for admin functions

### Transaction Pipeline
- **Nonce Management**: Redis-based nonce reservation
- **Gas Optimization**: EIP-1559 with surge protection
- **Idempotency**: Request ID-based duplicate prevention
- **Retry Logic**: Exponential backoff with jitter

### Monitoring & Observability
- **Health Checks**: `/live`, `/ready`, `/health` endpoints
- **Metrics**: Prometheus-compatible metrics
- **Logging**: Structured JSON logging with redaction
- **Circuit Breakers**: Automatic failure protection

### Risk Management
- **Position Validation**: Comprehensive risk calculations
- **Oracle Aggregation**: Multi-source price feeds
- **Slippage Protection**: Configurable slippage bounds
- **Liquidation Monitoring**: Real-time risk assessment

## 📊 Monitoring

### Health Endpoints

```bash
# Liveness probe
curl http://localhost:8080/live

# Readiness probe
curl http://localhost:8080/ready

# Comprehensive health
curl http://localhost:8080/health

# Metrics
curl http://localhost:8080/metrics
```

### Key Metrics

- `tx_send_total`: Transaction send count by status
- `tx_confirmation_seconds`: Transaction confirmation time
- `wallet_decrypt_errors_total`: Wallet decryption errors
- `oracle_price_requests_total`: Oracle price requests
- `bot_commands_total`: Bot command usage
- `circuit_breaker_state`: Circuit breaker status

### Alerts

```yaml
# Example Prometheus alerts
- alert: WalletDecryptErrors
  expr: wallet_decrypt_errors_total > 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Wallet decryption errors detected"

- alert: CircuitBreakerOpen
  expr: circuit_breaker_state == 1
  for: 30s
  labels:
    severity: warning
  annotations:
    summary: "Circuit breaker is open"
```

## 🔐 Security Features

### Envelope Encryption

```python
# Production: AWS KMS
from src.security.key_vault import AwsKmsKeyVault
key_vault = AwsKmsKeyVault(kms_key_id="arn:aws:kms:...", kms_client=boto3.client("kms"))

# Development: Local Fernet
from src.security.key_vault import LocalFernetKeyVault
key_vault = LocalFernetKeyVault(wrapping_key_b64="your_key")
```

### Key Rotation

```bash
# Rotate keys (zero downtime)
python -m src.cli.rotate_keys
```

### Access Control

```python
# Check permissions
from src.bot.middleware.authz import authz_middleware

if authz_middleware.can_execute_command(user_id, "admin"):
    # Execute admin command
    pass
```

## 🚦 Rate Limiting

### Command Rate Limits

- **Trade**: 5 commands per 10 seconds
- **Status**: 20 commands per 10 seconds
- **Help**: 10 commands per 10 seconds
- **Default**: 10 commands per 10 seconds

### Configuration

```python
# Custom rate limits
from src.bot.middleware.rate_limit import CommandRateLimiter

rate_limiter = CommandRateLimiter(redis_client)
rate_limiter.limiters['custom'] = RateLimiter(capacity=5, refill_per_sec=0.5)
```

## 🗄️ Database Schema

### New Tables

- `wallets`: Envelope encryption support
- `sent_transactions`: Idempotency tracking
- Precision columns for financial data

### Migrations

```bash
# Run migrations
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

## 🔄 Deployment Strategies

### Blue-Green Deployment

1. **Deploy Green**: New version with flags OFF
2. **Run Migrations**: Additive database changes
3. **Enable Features**: Gradual feature flag activation
4. **Traffic Shift**: 10% → 50% → 100%
5. **Monitor**: Watch metrics and logs
6. **Decommission Blue**: After 24-48h clean metrics

### Feature Flags

```bash
# Enable envelope encryption
export KEY_ENVELOPE_ENABLED=true

# Enable new transaction pipeline
export TX_PIPELINE_V2=true

# Enable Avantis v2 integration
export AVANTIS_V2=true

# Enable strict handlers
export STRICT_HANDLERS_ENABLED=true
```

## 🧪 Testing

### Unit Tests

```bash
# Run all tests
pytest

# Run specific test suites
pytest tests/security/
pytest tests/blockchain/
pytest tests/risk/
```

### Integration Tests

```bash
# Test with local blockchain
pytest tests/integration/ -v

# Test with real RPC (use with caution)
pytest tests/integration/ --rpc-url=https://mainnet.base.org
```

### Security Tests

```bash
# Test key vault
pytest tests/security/test_key_vault.py -v

# Test encryption roundtrips
pytest tests/security/ -k "encrypt" -v
```

## 🚨 Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```bash
   # Check Redis status
   redis-cli ping
   
   # Check connection string
   echo $REDIS_URL
   ```

2. **Database Migration Failed**
   ```bash
   # Check database connectivity
   psql $DATABASE_URL -c "SELECT 1"
   
   # Check migration status
   alembic current
   ```

3. **Key Vault Errors**
   ```bash
   # Check AWS credentials
   aws sts get-caller-identity
   
   # Check KMS key
   aws kms describe-key --key-id $AWS_KMS_KEY_ID
   ```

4. **Circuit Breaker Open**
   ```bash
   # Check circuit breaker status
   curl http://localhost:8080/health | jq '.circuit_breakers'
   
   # Reset circuit breakers
   curl -X POST http://localhost:8080/admin/reset-breakers
   ```

### Logs

```bash
# View structured logs
tail -f logs/app.log | jq

# Filter by level
tail -f logs/app.log | jq 'select(.level == "ERROR")'

# Filter by component
tail -f logs/app.log | jq 'select(.logger | contains("blockchain"))'
```

## 📈 Performance Tuning

### Database Optimization

```sql
-- Add indexes for hot queries
CREATE INDEX CONCURRENTLY idx_positions_user_status ON positions(user_id, status);
CREATE INDEX CONCURRENTLY idx_fills_address_ts ON fills(address, ts);

-- Analyze tables
ANALYZE positions;
ANALYZE fills;
```

### Redis Optimization

```bash
# Configure Redis for high throughput
redis-cli CONFIG SET maxmemory 2gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
redis-cli CONFIG SET save "900 1 300 10 60 10000"
```

### Application Tuning

```python
# Optimize connection pools
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 30
REDIS_POOL_SIZE = 10
```

## 🔒 Security Checklist

- [ ] Envelope encryption enabled
- [ ] KMS key configured
- [ ] Admin users configured
- [ ] Rate limiting enabled
- [ ] Circuit breakers configured
- [ ] Logging redaction enabled
- [ ] Health checks configured
- [ ] Monitoring alerts set up
- [ ] Database migrations applied
- [ ] Feature flags configured

## 📞 Support

For enterprise support and custom deployments, contact the development team.

### Emergency Contacts

- **Security Issues**: security@company.com
- **Production Issues**: ops@company.com
- **Development**: dev@company.com

### Documentation

- [Architecture Overview](docs/architecture.md)
- [API Reference](docs/api.md)
- [Security Guide](docs/security.md)
- [Monitoring Guide](docs/monitoring.md)
