#!/usr/bin/env bash
# Install root-level compose.yaml and .env from scripts/templates/.
# Idempotent: never overwrites existing root files.
# (These files live at the repository root, which is outside the backend
# agent's write scope, so they are shipped as templates + this installer.)
set -euo pipefail

echo "==> Target environment: LOCAL DEVELOPMENT (repository root files)"
cd "$(dirname "$0")/.."

install_file() {
  local source="$1" target="$2"
  if [ -e "$target" ]; then
    echo "==> $target already exists; leaving it untouched."
  else
    cp "$source" "$target"
    echo "==> Installed $target"
  fi
}

install_file scripts/templates/compose.yaml compose.yaml
install_file scripts/templates/.env .env

echo "==> Done. Review values, then: ./scripts/dev-up.sh"
