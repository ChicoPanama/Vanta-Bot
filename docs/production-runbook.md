# Production Runbook - Vanta-Bot (Phase 9)

## Overview
This runbook provides step-by-step procedures for deploying, operating, and troubleshooting the Vanta-Bot in production.

---

## 📋 Pre-Deployment Checklist

### Infrastructure
- [ ] PostgreSQL database provisioned and accessible
- [ ] Redis cluster provisioned and accessible
- [ ] Base RPC endpoint configured and tested
- [ ] AWS KMS (if using) configured and accessible
- [ ] Health monitoring endpoints accessible
- [ ] Log aggregation system configured

### Configuration
- [ ] All environment variables set (see `.env.example`)
- [ ] Telegram bot token configured
- [ ] Trader wallet configured (private key or KMS)
- [ ] Admin user IDs configured
- [ ] Oracle feed addresses verified (Chainlink/Pyth)
- [ ] Contract addresses verified on Base network

### Security
- [ ] Private keys stored securely (never in code/logs)
- [ ] KMS access roles configured (if using)
- [ ] API secrets rotated and stored in secret manager
- [ ] Rate limiting configured
- [ ] Admin permissions verified
- [ ] Emergency stop procedures tested

### Testing
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Smoke tests passing on staging
- [ ] Chaos tests reviewed
- [ ] Manual end-to-end test completed on testnet

---

## 🚀 Deployment Procedure

### Step 1: Database Migration
```bash
# Backup existing database
python ops/backup.sh

# Run migrations
python ops/migrate.py

# Verify migration
psql $DATABASE_URL -c "SELECT version_num FROM alembic_version;"
```

### Step 2: Seed Initial Data (Optional)
```bash
# Only for new deployments
python scripts/seed_database.py
```

### Step 3: Deploy Services

#### Using Docker Compose
```bash
# Build images
make docker-build

# Start all services in DRY mode
export COPY_EXECUTION_MODE=DRY
make docker-up

# Check logs
make docker-logs
```

#### Manual Deployment
```bash
# Terminal 1: Bot
python -m src.bot.application

# Terminal 2: Webhook API
uvicorn src.api.webhook:app --host 0.0.0.0 --port 8080

# Terminal 3: Signal Worker
python -m src.workers.signal_worker

# Terminal 4: TP/SL Executor
python -m src.services.executors.tpsl_executor

# Terminal 5: Avantis Indexer
python -m src.services.indexers.avantis_indexer
```

### Step 4: Health Verification
```bash
# Check basic health
curl http://localhost:8080/healthz

# Check detailed health
curl http://localhost:8080/health | jq

# Check readiness
curl http://localhost:8080/readyz

# Verify all components are "healthy"
```

### Step 5: Monitoring Setup
- [ ] Configure Prometheus scraping
- [ ] Set up Grafana dashboards
- [ ] Configure alerting rules
- [ ] Test alert routing

### Step 6: Switch to LIVE Mode (After Validation)
```bash
# Via environment variable (restart required)
export COPY_EXECUTION_MODE=LIVE

# Or via Redis (no restart required)
redis-cli SET exec_mode '{"mode":"LIVE","emergency_stop":false}'
```

---

## 🔍 Monitoring & Observability

### Key Metrics to Monitor

1. **Health Endpoints**
   - `/healthz` - Basic liveness
   - `/readyz` - Full readiness
   - `/health` - Component details
   - `/metrics` - Prometheus metrics

2. **System Metrics**
   - CPU usage < 70%
   - Memory usage < 80%
   - Disk usage < 85%
   - Open file descriptors < 70% of limit

3. **Application Metrics**
   - Transaction success rate > 90%
   - Oracle price freshness < 30s
   - Redis connection status: UP
   - Database connection status: UP
   - Queue depth < 100

4. **Business Metrics**
   - Active positions count
   - Daily trade volume
   - Risk policy violations
   - Emergency stop activations

### Log Locations
```bash
# Application logs
tail -f logs/app.log

# Docker logs
docker compose logs -f --tail=100

# System logs
journalctl -u vanta-bot.service -f
```

---

## 🚨 Emergency Procedures

### Emergency Stop
```bash
# Method 1: Environment variable (fastest)
export EMERGENCY_STOP=true

# Method 2: Redis
redis-cli SET exec_mode '{"mode":"DRY","emergency_stop":true}'

# Method 3: Admin command via Telegram
/emergency_stop
```

### Roll Back Deployment
```bash
# Stop services
make docker-down

# Restore database backup
psql $DATABASE_URL < backups/YYYYMMDD_HHMMSS/backup.sql

# Deploy previous version
git checkout v<previous-version>
make docker-build
make docker-up
```

### Switch to DRY Mode
```bash
# Via Redis (immediate)
redis-cli SET exec_mode '{"mode":"DRY","emergency_stop":false}'

# Via environment (requires restart)
export COPY_EXECUTION_MODE=DRY
make docker-down
make docker-up
```

---

## 🐛 Troubleshooting

### Service Won't Start

**Symptom**: Service exits immediately after start

**Diagnosis**:
```bash
# Check logs
docker logs vanta-bot

# Check environment
env | grep -E "DATABASE_URL|REDIS_URL|BASE_RPC_URL"

# Test dependencies
python -c "import redis; print('Redis OK')"
python -c "from web3 import Web3; print('Web3 OK')"
```

**Solutions**:
1. Verify all required environment variables are set
2. Test database connectivity
3. Test Redis connectivity
4. Check RPC endpoint connectivity
5. Review logs for specific error messages

### Database Connection Errors

**Symptom**: `OperationalError` or connection timeout

**Diagnosis**:
```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1;"

# Check connection pool
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"
```

**Solutions**:
1. Verify DATABASE_URL is correct
2. Check firewall rules
3. Verify database is running
4. Check connection pool settings
5. Review database logs

### Redis Connection Errors

**Symptom**: `ConnectionError` or timeout

**Diagnosis**:
```bash
# Test connection
redis-cli -u $REDIS_URL ping

# Check info
redis-cli -u $REDIS_URL INFO
```

**Solutions**:
1. Verify REDIS_URL is correct
2. Check Redis is running
3. Verify network connectivity
4. Check Redis maxclients setting
5. Review Redis logs

### RPC Endpoint Issues

**Symptom**: Transaction failures or timeouts

**Diagnosis**:
```bash
# Test RPC
curl -X POST $BASE_RPC_URL \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# Check rate limits
tail -f logs/app.log | grep "rate limit"
```

**Solutions**:
1. Verify RPC endpoint is accessible
2. Check for rate limiting
3. Consider backup RPC endpoints
4. Monitor RPC provider status page
5. Increase timeout settings if needed

### Transaction Failures

**Symptom**: Trades failing with errors

**Diagnosis**:
```bash
# Check recent trades
psql $DATABASE_URL -c "SELECT * FROM trades ORDER BY created_at DESC LIMIT 10;"

# Check nonce issues
psql $DATABASE_URL -c "SELECT * FROM tx_intents WHERE status='FAILED' ORDER BY created_at DESC;"

# Check gas prices
python -c "from web3 import Web3; w3=Web3(Web3.HTTPProvider('$BASE_RPC_URL')); print(w3.eth.gas_price)"
```

**Solutions**:
1. Verify sufficient USDC balance
2. Check gas price settings
3. Verify contract addresses
4. Check for nonce conflicts
5. Review transaction logs

### Price Feed Issues

**Symptom**: Stale or missing prices

**Diagnosis**:
```bash
# Check price feeds
curl http://localhost:8080/health | jq '.components.price_feeds'

# Test Chainlink
python scripts/test_oracle_e2e.py

# Test Pyth
curl "https://hermes.pyth.network/v2/updates/price/latest?ids[]=0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43"
```

**Solutions**:
1. Verify feed addresses are correct
2. Check oracle provider status
3. Verify RPC connectivity
4. Review staleness thresholds
5. Consider fallback feeds

---

## 📊 Performance Tuning

### Database Optimization
```bash
# Run VACUUM
psql $DATABASE_URL -c "VACUUM ANALYZE;"

# Check slow queries
psql $DATABASE_URL -c "SELECT * FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10;"

# Add indexes if needed
psql $DATABASE_URL -c "CREATE INDEX idx_trades_user_created ON trades(tg_user_id, created_at);"
```

### Redis Optimization
```bash
# Check memory usage
redis-cli INFO memory

# Check slow commands
redis-cli SLOWLOG GET 10

# Tune maxmemory-policy
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### RPC Rate Limiting
```bash
# Monitor rate limit hits
grep "rate limit" logs/app.log | wc -l

# Adjust backoff strategy in code
# See src/blockchain/tx/sender.py
```

---

## 🔄 Routine Maintenance

### Daily
- [ ] Check service health
- [ ] Review error logs
- [ ] Monitor queue depth
- [ ] Verify backup completion

### Weekly
- [ ] Review performance metrics
- [ ] Check disk space
- [ ] Review slow queries
- [ ] Update dependencies (security patches)

### Monthly
- [ ] Database vacuum and analyze
- [ ] Rotate logs
- [ ] Review and update risk limits
- [ ] Test backup restoration
- [ ] Review alert rules

### Quarterly
- [ ] Full system audit
- [ ] Update runbook
- [ ] Disaster recovery drill
- [ ] Security review
- [ ] Performance baseline update

---

## 📞 Escalation

### Severity Levels

**P0 - Critical** (Response: Immediate)
- Complete service outage
- Data loss or corruption
- Security breach
- Emergency stop activated unexpectedly

**P1 - High** (Response: < 1 hour)
- Partial service degradation
- Transaction failures > 50%
- Database connection issues
- Price feed failures

**P2 - Medium** (Response: < 4 hours)
- Individual component failures
- Performance degradation
- Non-critical errors increasing
- Warning threshold breaches

**P3 - Low** (Response: Next business day)
- Minor bugs
- Documentation updates
- Feature requests
- Optimization opportunities

### Contact Information
- **On-Call Engineer**: [Configure alerting system]
- **Database Admin**: [Contact info]
- **Infrastructure Team**: [Contact info]
- **Security Team**: [Contact info]

---

## 📝 Change Management

### Before Making Changes
1. Review this runbook
2. Check current system status
3. Notify stakeholders
4. Prepare rollback plan
5. Schedule maintenance window (if needed)

### During Changes
1. Follow deployment procedure
2. Monitor health endpoints
3. Check logs continuously
4. Verify metrics remain healthy
5. Test critical user journeys

### After Changes
1. Verify all systems healthy
2. Monitor for 1 hour minimum
3. Document any issues
4. Update runbook if needed
5. Notify stakeholders of completion

---

## 🎯 Go/No-Go Checklist

Before switching to LIVE mode, verify all items:

### Infrastructure
- [ ] All services running and healthy
- [ ] Database connections stable
- [ ] Redis connections stable
- [ ] RPC endpoint responsive
- [ ] Health endpoints returning 200

### Configuration
- [ ] Environment variables verified
- [ ] Chainlink feeds validated
- [ ] Pyth feeds validated
- [ ] Contract addresses confirmed
- [ ] Admin users configured

### Monitoring
- [ ] Prometheus scraping metrics
- [ ] Grafana dashboards accessible
- [ ] Alerts configured and tested
- [ ] Log aggregation working
- [ ] On-call rotation configured

### Security
- [ ] Private keys secured
- [ ] Rate limiting active
- [ ] Admin permissions verified
- [ ] Emergency stop tested
- [ ] Security scan passed

### Testing
- [ ] DRY mode tested for 24h minimum
- [ ] All critical paths tested
- [ ] Risk limits verified
- [ ] Liquidation protection confirmed
- [ ] TP/SL orders working

### Team Readiness
- [ ] On-call engineer identified
- [ ] Runbook reviewed
- [ ] Emergency procedures tested
- [ ] Escalation path clear
- [ ] Rollback plan ready

---

**Last Updated**: Phase 9 Completion
**Version**: 1.0.0
**Maintainer**: DevOps Team
