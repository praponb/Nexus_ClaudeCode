#!/usr/bin/env bash
# Push this working tree to the Ubuntu deployment host over rsync.
# Run ON THE MAC. Companion to DEPLOY-UBUNTU.md section 3.
#
# Usage:
#   ./scripts/sync-to-server.sh                    # to the default host below
#   ./scripts/sync-to-server.sh prapon@10.0.0.5   # to somewhere else
#   ./scripts/sync-to-server.sh --dry-run          # show what would change
#
# WHY RSYNC AND NOT git clone: the repo is private, and this keeps GitHub
# credentials off the deployment host entirely -- there is no deploy key, no
# token, nothing to leak from a public-facing machine. The trade-off is that the
# server has no git history and no `git pull`: THIS MAC IS THE SOURCE OF TRUTH
# for what is deployed. Commit before syncing, or you will not be able to tell
# later what is actually running out there.
set -euo pipefail

cd "$(dirname "$0")/.."

DEST_DEFAULT="prapon@192.168.1.49:~/inventory/"
DRY_RUN=""
DEST=""

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN="--dry-run" ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    -*) echo "ERROR: unknown option '$arg'" >&2; exit 2 ;;
    *) DEST="$arg" ;;
  esac
done

DEST="${DEST:-$DEST_DEFAULT}"
# Accept a bare "user@host" and append the standard path, so callers need not
# repeat it. Anything already carrying a colon (host:path) or a slash (a local
# directory, used by the tests) is taken exactly as given.
case "$DEST" in
  *:*) ;;
  */*) ;;
  *) DEST="${DEST}:~/inventory/" ;;
esac

# The exclusions below are not tidiness -- .venv and node_modules hold compiled
# arm64 binaries from this Mac. Shipping them to an amd64 server would place
# broken native modules where the Docker build expects to create working ones.
# Both are regenerated inside the images, so they must never cross.
#
# .env is excluded for correctness: the server has its own, written by
# scripts/export-app-env.sh, holding only the app subset. The Mac's .env also
# carries the orchestrator's paid API keys and must not land on a web host.
#
# backups/ is excluded because dumps are shipped deliberately at cutover.
#
# rsync does not delete excluded paths on the receiver, so --delete prunes stale
# files without ever touching the server's own .env or backups/.
EXCLUDES=(
  --exclude '.git/'
  --exclude '.venv/'
  --exclude 'node_modules/'
  --exclude '.nuxt/'
  --exclude '.output/'
  --exclude '__pycache__/'
  --exclude '.mypy_cache/'
  --exclude '.pytest_cache/'
  --exclude '.ruff_cache/'
  --exclude '.DS_Store'
  --exclude '.env'
  --exclude 'app.env'
  --exclude 'backups/'
  --exclude 'runs/'
)

if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  echo "NOTE: working tree has uncommitted changes. They WILL be synced."
  echo "      That is fine for iterating, but commit before a real deploy so the"
  echo "      server's contents can be traced back to a commit."
  echo
fi

echo "==> Syncing $(pwd)"
echo "         -> ${DEST}"
[ -n "$DRY_RUN" ] && echo "    (dry run -- nothing will be written)"
echo

# macOS ships openrsync (advertises "rsync 2.6.9 compatible", protocol 29),
# which does NOT understand rsync 3.x flags such as --info=. Stick to options
# that exist in both, and use a newer rsync only if one is actually installed.
RSYNC_BIN="$(command -v rsync)"
for candidate in /opt/homebrew/bin/rsync /usr/local/bin/rsync; do
  if [ -x "$candidate" ] && "$candidate" --version 2>/dev/null | head -1 | grep -qv 'openrsync'; then
    RSYNC_BIN="$candidate"
    break
  fi
done

"$RSYNC_BIN" -az --delete --stats \
  $DRY_RUN "${EXCLUDES[@]}" \
  ./ "$DEST"

echo
echo "==> Sync complete."
if [ -z "$DRY_RUN" ]; then
cat <<'EOF'
    On the server:
      cd ~/inventory
      docker compose build && docker compose up -d
      ./scripts/migrate.sh
    Back up BEFORE deploying over a running stack:  ./scripts/backup.sh
EOF
fi
