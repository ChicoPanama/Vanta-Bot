# Phases Breakdown (0 → 9)

This document tracks the detailed breakdown and acceptance criteria for each phase of the Vanta-Bot End-to-End Refactor & Integration.

---

## Phase 0 — Baseline Hygiene ✅ COMPLETED

**Goal:** Make the repo easy to run, test, and contribute to—without touching business logic. Create clean structure, enforce tooling, and corral loose scripts/tests.

### Deliverables:
- ✅ Python pinned to 3.11 in `pyproject.toml` and mypy config
- ✅ `.env.example` added/updated with placeholder values
- ✅ Loose debug/e2e scripts moved to `scripts/` or `tests/e2e/adhoc/`
- ✅ Default tests run fast and deterministically (adhoc excluded)
- ✅ Makefile targets verified: `dev-install`, `test-unit`, `test-integration`, `type-check`
- ✅ Pre-commit and secret scan wired (trufflehog in CI)
- ✅ Mock oracle not importable in prod paths (TEST ONLY banner)
- ✅ README quick start accurate
- ✅ Phase gate scaffolding: `PHASE_STATE.md`, PR template, `scripts/verify_release.py`

### Acceptance Criteria:
- [x] Python 3.11 requirement enforced
- [x] `.gitignore` hardened (coverage artifacts, dumps)
- [x] `pytest.ini` excludes `tests/e2e/adhoc` by default
- [x] CI runs lint, typecheck, tests, security scan, phase gate
- [x] All checks pass (with legacy issues documented and ignored)

**Branch:** `chore/phase-0-baseline`
**Status:** PASSED (2025-09-30)

---

## Phase 1 — Secrets & Safety 🚧 IN PROGRESS

**Goal:** Eliminate catastrophic key exposure risks and make secret handling boring, automated, and testable.

### Deliverables:
- [ ] Typed configuration with Pydantic (`src/config/settings.py`)
- [ ] KMS-first signer with local fallback for dev
- [ ] Envelope encryption utilities (AES-GCM + KMS)
- [ ] Encrypted SQLAlchemy types for sensitive DB fields
- [ ] Migration for encrypted columns/tables
- [ ] Credentials repository API
- [ ] Startup validation (fail fast on config errors)
- [ ] CI secret scanning enforced
- [ ] DEK rotation script (`scripts/rewrap_deks.py`)
- [ ] Unit & integration tests for crypto, signers, encrypted types

### Acceptance Criteria:
- [ ] KMS-first signer wired; local signer prints clear warning
- [ ] Typed settings control all env; missing critical vars fail fast
- [ ] Envelope encryption with AES-GCM; DEK wrapped by KMS
- [ ] Migrations add encrypted columns/tables and apply cleanly
- [ ] Rotation script rewraps stored DEKs without data loss
- [ ] Secret scanning runs in CI; pre-commit hooks enabled
- [ ] Unit/integration tests cover signer, crypto, encrypted types

**Branch:** `feat/phase-1-secrets-safety`
**Status:** IN_PROGRESS

---

## Phase 2 — Transaction Pipeline

**Goal:** A single, reliable path for every on-chain action: build → gas policy → nonce → sign → send → confirm → persist → reconcile.

### Planned Deliverables:
- EIP-1559 gas policy by default
- Redis-backed nonce manager (monotonic under concurrency)
- Transaction builder, sender with RBF retries
- Receipt watcher with confirmations
- Idempotency keys for intents
- Typed persistence (TxIntent, TxSend, TxReceipt models)
- Transaction orchestrator
- Unit & integration tests

**Status:** PLANNED

---

## Phase 3 — Avantis SDK Hardwiring

**Goal:** Thin, deterministic integration layer around Avantis: normalize units once, resolve addresses centrally, use real price feeds only, produce calldata then hand off to TxOrchestrator.

### Planned Deliverables:
- Canonical market & address registry
- Real price adapters (Pyth/Chainlink) with aggregator
- Unit normalization (single-scaling rule)
- ABI + calldata builders for Avantis actions
- Integration service (single public surface)
- UX-ready schemas (strict types)
- Startup validation for feeds & markets
- Unit & integration tests

**Status:** PLANNED

---

## Phase 4 — TBD

*To be defined after Phase 0–3 completion.*

---

## Phase 5 — TBD

*To be defined after Phase 0–3 completion.*

---

## Phase 6 — TBD

*To be defined after Phase 0–3 completion.*

---

## Phase 7 — TBD

*To be defined after Phase 0–3 completion.*

---

## Phase 8 — TBD

*To be defined after Phase 0–3 completion.*

---

## Phase 9 — TBD

*To be defined after Phase 0–3 completion.*

---

## Phase Progression Rules

1. **No skipping phases:** Phase N+1 cannot begin until Phase N status = `PASSED`
2. **Phase gate enforcement:** CI `phase_gate` job blocks PRs for Phase N+1 if Phase N ≠ `PASSED`
3. **Required artifacts per phase:**
   - Updated `PHASE_STATE.md`
   - `docs/` updates (design notes, rollback steps)
   - `CHANGELOG.md` entry
   - Tests + coverage report (≥80% on touched lines)
   - Updated `scripts/verify_release.py`
4. **Promotion ritual:** PR review → comment "Promote Phase N" → merge → update `PHASE_STATE.md` to `PASSED`

---

*Last updated: 2025-09-30*
