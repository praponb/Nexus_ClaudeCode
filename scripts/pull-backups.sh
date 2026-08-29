#!/usr/bin/env bash
# Copy the server's backups to a second machine (NFR-012).
# Run ON THE MAC. Companion to scripts/backup.sh, which runs on the server.
#
# Usage:
#   ./scripts/pull-backups.sh                       # from the default host below
#   ./scripts/pull-backups.sh prapon@10.0.0.5      # from somewhere else
#   ./scripts/pull-backups.sh --dry-run             # show what would be copied
#
# WHY THIS EXISTS: backup.sh writes into ~/inventory/backups on the server, which
# is the same physical disk as the Postgres volume it is dumping. That covers a
# bad migration or an accidental delete; it covers nothing at all if the drive
# fails. A backup that dies with its source is not a backup. This pulls the dumps
# to a second machine, which is the part that was missing.
#
# BACKUP_MIRROR_DIR, if set, gets a second copy -- the same pattern the
# Jobs4Dent LaunchAgent uses for iCloud Drive. Treat a cloud mirror as a mirror,
# not the primary: with "Optimize Mac Storage" macOS may evict the local file and
# leave a placeholder, so recovery must never depend on a download completing.
set -euo pipefail

cd "$(dirname "$0")/.."

SRC_DEFAULT="prapon@192.168.1.49"
DEST_DIR="${BACKUP_PULL_DIR:-$HOME/inventory-backups}"
KEEP="${BACKUP_PULL_KEEP:-30}"
DRY_RUN=""
SRC=""

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN="--dry-run" ;;
    -h|--help) awk 'NR>1 && /^set -euo pipefail/{exit} NR>1' "$0"; exit 0 ;;
    -*) echo "ERROR: unknown option '$arg'" >&2; exit 2 ;;
    *) SRC="$arg" ;;
  esac
done
SRC="${SRC:-$SRC_DEFAULT}"
case "$SRC" in
  *:*) ;;
  *) SRC="${SRC}:~/inventory/backups/" ;;
esac

mkdir -p "$DEST_DIR"

echo "==> Pulling $SRC"
echo "         -> $DEST_DIR"
[ -n "$DRY_RUN" ] && echo "    (dry run -- nothing will be written)"

# macOS ships openrsync (protocol 29), which rejects rsync 3.x flags. Same
# constraint as sync-to-server.sh; keep the options common to both.
RSYNC_BIN="$(command -v rsync)"
for candidate in /opt/homebrew/bin/rsync /usr/local/bin/rsync; do
  if [ -x "$candidate" ] && "$candidate" --version 2>/dev/null | head -1 | grep -qv 'openrsync'; then
    RSYNC_BIN="$candidate"
    break
  fi
done

# Deliberately NOT --delete. The server prunes to BACKUP_KEEP=14; if this copy
# mirrored that pruning it would inherit the server's retention window and stop
# being a longer-lived second line of defence.
"$RSYNC_BIN" -az --stats $DRY_RUN "$SRC" "$DEST_DIR/"

if [ -n "$DRY_RUN" ]; then
  exit 0
fi

# A pull that silently copies nothing is worse than a failure: it looks fine.
NEWEST="$(ls -1t "$DEST_DIR"/asset-inventory-*.sql.gz 2>/dev/null | head -1 || true)"
if [ -z "$NEWEST" ]; then
  echo "ERROR: no database dump present after the pull. Nothing is backed up here." >&2
  exit 1
fi
if ! gzip -t "$NEWEST" 2>/dev/null; then
  echo "ERROR: newest dump $NEWEST is not a valid gzip stream." >&2
  exit 1
fi
echo "==> Newest dump: $(basename "$NEWEST") ($(du -h "$NEWEST" | cut -f1)), gzip OK"

if [ -n "${BACKUP_MIRROR_DIR:-}" ]; then
  mkdir -p "$BACKUP_MIRROR_DIR"
  echo "==> Mirroring to $BACKUP_MIRROR_DIR"
  "$RSYNC_BIN" -a "$DEST_DIR/" "$BACKUP_MIRROR_DIR/"
fi

# Retention. Keep the newest KEEP of each kind; without this the directory grows
# without bound once this runs on a schedule.
PRUNED=0
prune_glob() {
  while IFS= read -r stale; do
    [ -n "$stale" ] || continue
    rm -f "$stale"
    PRUNED=$((PRUNED + 1))
  done <<EOF_PRUNE
$(ls -1t $1 2>/dev/null | tail -n "+$((KEEP + 1))")
EOF_PRUNE
}
prune_glob "$DEST_DIR/asset-inventory-*.sql.gz"
prune_glob "$DEST_DIR/asset-inventory-media-*.tar.gz"
if [ "$PRUNED" -gt 0 ]; then
  echo "==> Pruned $PRUNED local copy/copies beyond the newest $KEEP."
fi

echo "==> Pull complete: $(ls -1 "$DEST_DIR"/asset-inventory-*.sql.gz 2>/dev/null | wc -l | tr -d ' ') dump(s) held locally."
