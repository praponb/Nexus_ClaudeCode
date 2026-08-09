#!/usr/bin/env bash
# Restore a backup produced by scripts/backup.sh (NFR-012).
# Usage: ./scripts/restore.sh backups/asset-inventory-<stamp>.sql.gz
# WARNING: destructive — drops and recreates the database. Never run against
# production without a signed-off recovery plan (see backend/docs/BACKUP_RESTORE.md).
set -euo pipefail

echo "==> Target environment: LOCAL/CI restore (docker compose postgres)"
cd "$(dirname "$0")/.."

# ADR-006 bootstrap: the canonical compose file lives under backend/ (agent
# write scopes cannot create repo-root files). Without this, `docker compose`
# fails with "no configuration file provided: not found" on a clean checkout,
# or if dev-up.sh was never run yet -- mirrors dev-up.sh so every script works
# regardless of which one you run first.
if [ ! -f compose.yaml ] && [ -f backend/compose.yaml ]; then
  cp backend/compose.yaml compose.yaml
  echo "==> Created repo-root compose.yaml from backend/compose.yaml (canonical; ADR-006)."
fi

if [ $# -ne 1 ] || [ ! -f "$1" ]; then
  echo "Usage: $0 <backup-file.sql.gz>" >&2
  exit 2
fi

if [ "${APP_ENV:-local}" = "production" ]; then
  echo "ERROR: refusing to restore with APP_ENV=production." >&2
  exit 1
fi

POSTGRES_USER="${POSTGRES_USER:-asset_inventory}"
POSTGRES_DB="${POSTGRES_DB:-asset_inventory}"

echo "==> Restoring '$1' into database '${POSTGRES_DB}' (drop + recreate)"
docker compose exec -T postgres psql -U "${POSTGRES_USER}" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();" >/dev/null 2>&1 || true
docker compose exec -T postgres dropdb -U "${POSTGRES_USER}" --if-exists "${POSTGRES_DB}"
docker compose exec -T postgres createdb -U "${POSTGRES_USER}" "${POSTGRES_DB}"
gunzip -c "$1" | docker compose exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -v ON_ERROR_STOP=1 --quiet

echo "==> Restore complete. Apply any pending migrations next: ./scripts/migrate.sh"
