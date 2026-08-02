#!/usr/bin/env bash
# Stop the local development stack.
set -euo pipefail

echo "==> Target environment: LOCAL DEVELOPMENT (docker compose)"
cd "$(dirname "$0")/.."

# ADR-006 bootstrap: the canonical compose file lives under backend/ (agent
# write scopes cannot create repo-root files). Without this, `docker compose
# down` fails with "no configuration file provided: not found" on a clean
# checkout, or if dev-up.sh was never run yet -- mirrors dev-up.sh so both
# scripts work regardless of which one you run first.
if [ ! -f compose.yaml ] && [ -f backend/compose.yaml ]; then
  cp backend/compose.yaml compose.yaml
  echo "==> Created repo-root compose.yaml from backend/compose.yaml (canonical; ADR-006)."
fi

docker compose down --remove-orphans
echo "==> Stack stopped. (Volumes preserved; use 'docker compose down -v' to wipe data.)"
