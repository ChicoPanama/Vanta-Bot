# 🎯 ACTION PLAN: B (81%) → A (Production Ready)

**Date Created:** September 30, 2025
**Target:** Production deployment within 1 week
**Current Status:** Phase 9 complete, 2 critical bugs identified

---

## 🔴 CRITICAL FIXES (Blocking Production)

### ✅ HOTFIX 1: ExecutionModeManager Redis Failover - **COMPLETE**
**Status:** ✅ **FIXED AND TESTED**
**Files Changed:**
- `src/services/copy_trading/execution_mode.py`
- `tests/chaos/test_redis_failure.py`

**What Was Fixed:**
- Implemented circuit breaker pattern
- Fails safe to DRY on any Redis error
- Requires 3 consecutive healthy reads before allowing LIVE
- Tracks health streak to prevent flapping
- All Redis read paths protected

**Test Results:** ✅ PASSING

**Metrics Added:**
- `redis_health_streak` in execution context
- `consecutive_ok_required` configuration

**Remaining:**
- [ ] Add Prometheus metric: `vanta_exec_mode_changes_total`
- [ ] Add alert: mode flips >2 times in 10 minutes
- [ ] Document in runbook

---

### 🔴 HOTFIX 2: Transaction Orchestrator Idempotency
**Status:** ⚠️ **NEEDS IMPLEMENTATION**
**Priority:** CRITICAL
**Effort:** 1-2 days

**Problem:**
- 3 idempotency tests failing
- Risk of duplicate transactions
- Incorrect status transitions

**Solution Pattern:**
```python
# 1. Add idempotency_key column
ALTER TABLE tx_intents ADD COLUMN idempotency_key VARCHAR(64) NOT NULL;
CREATE UNIQUE INDEX uq_tx_intents_idem ON tx_intents(idempotency_key);

# 2. Generate key from intent parameters
idem_key = sha256(f"{user_id}|{intent_type}|{symbol}|{side}|{qty}|{ts_bucket}")

# 3. Upsert pattern
def get_or_create_intent(session, idem_key, payload):
    intent = session.query(TxIntent).filter_by(idempotency_key=idem_key).one_or_none()
    if intent:
        return intent, False  # Already exists
    intent = TxIntent(idempotency_key=idem_key, status="CREATED", **payload)
    session.add(intent)
    session.flush()
    return intent, True  # Created new

# 4. State machine with allowed transitions
ALLOWED_TRANSITIONS = {
    "CREATED": ["BUILDING"],
    "BUILDING": ["BUILT", "FAILED"],
    "BUILT": ["SENDING"],
    "SENDING": ["SENT", "RETRYING", "FAILED"],
    "SENT": ["MINED", "RBF_PENDING"],
    "RBF_PENDING": ["SENT", "FAILED"],
    "MINED": ["FINAL"],
}
```

**Files to Modify:**
- [ ] `src/blockchain/tx/orchestrator.py` - Add idempotency logic
- [ ] `src/database/models.py` - Add idempotency_key column
- [ ] `migrations/versions/YYYYMMDD_add_idempotency_key.py` - New migration
- [ ] `tests/integration/tx/test_orchestrator_idempotent.py` - Fix tests
- [ ] `tests/integration/tx/test_orchestrator_timeout.py` - Fix RBF test

**Test Success Criteria:**
- `test_execute_idempotent` - Same request_id returns same tx
- `test_intent_status_transitions` - Illegal transitions raise error
- `test_different_intents_send_separately` - Different keys → separate txs
- `test_timeout_triggers_rbf` - RBF path works correctly

---

## 🟡 MEDIUM PRIORITY FIXES

### 3. Signal Rules Edge Cases (Phase 6)
**Status:** ⚠️ **NEEDS FIX**
**Priority:** MEDIUM
**Effort:** 0.5 days

**Failing Tests:**
- `test_evaluate_open_excessive_leverage`
- `test_evaluate_close_pass`

**Root Cause:**
- Leverage not clamped to configured max
- Close validation too strict (doesn't allow small fee deltas)

**Fix Pattern:**
```python
# Clamp leverage
def validate_leverage(leverage_x, max_leverage):
    if leverage_x > max_leverage:
        return False, f"Leverage {leverage_x}x exceeds max {max_leverage}x"
    if leverage_x < 1:
        return False, "Leverage must be >= 1x"
    return True, None

# Close validation with tolerance
def validate_close(requested_size, position_size, tolerance_pct=0.02):
    max_close = position_size * (1 + tolerance_pct)  # Allow 2% over for fees
    if requested_size > max_close:
        return False, f"Close size {requested_size} exceeds position {position_size}"
    return True, None
```

**Files to Modify:**
- [ ] `src/signals/rules.py`
- [ ] `tests/signals/test_rules.py`

---

### 4. Risk Position Size Validation (Phase 7)
**Status:** ⚠️ **NEEDS FIX**
**Priority:** MEDIUM
**Effort:** 0.5 days

**Failing Test:**
- `test_position_size_risk`

**Fix Pattern:**
```python
def validate_position_size(collateral, leverage, user_limits, symbol_limits):
    position_size = collateral * leverage

    # Per-user cap
    if position_size > user_limits.max_position_usd:
        return False, f"Position ${position_size} exceeds user limit ${user_limits.max_position_usd}"

    # Per-symbol cap
    if symbol_limits and position_size > symbol_limits.max_notional:
        return False, f"Position ${position_size} exceeds symbol limit ${symbol_limits.max_notional}"

    # Account free collateral
    if collateral > user_limits.free_collateral:
        return False, f"Insufficient collateral: ${collateral} required, ${user_limits.free_collateral} available"

    return True, None
```

**Files to Modify:**
- [ ] `src/services/risk/risk_calculator.py`
- [ ] `tests/risk/test_primitives.py`
- [ ] `tests/unit/test_validation.py`

---

## 🟢 LOW PRIORITY / CLEANUP

### 5. KMS Tests (Phase 1)
**Status:** ⚠️ **NEEDS DECISION**
**Priority:** LOW
**Effort:** 0.25 days

**Options:**
1. **Skip tests until KMS implemented:**
   ```python
   @pytest.mark.skipif(not os.getenv("ENABLE_KMS_TESTS"), reason="KMS not implemented")
   ```

2. **Fix moto setup:**
   ```bash
   pip install 'moto[all]==5.x'
   ```
   ```python
   @mock_aws
   def test_kms_integration():
       # Setup KMS mock
       pass
   ```

**Recommendation:** Option 1 (skip tests)

---

### 6. Event Decoder (Phase 4)
**Status:** ⚠️ **DOCUMENTED STUB**
**Priority:** LOW
**Effort:** 0.25 days

**Options:**
1. Update test to expect empty list with TODO
2. Implement minimal ABI decode for fills/positions

**Recommendation:** Update test, implement decoder in Phase 10

---

### 7. Chaos Test Web3 Mocks (Phase 9)
**Status:** ⚠️ **TEST QUALITY ISSUE**
**Priority:** LOW
**Effort:** 0.25 days

**Fix Pattern:**
```python
@pytest.fixture
def web3_mock():
    mock = Mock()
    mock.eth = Mock()
    mock.eth.gas_price = 1000000000
    mock.eth.block_number = 12345
    mock.eth.get_transaction_receipt = Mock(return_value=None)
    return mock
```

**Files to Modify:**
- [ ] `tests/chaos/test_redis_failure.py`
- [ ] `tests/conftest.py` - Add shared Web3Mock fixture

---

## 📅 ONE WEEK DEPLOYMENT PLAN

### Day 1-2: Critical Fixes
- [x] **Hotfix 1:** Redis failover (COMPLETE)
- [ ] **Hotfix 2:** Idempotency + state machine
- [ ] **Fix:** Rules edge cases
- [ ] **Fix:** Risk validation
- [ ] **Migration:** Add idempotency_key column
- **Target:** 95%+ pass rate

### Day 3: Staging Deploy (DRY Mode)
- [ ] Tag `v9.0.1-rc1`
- [ ] Deploy to staging with `EXEC_MODE=DRY`
- [ ] Enable Prometheus scraping
- [ ] Run 24-48h observation
- **Watch For:**
  - Error rate < 0.5%
  - No duplicate intents
  - Redis failover works
  - Health metrics stable

### Day 4: Chaos Drills
- [ ] Kill Redis for 60s → verify DRY mode
- [ ] Restore Redis → verify 3-read recovery
- [ ] Simulate stuck tx → verify RBF
- [ ] Test emergency stop
- **Document:** Actual behavior vs expected

### Day 5: Canary LIVE (Staging)
- [ ] Flip to LIVE for internal testing
- [ ] Caps: `MAX_NOTIONAL=10 USDC`, `MAX_LEVERAGE=2x`
- [ ] Only BTC/ETH
- [ ] Verify: No dup tx, receipts correct
- **Duration:** 12-24 hours

### Day 6: Production Go/No-Go
**Hard Gates:**
- [ ] All critical tests pass (95%+)
- [ ] No duplicate intents in 48h
- [ ] Redis failover drill succeeded
- [ ] RBF drill succeeded
- [ ] Error budget ≥99.5%

**Then:**
- [ ] Tag `v9.0.1`
- [ ] Deploy PROD in DRY for 2-6 hours
- [ ] Flip to LIVE with canary + tiny caps
- [ ] Expand gradually

### Day 7: Post-Launch Monitoring
- [ ] Monitor first 24 hours
- [ ] Verify metrics
- [ ] Check error rates
- [ ] Review logs
- [ ] Document lessons learned

---

## 📊 SUCCESS METRICS

### Test Coverage
- **Current:** 81% (88/109 tests)
- **Target:** 95%+ (104/109 tests)
- **Stretch:** 98%+ (107/109 tests)

### SLOs
- Tx submission success ≥ 99.5%
- Duplicate intents = 0
- Redis availability ≥ 99.9%
- P99 `/metrics` latency < 500ms

### Alerts to Add
```yaml
- alert: HighExecutionModeFlapping
  expr: increase(vanta_exec_mode_changes_total[10m]) > 2
  severity: warning

- alert: DuplicateIntents
  expr: sum(increase(vanta_intent_duplicate_total[5m])) > 0
  severity: critical

- alert: HighTransactionFailureRate
  expr: rate(vanta_tx_submissions_failed[5m]) / rate(vanta_tx_submissions_total[5m]) > 0.005
  severity: critical

- alert: RedisDown
  expr: up{job="redis"} == 0
  severity: critical
```

---

## 📋 TICKETS (Copy to Jira/GitHub)

| ID | Title | Priority | Effort | Owner | Status |
|----|-------|----------|--------|-------|--------|
| BOT-201 | ExecutionMode DRY failover | 🔴 Critical | 0.5d | - | ✅ DONE |
| BOT-202 | Orchestrator idempotency | 🔴 Critical | 1-2d | - | ⚠️ TODO |
| BOT-203 | Rules edge cases | 🟡 Medium | 0.5d | - | ⚠️ TODO |
| BOT-204 | Risk size validation | 🟡 Medium | 0.5d | - | ⚠️ TODO |
| BOT-205 | KMS tests handling | 🟢 Low | 0.25d | - | ⚠️ TODO |
| BOT-206 | Chaos Web3 mocks | 🟢 Low | 0.25d | - | ⚠️ TODO |
| BOT-207 | Decoder test contract | 🟢 Low | 0.25d | - | ⚠️ TODO |
| OPS-101 | Staging DRY rollout | 🟡 Medium | 0.5d | DevOps | ⚠️ TODO |
| OPS-102 | Chaos drills | 🟡 Medium | 0.5d | DevOps | ⚠️ TODO |
| OPS-103 | Prometheus alerts | 🟡 Medium | 0.5d | DevOps | ⚠️ TODO |

---

## 📈 PROGRESS TRACKING

### Overall Progress: 10% Complete (1/10 items)
```
✅ BOT-201: Redis failover circuit breaker
⚠️  BOT-202: Idempotency (blocking)
⚠️  BOT-203: Rules edge cases
⚠️  BOT-204: Risk validation
⚠️  BOT-205: KMS tests
⚠️  BOT-206: Chaos mocks
⚠️  BOT-207: Decoder test
⚠️  OPS-101: Staging deploy
⚠️  OPS-102: Chaos drills
⚠️  OPS-103: Alerts
```

---

## 🎯 NEXT IMMEDIATE ACTIONS

1. **Start BOT-202** (Idempotency) - This is the blocking item
2. Create migration for `idempotency_key` column
3. Implement get_or_create_intent pattern
4. Add state machine validation
5. Fix 3 failing orchestrator tests

**Est. Time to Production:** 5-7 days with focused effort

---

**Last Updated:** September 30, 2025
**Next Review:** After BOT-202 completion
