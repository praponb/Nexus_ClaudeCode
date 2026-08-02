#!/usr/bin/env bash
# Regenerate backend/openapi.json from the running backend container.
set -euo pipefail

echo "==> Exporting OpenAPI schema (backend/openapi.json)"
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

docker compose exec -T -e DJANGO_SETTINGS_MODULE=config.settings.test backend \
  python manage.py spectacular --file openapi.json --validate
echo "==> Wrote backend/openapi.json"
