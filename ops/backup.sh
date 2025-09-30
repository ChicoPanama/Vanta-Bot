#!/usr/bin/env bash
# Database backup script (Phase 9)
set -euo pipefail

STAMP=$(date +"%Y%m%d_%H%M%S")
OUT="backups/${STAMP}"
mkdir -p "$OUT"

echo "[*] Backing up database to ${OUT}"

PGPASSWORD="${PG_PASSWORD:-vanta}" pg_dump \
  -h "${PG_HOST:-localhost}" \
  -p "${PG_PORT:-5432}" \
  -U "${PG_USER:-vanta}" \
  -d "${PG_DB:-vanta}" \
  -Fc > "${OUT}/db.dump"

echo "✅ Backup complete: ${OUT}/db.dump"
