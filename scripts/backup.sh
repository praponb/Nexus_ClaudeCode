#!/usr/bin/env bash
# Create an encrypted-at-rest-ready PostgreSQL backup (NFR-012).
# Produces a gzipped pg_dump under backups/ (git-ignored). Encrypt at rest via
# your volume/KMS layer; store attachment media (backend_media volume) with the
# same schedule so a restore pairs DB + files.
set -euo pipefail

echo "==> Target environment: LOCAL/CI backup (docker compose postgres)"
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

POSTGRES_USER="${POSTGRES_USER:-asset_inventory}"
POSTGRES_DB="${POSTGRES_DB:-asset_inventory}"
STAMP="$(date -u +%Y%m%d-%H%M%SZ)"
DEST_DIR="backups"
DEST="${DEST_DIR}/asset-inventory-${STAMP}.sql.gz"

mkdir -p "${DEST_DIR}"

echo "==> Dumping database '${POSTGRES_DB}' to ${DEST}"
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
  | gzip -9 > "${DEST}"

echo "==> Backup complete: ${DEST} ($(du -h "${DEST}" | cut -f1))"
echo "==> Reminder: snapshot the attachment volume (backend_media) on the same schedule."
