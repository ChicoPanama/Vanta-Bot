# Delivery Plan

We will execute phases sequentially with strict phase gates. Each phase ships in one or more PRs with tests, docs, and CI.

- Phase cadence: N must pass before N+1 begins
- PR labels required: `phase:N`, `type:<category>`
- Required checks: lint, typecheck, tests, security-scan, verify_release, phase_gate

Detailed milestones will be added once the Phase 0–9 plan is provided.
