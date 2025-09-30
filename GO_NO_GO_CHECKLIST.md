# 🚦 GO/NO-GO CHECKLIST - v9.0.1-rc2

**Release:** v9.0.1-rc2  
**Tag SHA:** caf62bd  
**Date:** September 30, 2025  
**Status:** ⚠️ **VALIDATION REQUIRED**

---

## 📋 CRITICAL GO/NO-GO GATES

**ALL ITEMS MUST BE ✅ BEFORE DEPLOYMENT**

---

## 🔐 SECTION 1: SECURITY VALIDATION (BLOCKING)

### ✅ SEC-001: Deterministic Idempotency Keys

**Commit:** e0c5e53  
**File:** `src/blockchain/avantis/service.py`  
**GitHub:** [View Diff](https://github.com/ChicoPanama/Vanta-Bot/commit/e0c5e53)

**What Changed:**
- ❌ BEFORE: `intent_key = f"open:{user_id}:{symbol}:{uuid4()}"` (random)
- ✅ AFTER: `intent_key = make_intent_key(user_id, "open", symbol, side, qty_1e6)` (deterministic)

**Validation Checklist:**
- [ ] ⚠️ Code review: `src/blockchain/avantis/service.py` lines 23-59 (make_intent_key function)
- [ ] ⚠️ Code review: Lines 129-140 (open_market usage)
- [ ] ⚠️ Code review: Lines 177-187 (close_market usage)
- [ ] ⚠️ Test review: All 8 tests in `tests/security/test_idempotency_deterministic.py` pass
- [ ] ⚠️ **STAGING TEST:** Send duplicate open request within 1s → verify single TxIntent
- [ ] ⚠️ **STAGING TEST:** Check `tx_intents` table has unique `intent_key` for duplicates
- [ ] ⚠️ **STAGING TEST:** Verify `vanta_intent_duplicate_total` metric = 0

**Risk if Skipped:** 🔴 CRITICAL - Duplicate real transactions possible

**Sign-off:** _______________________  Date: __________

---

### ✅ SEC-002: Mock Price Guard

**Commit:** e0c5e53  
**File:** `src/blockchain/avantis_client.py`  
**GitHub:** [View Diff](https://github.com/ChicoPanama/Vanta-Bot/commit/e0c5e53)

**What Changed:**
- ❌ BEFORE: Returns hardcoded BTC=$50k, ETH=$3k with no guard
- ✅ AFTER: Raises RuntimeError if `ENVIRONMENT` in ("production", "prod", "staging")

**Validation Checklist:**
- [ ] ⚠️ Code review: `src/blockchain/avantis_client.py` lines 472-510
- [ ] ⚠️ **CONFIG CHECK:** Verify `ENVIRONMENT=production` in staging config
- [ ] ⚠️ **STAGING TEST:** Verify `get_real_time_prices()` raises RuntimeError
- [ ] ⚠️ **CODE REVIEW:** Confirm `PriceAggregator` used in all production paths
- [ ] ⚠️ **CODE REVIEW:** Check `AvantisService` uses `self.price_agg` (not mock)

**Risk if Skipped:** 🔴 CRITICAL - Trading on incorrect mock prices

**Sign-off:** _______________________  Date: __________

---

### ✅ SEC-003: Private Key Exposure

**Commit:** e0c5e53  
**File:** `scripts/use_sdk_build_trade_open_tx.py`  
**GitHub:** [View Diff](https://github.com/ChicoPanama/Vanta-Bot/commit/e0c5e53)

**What Changed:**
- ❌ BEFORE: `"TRADER_PRIVATE_KEY": "aa3645...1f87"` (hardcoded)
- ✅ AFTER: Commented out with security warning

**Validation Checklist:**
- [ ] ⚠️ Code review: `scripts/use_sdk_build_trade_open_tx.py` lines 25-26
- [ ] ⚠️ **CRITICAL:** Verify key `aa3645...1f87` was NEVER used with real funds
- [ ] ⚠️ **CRITICAL:** If key ever used with funds → rotate/revoke on-chain
- [ ] ⚠️ **CRITICAL:** Purge key from git history:
  ```bash
  git filter-repo --path scripts/use_sdk_build_trade_open_tx.py --invert-paths
  # OR use GitHub secret scanning
  ```
- [ ] ⚠️ **CI/CD:** Add secret scanner (gitleaks or trufflehog):
  ```bash
  # .github/workflows/security.yml
  - uses: trufflesecurity/trufflehog@main
  ```

**Risk if Skipped:** 🔴 CRITICAL - Funds at risk if key ever used

**Sign-off:** _______________________  Date: __________

---

### ✅ SEC-004: Safe Leverage Fallback

**Commit:** e0c5e53  
**File:** `src/copy_trading/copy_executor.py`  
**GitHub:** [View Diff](https://github.com/ChicoPanama/Vanta-Bot/commit/e0c5e53)

**What Changed:**
- ❌ BEFORE: `return float(row["max_leverage"]) if row else 50.0`
- ✅ AFTER: `return float(row["max_leverage"]) if row else 5.0`

**Validation Checklist:**
- [ ] ⚠️ Code review: `src/copy_trading/copy_executor.py` lines 671-696
- [ ] ⚠️ **DATABASE CHECK:** Verify all `copy_configurations` have `max_leverage` set
- [ ] ⚠️ **STAGING TEST:** Test with missing config → verify 5x used (not 50x)
- [ ] ⚠️ **STAGING TEST:** Verify per-user `UserRiskPolicy.max_leverage_x` enforced

**Risk if Skipped:** 🟡 MEDIUM - Unintentional high leverage

**Sign-off:** _______________________  Date: __________

---

### ✅ SEC-005: Single Signer Factory

**Commits:** e0c5e53  
**Files:** `src/blockchain/base_client.py`, `src/blockchain/signer_factory.py`  
**GitHub:** [View Diff](https://github.com/ChicoPanama/Vanta-Bot/commit/e0c5e53)

**What Changed:**
- ✅ `base_client.py` now imports from `signers.factory.get_signer`
- ✅ Legacy `signer_factory.py` deprecated with clear error message

**Validation Checklist:**
- [ ] ⚠️ Code review: `src/blockchain/base_client.py` line 294
- [ ] ⚠️ Code review: `src/blockchain/signer_factory.py` (entire file)
- [ ] ⚠️ **GREP CHECK:** No references to old factory:
  ```bash
  grep -r "from.*signer_factory import" src/ --exclude-dir=blockchain/signer_factory.py
  # Should return NO results
  ```
- [ ] ⚠️ **CONFIG CHECK:** Verify `SIGNER_BACKEND=kms` (not "local") in production

**Risk if Skipped:** 🟡 MEDIUM - Configuration confusion

**Sign-off:** _______________________  Date: __________

---

## 🧪 SECTION 2: STAGING SMOKE TESTS (BLOCKING)

### Test 1: Idempotency Validation

**Setup:**
```bash
# Deploy to staging with ENVIRONMENT=production, EXEC_MODE=DRY
docker compose --env-file .env.staging up -d
```

**Test Steps:**
```bash
# 1. Send duplicate open signal within 1s
payload='{"source":"test","signal_id":"smoke-001","tg_user_id":123,"symbol":"BTC-USD","side":"LONG","collateral_usdc":10,"leverage_x":2,"slippage_pct":0.5}'
sig=$(echo -n "$payload" | openssl dgst -sha256 -hmac "$WEBHOOK_HMAC_SECRET" -r | cut -d' ' -f1)

# Send twice rapidly
curl -X POST http://staging:8090/signals -H "Content-Type: application/json" -H "X-Signature: $sig" -d "$payload" &
curl -X POST http://staging:8090/signals -H "Content-Type: application/json" -H "X-Signature: $sig" -d "$payload" &
wait

# 2. Check database
docker compose exec postgres psql -U user -d vanta -c \
  "SELECT COUNT(*), intent_key FROM tx_intents WHERE intent_key LIKE '%smoke-001%' GROUP BY intent_key;"
# Expected: 1 row, COUNT = 1

# 3. Check metrics
curl -s http://staging:8090/metrics | grep vanta_intent_duplicate_total
# Expected: 0
```

**Pass Criteria:**
- [ ] ⚠️ Only 1 TxIntent created despite duplicate requests
- [ ] ⚠️ `vanta_intent_duplicate_total` = 0
- [ ] ⚠️ Logs show "Found existing intent" for second request

**Sign-off:** _______________________  Date: __________

---

### Test 2: Mock Price Block Validation

**Test Steps:**
```python
# In staging environment with ENVIRONMENT=production
from src.blockchain.avantis_client import AvantisClient

client = AvantisClient(...)
try:
    prices = client.get_real_time_prices(["BTC", "ETH"])
    print("❌ FAIL: Mock prices returned!")
except RuntimeError as e:
    if "Mock price method not available in production" in str(e):
        print("✅ PASS: Mock prices blocked!")
    else:
        print(f"❌ FAIL: Wrong error: {e}")
```

**Pass Criteria:**
- [ ] ⚠️ `get_real_time_prices()` raises RuntimeError in staging
- [ ] ⚠️ Error message directs to use PriceAggregator
- [ ] ⚠️ Verify `AvantisService` uses `PriceAggregator` for all prices

**Sign-off:** _______________________  Date: __________

---

### Test 3: Leverage Fallback Validation

**Test Steps:**
```sql
-- 1. Create user without copy config
INSERT INTO copy_configurations (copytrader_id) VALUES (999);
-- Intentionally omit max_leverage

-- 2. Trigger copy trade for user 999
-- 3. Check logs
docker compose logs worker | grep "max leverage"
# Expected: "max leverage: 5.0" (not 50.0)
```

**Pass Criteria:**
- [ ] ⚠️ Missing config uses 5.0x (not 50.0x)
- [ ] ⚠️ All existing configs have explicit `max_leverage` set

**Sign-off:** _______________________  Date: __________

---

## 🔥 SECTION 3: CHAOS DRILLS (BLOCKING)

### Drill 1: Redis Outage → Circuit Breaker (BOT-201)

**Commit:** 1a6e611  
**File:** `src/services/copy_trading/execution_mode.py`  
**GitHub:** [View Diff](https://github.com/ChicoPanama/Vanta-Bot/commit/1a6e611)

**Test Steps:**
```bash
# 1. Verify starting state
curl -s http://staging:8090/health | jq '.execution_mode'
# Expected: {"mode":"DRY","redis_health_streak":3}

# 2. Pause Redis
docker compose pause redis

# 3. Generate traffic for 60s
for i in {1..10}; do
  curl -s http://staging:8090/health | jq '.execution_mode.mode'
  sleep 5
done
# Expected: All should show "DRY"

# 4. Unpause Redis
docker compose unpause redis

# 5. Monitor recovery (requires 3 healthy reads)
for i in {1..10}; do
  curl -s http://staging:8090/health | jq '.execution_mode'
  sleep 2
done
# Expected: redis_health_streak increments: 0→1→2→3
```

**Pass Criteria:**
- [ ] ⚠️ Bot immediately fails to DRY on Redis failure
- [ ] ⚠️ Logs show "FAILING SAFE TO DRY MODE"
- [ ] ⚠️ After recovery, requires 3 consecutive reads before LIVE
- [ ] ⚠️ `vanta_exec_mode_changes_total` increments appropriately

**Sign-off:** _______________________  Date: __________

---

### Drill 2: Duplicate Signal → Idempotency (SEC-001)

**Test Steps:**
```bash
# Already covered in Section 2, Test 1
# This drill validates the fix under load

# Send 10 duplicate requests concurrently
for i in {1..10}; do
  curl -X POST http://staging:8090/signals \
    -H "Content-Type: application/json" \
    -H "X-Signature: $sig" \
    -d "$payload" &
done
wait

# Check database
# Expected: Still only 1 TxIntent
```

**Pass Criteria:**
- [ ] ⚠️ Only 1 TxIntent despite 10 concurrent requests
- [ ] ⚠️ No race conditions or deadlocks

**Sign-off:** _______________________  Date: __________

---

### Drill 3: RPC Hiccup → RBF Behavior

**Test Steps:**
```bash
# Simulate slow RPC (if using toxiproxy)
# OR temporarily point to a rate-limited endpoint

# Monitor RBF attempts
docker compose logs orchestrator | grep -i "rbf"
docker compose logs orchestrator | grep -i "timeout"

# Check metrics
curl -s http://staging:8090/metrics | grep vanta_rbf
```

**Pass Criteria:**
- [ ] ⚠️ Timeouts handled gracefully
- [ ] ⚠️ RBF attempts logged (if applicable)
- [ ] ⚠️ No cascading failures

**Sign-off:** _______________________  Date: __________

---

## 🔒 SECTION 4: SECRET MANAGEMENT (BLOCKING)

### Private Key Rotation

**Exposed Key:** `aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87`

**Required Actions:**
- [ ] ⚠️ **CRITICAL:** Verify this key was NEVER used with real funds
  ```bash
  # Check blockchain for transactions from this key's address
  # If found: IMMEDIATELY drain funds to safe address
  ```
- [ ] ⚠️ **CRITICAL:** If key ever used → rotate on-chain
- [ ] ⚠️ **CRITICAL:** Generate new key for production:
  ```bash
  openssl rand -hex 32
  # Store in secure secret manager (AWS Secrets Manager, HashiCorp Vault)
  ```
- [ ] ⚠️ **CRITICAL:** Update all configs to use new key
- [ ] ⚠️ **CRITICAL:** Purge old key from git history:
  ```bash
  # Option 1: BFG Repo-Cleaner
  bfg --replace-text passwords.txt
  
  # Option 2: git-filter-repo
  git filter-repo --path scripts/use_sdk_build_trade_open_tx.py --invert-paths
  
  # Option 3: GitHub secret scanning removal request
  ```

**Sign-off:** _______________________  Date: __________

---

### CI Secret Scanning

**Required Actions:**
- [ ] ⚠️ Add pre-commit hook with gitleaks:
  ```yaml
  # .pre-commit-config.yaml
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
  ```
- [ ] ⚠️ Add GitHub Actions secret scan:
  ```yaml
  # .github/workflows/security.yml
  name: Security Scan
  on: [push, pull_request]
  jobs:
    secrets:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v3
        - uses: trufflesecurity/trufflehog@main
          with:
            path: ./
            base: main
  ```
- [ ] ⚠️ Enable GitHub secret scanning (Settings → Security → Secret scanning)

**Sign-off:** _______________________  Date: __________

---

## 📊 SECTION 5: METRICS & MONITORING (RECOMMENDED)

### Prometheus Alerts Verification

**File:** `ops/production-alerts.rules.yml`

**Validation:**
```bash
# Validate alert rules
promtool check rules ops/production-alerts.rules.yml

# Load into Prometheus
# Add to prometheus.yml:
# rule_files:
#   - "ops/production-alerts.rules.yml"

# Reload Prometheus
curl -X POST http://prometheus:9090/-/reload
```

**Checklist:**
- [ ] ⏳ Alert rules validated with promtool
- [ ] ⏳ Rules loaded into Prometheus
- [ ] ⏳ Test firing conditions:
  - DuplicateIntentsDetected
  - ExecutionModeStuckInLive
  - HighTransactionFailureRate

**Sign-off:** _______________________  Date: __________

---

## ✅ SECTION 6: FINAL GO/NO-GO DECISION

### Pre-Deployment Summary

**Security Fixes Applied:**
- ✅ SEC-001: Deterministic idempotency keys
- ✅ SEC-002: Mock price guards
- ✅ SEC-003: Hardcoded key removed
- ✅ SEC-004: Safe leverage fallback
- ✅ SEC-005: Single signer factory

**Test Coverage:**
- Tests Passed: 97/109 (84%)
- New Security Tests: 8/8 passed
- Production Blockers: 0 (after validation)

**Tag Information:**
- Release: v9.0.1-rc2
- Commit: caf62bd
- GitHub: https://github.com/ChicoPanama/Vanta-Bot/releases/tag/v9.0.1-rc2

---

### GO/NO-GO DECISION CRITERIA

**🟢 GO if ALL are TRUE:**
- [ ] ✅ All Section 1 security validations complete
- [ ] ✅ All Section 2 staging smoke tests pass
- [ ] ✅ All Section 3 chaos drills pass
- [ ] ✅ Section 4 secret management complete
- [ ] ✅ Private key rotated/verified unused
- [ ] ✅ Git history purged
- [ ] ✅ CI secret scanning enabled
- [ ] ✅ `ENVIRONMENT=production` in all prod configs
- [ ] ✅ All sign-offs obtained

**🔴 NO-GO if ANY are TRUE:**
- [ ] ❌ Any security validation failed
- [ ] ❌ Idempotency test shows duplicates
- [ ] ❌ Mock prices not blocked in staging
- [ ] ❌ Private key not rotated (if ever used)
- [ ] ❌ Redis failover didn't work
- [ ] ❌ Any missing sign-offs

---

### FINAL DECISION

**Date:** _______________  
**Decision:** ⬜ GO / ⬜ NO-GO  
**Approved By:**

- Engineering Lead: _______________________
- Security Lead: _______________________
- Operations Lead: _______________________

**If NO-GO, Blocking Issues:**
- [ ] _______________________________________
- [ ] _______________________________________
- [ ] _______________________________________

**Next Steps if GO:**
1. Proceed to DEPLOYMENT_CHECKLIST.md Phase 1 (Staging DRY)
2. Monitor for 24-48 hours
3. Conduct remaining chaos drills
4. Proceed to canary LIVE per schedule

**Next Steps if NO-GO:**
1. Document all blocking issues
2. Create remediation plan
3. Fix blocking issues
4. Re-run validation
5. Reconvene for new GO/NO-GO

---

**Document Version:** 1.0  
**Last Updated:** September 30, 2025  
**Next Review:** After validation complete

