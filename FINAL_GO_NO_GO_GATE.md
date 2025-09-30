# 🚦 FINAL GO/NO-GO GATE - v9.0.1-rc2

**Release:** v9.0.1-rc2  
**Target:** Production Deployment  
**Date:** September 30, 2025  
**Status:** ⚠️ **AWAITING VALIDATION**

---

## ⚡ EXECUTIVE SUMMARY

**Clear these gates → Ship. Fail any → No-Go.**

| Gate | Duration | Pass Criteria | Status |
|------|----------|---------------|--------|
| A) Staging DRY Burn-in | 24h | All 4 tests + 4 metrics pass | ⏳ Pending |
| B) Staging LIVE Canary | 2-4h | No dup sends, receipts OK | ⏳ Pending |
| C) Secrets & Hygiene | Once | Key rotated, CI scan enabled | ⏳ Pending |

**If all pass → Proceed to Production flip plan**

---

## 🔬 GATE A: STAGING DRY — 24H BURN-IN

### Required Configuration

```bash
# .env.staging
ENVIRONMENT=production  # Critical: blocks mock prices
EXEC_MODE=DRY
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
BASE_RPC_URL=https://mainnet.base.org
SIGNER_BACKEND=kms  # Or "local" for dev
ALLOW_LIVE_AFTER_STREAK=3
```

---

### Test 1: Duplicate Intent (SEC-001)

**Command:**
```bash
# Fire same open twice within 1s
payload='{"source":"test","signal_id":"go-001","tg_user_id":999,"symbol":"BTC-USD","side":"LONG","collateral_usdc":10,"leverage_x":2,"slippage_pct":0.5}'
sig=$(echo -n "$payload" | openssl dgst -sha256 -hmac "$WEBHOOK_HMAC_SECRET" -r | cut -d' ' -f1)

# Send twice concurrently
curl -X POST http://staging:8090/signals -H "Content-Type: application/json" -H "X-Signature: $sig" -d "$payload" &
curl -X POST http://staging:8090/signals -H "Content-Type: application/json" -H "X-Signature: $sig" -d "$payload" &
wait
```

**Pass Criteria:**
- ✅ Database query returns **1** `tx_intent` row
  ```sql
  SELECT COUNT(*) FROM tx_intents WHERE intent_key IN (
    SELECT intent_key FROM tx_intents 
    WHERE intent_metadata::text LIKE '%go-001%'
  );
  -- Expected: 1
  ```
- ✅ Exactly **1** `tx_send` created (if execution reached that stage)
- ✅ Metric: `sum(increase(vanta_intent_duplicate_total[5m])) == 0`

**Result:** □ Pass / □ Fail  
**Notes:** _______________________________________________

---

### Test 2: Mock Price Guard (SEC-002)

**Command:**
```python
# Run in staging environment with ENVIRONMENT=production
from src.blockchain.avantis_client import AvantisClient
import os

os.environ["ENVIRONMENT"] = "production"  # Ensure it's set
client = AvantisClient(...)

try:
    prices = client.get_real_time_prices(["BTC", "ETH"])
    print("❌ FAIL: Mock prices returned!")
    exit(1)
except RuntimeError as e:
    if "Mock price method not available in production" in str(e):
        print("✅ PASS: Mock prices blocked!")
        exit(0)
    else:
        print(f"❌ FAIL: Wrong error: {e}")
        exit(1)
```

**Pass Criteria:**
- ✅ `get_real_time_prices()` raises **RuntimeError**
- ✅ Error message: "Mock price method not available in production"
- ✅ All production paths use `PriceAggregator` (code review)

**Result:** □ Pass / □ Fail  
**Notes:** _______________________________________________

---

### Test 3: Leverage Fallback Clamp (SEC-004)

**Setup:**
```sql
-- Create test user without explicit max_leverage in copy_configurations
INSERT INTO copy_configurations (copytrader_id, enabled) 
VALUES (9999, true) 
ON CONFLICT (copytrader_id) DO NOTHING;
-- Intentionally omit max_leverage column

-- Ensure user has a risk policy
INSERT INTO user_risk_policies (tg_user_id, max_leverage_x, max_position_size_usd)
VALUES (9999, 3, 5000)
ON CONFLICT (tg_user_id) DO UPDATE SET max_leverage_x = 3;
```

**Command:**
```bash
# Trigger copy trade for user 9999
# Observe logs for leverage decision
docker compose logs worker | grep -i "max leverage" | tail -5
```

**Pass Criteria:**
- ✅ Logs show fallback leverage: **5.0** (not 50.0)
- ✅ Final leverage clamped by user policy: **3.0** (from UserRiskPolicy)
- ✅ Position not rejected due to excessive leverage

**Result:** □ Pass / □ Fail  
**Notes:** _______________________________________________

---

### Test 4: Redis Outage → Circuit Breaker (BOT-201)

**Command:**
```bash
# 1. Verify starting state
curl -s http://staging:8090/health | jq '.execution_mode'
# Expected: {"mode":"DRY","redis_health_streak":3}

# 2. Pause Redis for 60s
docker compose pause redis
sleep 2

# 3. Generate traffic and check mode stays DRY
for i in {1..12}; do
  mode=$(curl -s http://staging:8090/health | jq -r '.execution_mode.mode')
  streak=$(curl -s http://staging:8090/health | jq -r '.execution_mode.redis_health_streak')
  echo "[$i] Mode: $mode, Streak: $streak"
  sleep 5
done
# Expected: All show mode="DRY", streak=0

# 4. Restore Redis
docker compose unpause redis
sleep 2

# 5. Monitor recovery (requires 3 consecutive healthy reads)
for i in {1..10}; do
  health=$(curl -s http://staging:8090/health | jq '.execution_mode')
  echo "[$i] $health"
  sleep 2
done
# Expected: streak increments 0→1→2→3, mode stays DRY (since we're in DRY config)
```

**Pass Criteria:**
- ✅ During outage: mode immediately becomes **DRY**
- ✅ During outage: `redis_health_streak` resets to **0**
- ✅ Logs show: "FAILING SAFE TO DRY MODE" or similar
- ✅ After restore: streak increments **0→1→2→3**
- ✅ If requesting LIVE: only allowed after streak ≥ **3**

**Result:** □ Pass / □ Fail  
**Notes:** _______________________________________________

---

### Metrics Watch (24h continuous)

**Query these every 5 minutes; all must stay within thresholds:**

```promql
# 1. Duplicates (CRITICAL: must be exactly 0)
sum(increase(vanta_intent_duplicate_total[5m]))
# Threshold: == 0

# 2. Illegal transitions (CRITICAL: must be exactly 0)
increase(vanta_intent_illegal_transition_total[10m])
# Threshold: == 0

# 3. Exec mode stability (allow some flapping during drills)
increase(vanta_exec_mode_changes_total[10m])
# Threshold: ≤ 2

# 4. Tx submit failure ratio
rate(vanta_tx_submissions_failed[5m]) / rate(vanta_tx_submissions_total[5m])
# Threshold: ≤ 0.005 (0.5%)
```

**Grafana Dashboard:**
```bash
# Create dashboard queries
curl -X POST http://grafana:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @ops/grafana-go-no-go-dashboard.json
```

**Result:** □ Pass (all 24h) / □ Fail  
**Failure Time:** _____________  
**Failed Metric:** _______________________________________________

---

### Database Integrity Checks (once, after 1h)

```sql
-- 1. Unique constraint present
SELECT 1 FROM pg_indexes 
WHERE indexname = 'uq_tx_intents_idem' 
  AND tablename = 'tx_intents';
-- Expected: 1 row

-- 2. Recent intents have deterministic keys (no UUIDs)
SELECT intent_key, created_at 
FROM tx_intents 
ORDER BY created_at DESC 
LIMIT 5;
-- Expected: Keys are SHA256 hashes (64 hex chars), NOT UUIDs

-- 3. No duplicate intent keys
SELECT intent_key, COUNT(*) as cnt
FROM tx_intents
GROUP BY intent_key
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- 4. All user policies have max_leverage set
SELECT tg_user_id, max_leverage_x 
FROM user_risk_policies 
WHERE max_leverage_x IS NULL OR max_leverage_x > 50;
-- Expected: 0 rows (or acceptable exceptions documented)
```

**Result:** □ Pass / □ Fail  
**Notes:** _______________________________________________

---

### Gate A Sign-Off

**Staging DRY 24h burn-in:** □ Pass / □ Fail  
**All 4 tests passed:** □ Yes / □ No  
**All 4 metrics within threshold:** □ Yes / □ No  
**DB integrity checks passed:** □ Yes / □ No  

**Approver:** _______________________  Date: __________

**If FAIL:** Document issues and remediation plan:
- Issue: _______________________________________________
- Remediation: _______________________________________________
- ETA: __________

---

## 🐤 GATE B: STAGING LIVE CANARY — 2-4H

### Required Configuration

```bash
# .env.staging.canary
ENVIRONMENT=production
EXEC_MODE=LIVE  # ⚠️ LIVE mode with strict caps

# CANARY SAFETY CAPS (critical!)
MAX_NOTIONAL_USDC=10
MAX_LEVERAGE=2
ALLOWED_SYMBOLS=BTC,ETH
CANARY_ENABLED=true

# Circuit breaker settings
ENABLE_RBF=true
ALLOW_LIVE_AFTER_STREAK=3

# Monitoring
LOG_LEVEL=INFO
METRICS_ENABLED=true
```

### Canary Execution

**Deploy:**
```bash
# 1. Create canary config
cp config/env.prod.canary.template .env.staging.canary

# 2. Update with staging values
nano .env.staging.canary

# 3. Deploy
docker compose --env-file .env.staging.canary up -d

# 4. Verify mode
curl -s http://staging:8090/health | jq '.execution_mode.mode'
# Expected: "LIVE"
```

**Test Trade:**
```bash
# Send small canary open
payload='{"source":"canary","signal_id":"canary-001","tg_user_id":999,"symbol":"BTC-USD","side":"LONG","collateral_usdc":8,"leverage_x":2,"slippage_pct":0.5}'
sig=$(echo -n "$payload" | openssl dgst -sha256 -hmac "$WEBHOOK_HMAC_SECRET" -r | cut -d' ' -f1)

curl -X POST http://staging:8090/signals \
  -H "Content-Type: application/json" \
  -H "X-Signature: $sig" \
  -d "$payload"
```

**Watch Transaction:**
```bash
# Monitor orchestrator
docker compose logs -f orchestrator | grep -i canary

# Check tx status
psql -c "SELECT status, tx_hash FROM tx_intents WHERE intent_metadata::text LIKE '%canary-001%';"
```

### Pass Criteria

**Transaction Flow:**
- ✅ Intent created with deterministic key
- ✅ Transaction built and sent to chain
- ✅ Receipt confirmed within 30s
- ✅ Status transitions: `CREATED → BUILDING → BUILT → SENDING → SENT → MINED → FINAL`
- ✅ No duplicate sends for same intent

**Safety Caps Enforced:**
```bash
# Test over-limit rejection
payload_overlimit='{"source":"canary","signal_id":"canary-002","tg_user_id":999,"symbol":"BTC-USD","side":"LONG","collateral_usdc":15,"leverage_x":3,"slippage_pct":0.5}'
# Expected: Rejected with clear error message

# Test invalid symbol rejection
payload_invalid='{"source":"canary","signal_id":"canary-003","tg_user_id":999,"symbol":"SOL-USD","side":"LONG","collateral_usdc":5,"leverage_x":2,"slippage_pct":0.5}'
# Expected: Rejected (SOL not in ALLOWED_SYMBOLS)
```

**RBF Behavior (if timeout occurs):**
- ✅ Timeout detected after N seconds
- ✅ RBF attempt increments fee by ~12-15%
- ✅ Attempts capped at configured limit (2-3)
- ✅ Metrics: `vanta_rbf_attempt_total` increments appropriately

**Metrics (2-4h continuous):**
- ✅ Same 4 metrics as Gate A (within thresholds)
- ✅ Additional: `rate(vanta_tx_mined_total[5m]) > 0` (trades executing)

### Gate B Sign-Off

**Staging LIVE canary 2-4h:** □ Pass / □ Fail  
**Receipts confirmed:** □ Yes / □ No  
**No duplicate sends:** □ Yes / □ No  
**Safety caps enforced:** □ Yes / □ No  
**Metrics within threshold:** □ Yes / □ No  

**Approver:** _______________________  Date: __________

---

## 🔐 GATE C: SECRETS & HYGIENE

### Private Key Management

**Exposed Key:** `aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87`

**Required Actions:**

1. **Verify key never used with real funds:**
   ```bash
   # Derive address from private key
   python3 << 'EOF'
   from eth_account import Account
   key = "0xaa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87"
   account = Account.from_key(key)
   print(f"Address: {account.address}")
   EOF
   
   # Check blockchain for transactions
   # Visit: https://basescan.org/address/0x...
   # If ANY transactions found with real funds → IMMEDIATE ROTATION
   ```
   **Result:** □ No transactions / □ Transactions found (ROTATE NOW!)  
   **Address:** _______________________________________________

2. **Rotate key (if needed):**
   ```bash
   # Generate new key
   openssl rand -hex 32
   
   # Store in AWS Secrets Manager
   aws secretsmanager create-secret \
     --name vanta-bot/trader-key \
     --secret-string "NEW_KEY_HERE"
   
   # Update all configs
   # .env.staging, .env.production
   ```
   **New Key Stored:** □ Yes / □ Not Needed  
   **Location:** _______________________________________________

3. **Purge from git history:**
   ```bash
   # Option 1: BFG Repo-Cleaner (recommended)
   brew install bfg
   bfg --replace-text <(echo "aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87==[REDACTED]") .git
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive
   
   # Option 2: git-filter-repo
   git filter-repo --replace-text <(echo "aa3645...1f87==[REDACTED]")
   
   # Force push (coordinate with team!)
   git push origin --force --all
   git push origin --force --tags
   ```
   **Purged:** □ Yes / □ No  
   **Method Used:** _______________________________________________

### CI Secret Scanning

**Add Pre-commit Hook:**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
```

**Install:**
```bash
pre-commit install
pre-commit run --all-files
```

**Add GitHub Actions:**
```yaml
# .github/workflows/security-scan.yml
name: Security Scan
on: [push, pull_request]

jobs:
  secrets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      - name: Run Gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Run Trufflehog
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.repository.default_branch }}
```

**Deploy:**
```bash
git add .github/workflows/security-scan.yml .pre-commit-config.yaml
git commit -m "ci: Add secret scanning"
git push origin main
```

**Verify:**
```bash
# Check workflow runs
gh run list --workflow=security-scan.yml
# Expected: Green check marks
```

### Signer Factory Verification

**Check no legacy imports:**
```bash
# Should return NO results
grep -r "from.*signer_factory import create_signer" src/ \
  --exclude-dir=blockchain/signers

# Expected: Exit code 1 (no matches)
echo "Exit code: $?"
```

**Verify production uses KMS:**
```bash
# Check staging config
grep "SIGNER_BACKEND" .env.staging .env.production
# Expected: SIGNER_BACKEND=kms in production

# Dev can use local
# Expected: SIGNER_BACKEND=local in .env.local (OK)
```

### Gate C Sign-Off

**Private key rotated (if needed):** □ Yes / □ N/A  
**Git history purged:** □ Yes / □ No  
**CI secret scanning enabled:** □ Yes / □ No  
**Pre-commit hooks installed:** □ Yes / □ No  
**Signer factory unified:** □ Yes / □ No  
**Production uses KMS:** □ Yes / □ Dev-only  

**Approver:** _______________________  Date: __________

---

## 🚀 PRODUCTION FLIP PLAN

### Phase 1: Prod DRY Soak (2-6h)

**Deploy:**
```bash
# 1. Tag for production
git tag -a v9.0.1 -m "Production Release: All security fixes validated"
git push origin v9.0.1

# 2. Deploy with DRY mode
cp config/env.prod.template .env.production
# Edit: EXEC_MODE=DRY, fill secrets
docker compose --env-file .env.production up -d

# 3. Verify
curl -s https://prod.vanta-bot.com/health | jq '.execution_mode.mode'
# Expected: "DRY"
```

**Watch Metrics (same 4 as Gate A):**
```bash
# Monitor for 2-6 hours
watch -n 30 'curl -s http://prometheus:9090/api/v1/query?query=vanta_intent_duplicate_total | jq'
```

**Pass Criteria:**
- ✅ All 4 metrics within threshold for entire soak period
- ✅ No unexpected errors or restarts
- ✅ Health endpoint returns 200

**Sign-off:** □ Pass / □ Fail  
**Duration:** ______ hours  
**Approver:** _______________________  Date: __________

---

### Phase 2: Prod LIVE Canary (24h minimum)

**Deploy with Tiny Caps:**
```bash
# .env.production.canary
EXEC_MODE=LIVE
MAX_NOTIONAL_USDC=10
MAX_LEVERAGE=2
ALLOWED_SYMBOLS=BTC,ETH
CANARY_ENABLED=true
ALLOW_LIVE_AFTER_STREAK=3

# Redeploy
docker compose --env-file .env.production.canary up -d
```

**Monitor 24h:**
- ✅ Receipts confirmed
- ✅ No duplicate sends
- ✅ Metrics within threshold
- ✅ No user complaints
- ✅ On-call paging = 0

**Sign-off:** □ Pass / □ Fail  
**Approver:** _______________________  Date: __________

---

### Phase 3: Gradual Scale-Up

**Only after 24h canary green:**

```bash
# Phase 3a: Increase notional (wait 12h)
MAX_NOTIONAL_USDC=25

# Phase 3b: Add one symbol (wait 12h)
ALLOWED_SYMBOLS=BTC,ETH,SOL

# Phase 3c: Increase leverage (wait 12h)
MAX_LEVERAGE=4

# Phase 3d: Full caps (wait 24h)
MAX_NOTIONAL_USDC=50
MAX_LEVERAGE=5
ALLOWED_SYMBOLS=BTC,ETH,SOL,MATIC,ARB

# Phase 3e: Remove canary caps (production normal)
CANARY_ENABLED=false
MAX_NOTIONAL_USDC=500  # Or per business rules
```

**Watch metrics at each phase; rollback if any threshold breached.**

---

## 🔴 ABORT & ROLLBACK PROCEDURES

### Immediate Emergency Stop (< 30s)

**Method 1: Redis override (fastest)**
```bash
docker compose exec redis redis-cli SET vanta:exec_mode '{"mode":"DRY","emergency_stop":true}'
# Verify
curl -s https://prod/health | jq '.execution_mode.mode'
# Expected: "DRY" immediately
```

**Method 2: Environment variable**
```bash
# Update .env
EXEC_MODE=DRY
EMERGENCY_STOP=true

# Redeploy
docker compose up -d --force-recreate
```

**Incident Procedure:**
1. ✅ Execute emergency stop (Method 1 or 2)
2. ✅ Verify mode is DRY
3. ✅ Capture logs: `docker compose logs > incident-$(date +%s).log`
4. ✅ Capture metrics snapshot
5. ✅ Notify team in #incidents Slack channel
6. ✅ Create incident report in INCIDENTS/ directory

---

### Version Rollback (< 5 min)

**Rollback to previous stable version:**
```bash
# 1. Stop current version
docker compose down

# 2. Deploy previous tag
git checkout v9.0.0
docker compose --env-file .env.production up -d

# 3. Verify
curl -s https://prod/health | jq '.version'
# Expected: "v9.0.0"
```

**Coordination:**
- ✅ Announce in #ops: "Rolling back to v9.0.0 due to [issue]"
- ✅ Update status page
- ✅ Monitor for stability

---

### Database Restore (only if critical data corruption)

**Use pre-deployment backup:**
```bash
# 1. Stop application
docker compose down

# 2. Restore database
pg_restore -d vanta_production backups/vanta-prod-$(date +%F).dump

# 3. Verify
psql -d vanta_production -c "SELECT COUNT(*) FROM tx_intents WHERE created_at > NOW() - interval '1 day';"

# 4. Restart application
docker compose up -d
```

**Downtime:** ~5-15 minutes  
**Data Loss:** Up to backup time (should be < 1h if automated)

---

## ✅ ONE-PAGE FINAL SIGN-OFF

**Release:** v9.0.1-rc2 → v9.0.1  
**Deployment Date:** _______________

### Gate Results

| Gate | Result | Approver | Date |
|------|--------|----------|------|
| A) Staging DRY 24h | □ Pass / □ Fail | __________ | _____ |
| └─ Duplicate-intent test | □ Pass / □ Fail | | |
| └─ Mock-price guard | □ Pass / □ Fail | | |
| └─ Leverage fallback | □ Pass / □ Fail | | |
| └─ Redis outage drill | □ Pass / □ Fail | | |
| └─ Metrics (24h) | □ Pass / □ Fail | | |
| B) Staging LIVE canary 2-4h | □ Pass / □ Fail | __________ | _____ |
| └─ Receipts confirmed | □ Pass / □ Fail | | |
| └─ No duplicates | □ Pass / □ Fail | | |
| └─ Safety caps enforced | □ Pass / □ Fail | | |
| C) Secrets & hygiene | □ Pass / □ Fail | __________ | _____ |
| └─ Key rotated/purged | □ Yes / □ N/A | | |
| └─ CI scanning enabled | □ Yes / □ No | | |
| └─ Signer factory unified | □ Yes / □ No | | |

### Final Decision

**Overall Result:** □ GO / □ NO-GO

**Approvers (all required):**
- [ ] Engineering Lead: _______________________  Date: __________
- [ ] Operations Lead: _______________________  Date: __________
- [ ] Security Lead: _______________________  Date: __________
- [ ] Product Lead: _______________________  Date: __________

### If GO:
**Production deployment authorized:** □ Yes  
**Next Step:** Execute Production Flip Plan Phase 1 (Prod DRY soak)  
**ETA to LIVE:** _______________

### If NO-GO:
**Blocking issues:**
1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

**Remediation plan:**
- Action: _______________________________________________
- Owner: _______________________________________________
- ETA: _______________

**Next review:** _______________

---

## 📊 METRICS DASHBOARD

**Grafana Dashboard:** http://grafana:3000/d/go-no-go  
**Prometheus:** http://prometheus:9090  
**Logs:** `docker compose logs -f --tail=100`

**Key Alerts:**
- DuplicateIntentsDetected (critical)
- ExecutionModeStuckInLive (critical)
- HighTransactionFailureRate (critical)
- RedisHealthDegraded (warning)

---

**Document Version:** 1.0  
**Last Updated:** September 30, 2025  
**Next Review:** After each gate completion

