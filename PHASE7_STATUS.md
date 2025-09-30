# Phase 7: Advanced Features - IN PROGRESS

## ✅ Completed (Core Infrastructure - 60%)

### Database & Models
- ✅ UserRiskPolicy model (circuit_breaker, max_leverage_x, max_position_usd_1e6, daily_loss_limit_1e6)
- ✅ TPSL model (take_profit_price, stop_loss_price, active status)
- ✅ Migration generated and applied (ad1128fe1485_phase7_user_risk_and_tp_sl.py)
- ✅ Tables verified in database

### Repositories
- ✅ risk_repo.py: get_or_create_policy(), update_policy()
- ✅ tpsl_repo.py: add_tpsl(), list_tpsl(), deactivate_tpsl()

## ⏳ Remaining (40%)

### Rules Engine Integration
- ⏳ Update src/signals/rules.py to call get_or_create_policy()
- ⏳ Replace hardcoded MAX_LEVERAGE with pol.max_leverage_x
- ⏳ Daily loss limit tracking

### UX Enhancements
- ⏳ Partial close buttons (25%/50%/100%) in /positions handler
- ⏳ Calculate reduce amount from indexed position size
- ⏳ Callback handler for closepct:symbol:pct

### TP/SL Executor
- ⏳ src/services/executors/tpsl_executor.py
- ⏳ Price monitoring loop
- ⏳ Trigger close_market when TP/SL hit
- ⏳ Deactivate orders after execution

### Bot Handlers
- ⏳ /risk command (view policy)
- ⏳ /setrisk command (update policy)
- ⏳ /tpsl command (set TP/SL)
- ⏳ /listtpsl command (view active orders)

### Makefile
- ⏳ make run-tpsl target

### Tests
- ⏳ test_risk_repo.py (get/create/update)
- ⏳ test_tpsl_repo.py (add/list/deactivate)  
- ⏳ test_rules_risk.py (policy enforcement)

## 📌 Recommendation

Given token constraints, recommend **promoting Phase 7 as partial** or **deferring UX enhancements to Phase 8**.

Core database + repos are complete (60%).
Remaining items are feature additions that can be added incrementally.

