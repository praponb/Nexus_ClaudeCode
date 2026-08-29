#!/usr/bin/env bash
# Push this working tree to the Ubuntu deployment host over rsync.
# Run ON THE MAC. Companion to DEPLOY-UBUNTU.md section 3.
#
# Usage:
#   ./scripts/sync-to-server.sh                    # to the default host below
#   ./scripts/sync-to-server.sh prapon@10.0.0.5   # to somewhere else
#   ./scripts/sync-to-server.sh --dry-run          # show what would change
#   ./scripts/sync-to-server.sh --allow-dirty      # sync uncommitted work anyway
#
# WHY RSYNC AND NOT git clone: the repo is private, and this keeps GitHub
# credentials off the deployment host entirely -- there is no deploy key, no
# token, nothing to leak from a public-facing machine. The trade-off is that the
# server has no git history and no `git pull`.
#
# That trade-off is why this script REFUSES a dirty working tree unless you pass
# --allow-dirty. An uncommitted change that reaches the server is untraceable
# afterwards: nothing on either host records what it was. It also writes a
# DEPLOYED_COMMIT file into the transfer, so the server itself carries the SHA
# it is running instead of that fact living only in this Mac's working tree.
set -euo pipefail

cd "$(dirname "$0")/.."

DEST_DEFAULT="prapon@192.168.1.49:~/inventory/"
DRY_RUN=""
ALLOW_DIRTY=""
DEST=""

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN="--dry-run" ;;
    --allow-dirty) ALLOW_DIRTY="yes" ;;
    # Print the header block rather than a hardcoded line range, which silently
    # goes stale the first time this comment grows.
    -h|--help) awk 'NR>1 && /^set -euo pipefail/{exit} NR>1' "$0"; exit 0 ;;
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

GIT_SHA="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
GIT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
GIT_DIRTY="no"
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  GIT_DIRTY="yes"
fi

if [ "$GIT_DIRTY" = "yes" ] && [ -z "$ALLOW_DIRTY" ]; then
  echo "ERROR: the working tree has uncommitted changes." >&2
  echo >&2
  git status --short >&2
  echo >&2
  echo "       The server has no git history, so whatever is synced from an" >&2
  echo "       uncommitted tree cannot be traced back to anything afterwards." >&2
  echo "       Commit first, or pass --allow-dirty if you are deliberately" >&2
  echo "       iterating against the server." >&2
  exit 1
fi

# Written AFTER the check above, so generating it can never be what makes the
# tree dirty on the next run. It is gitignored for the same reason, and is not
# in EXCLUDES, so it ships.
cat > DEPLOYED_COMMIT <<EOF_STAMP
commit=${GIT_SHA}
branch=${GIT_BRANCH}
dirty=${GIT_DIRTY}
synced_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
synced_from=$(hostname -s) by $(id -un)
EOF_STAMP

if [ "$GIT_DIRTY" = "yes" ]; then
  echo "WARNING: syncing an uncommitted tree (--allow-dirty)."
  echo "         DEPLOYED_COMMIT will record dirty=yes, so the server at least"
  echo "         says it is running something that is not in git."
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
