## ✅ Phase 4 Complete! Now let's document it and commit:

<function_calls>
<invoke name="run_terminal_cmd">
<parameter name="command">cd /Users/arcadio/avantis-telegram-bot && cat >> CHANGELOG.md << 'EOF'

## Phase 4: Persistence & Indexing — 2025-09-30

### Added
- **Database models** (Phase 4):
  - `SyncState`: Track indexer progress by block
  - `IndexedFill`: Store trade executions from chain events
  - `UserPosition`: Aggregate position state per user/symbol
- **Repositories**:
  - `positions_repo`: CRUD for positions and fills
  - `sync_state_repo`: Track indexer block progress
- **Positions cache**: Redis-backed 30s TTL cache for user positions
- **Avantis indexer**: Backfill + head-following event indexer
  - Configurable confirmations (default: 2 blocks)
  - 2000-block chunks for efficient syncing
  - Event decoder stub (TODO: wire real Avantis ABI)
- **Service integration**: `AvantisService.list_user_positions()`
- **Startup reconciliation**: `reconcile_nonces()` on boot
- **Makefile targets**:
  - `make indexer`: Run indexer daemon
  - `make backfill`: One-shot backfill

### Changed
- **Migration strategy**: Squashed to single baseline migration
- Fixed async/sync SQLite URL handling in Alembic
- Removed legacy broken migrations

### Fixed
- Migration chain conflicts resolved
- Model `__table_args__` to use string column names
- Alembic `migrations/env.py` now converts async URLs to sync

### Tests
- 8 new unit tests (100% passing)
  - positions_repo: 4 tests
  - sync_state_repo: 3 tests
  - indexer decoder stub: 1 test

### Documentation
- PHASE4_SUMMARY.md with implementation details
- Inline code docstrings
- TODO markers for real event decoding

### Technical Debt
- Event decoder uses stub (returns empty list)
- Needs real Avantis event ABI/topics
- User wallet binding (TG user → EOA) pending Phase 5

EOF
echo "✅ CHANGELOG updated"
