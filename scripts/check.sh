#!/usr/bin/env bash
# Run all backend quality gates.
#
# CHECK_MODE=compose (default) runs them in Docker. It prefers `exec` into the
# running backend container, but that container only carries ruff/mypy/pytest
# when it was built from the `dev` stage -- deploy with
# BACKEND_BUILD_TARGET=production and it is a gunicorn image with no dev tools.
# So it falls back to a one-off container built from the dev stage, joined to
# the running stack's network. CHECK_MODE=local runs on the host instead
# (requires pip install -e '.[dev]' under backend/).
set -euo pipefail

echo "==> Target environment: CI/LOCAL quality gates (backend)"
cd "$(dirname "$0")/.."

# ADR-006 bootstrap: the canonical compose file lives under backend/ (agent
# write scopes cannot create repo-root files). Without this, `docker compose`
# fails with "no configuration file provided: not found" on a clean checkout,
# or if dev-up.sh was never run yet -- mirrors dev-up.sh so every script works
# regardless of which one you run first. Harmless no-op in CHECK_MODE=local.
if [ ! -f compose.yaml ] && [ -f backend/compose.yaml ]; then
  cp backend/compose.yaml compose.yaml
  echo "==> Created repo-root compose.yaml from backend/compose.yaml (canonical; ADR-006)."
fi

MODE="${CHECK_MODE:-compose}"
DEV_IMAGE="${CHECK_DEV_IMAGE:-asset-inventory-backend-dev}"
RUNNER=""   # set below for compose mode; unused (but must be defined) under set -u

# POSTGRES_* for the one-off container; .env is the same source compose reads.
if [ -f .env ]; then
  while IFS='=' read -r key value; do
    case "$key" in POSTGRES_DB|POSTGRES_USER|POSTGRES_PASSWORD) export "$key=$value" ;; esac
  done < <(grep -E '^POSTGRES_(DB|USER|PASSWORD)=' .env || true)
fi

backend_has_dev_tools() {
  docker compose exec -T backend sh -c 'command -v ruff >/dev/null 2>&1' 2>/dev/null
}

one_off_run() {
  if ! docker image inspect "$DEV_IMAGE" >/dev/null 2>&1; then
    echo "==> Building $DEV_IMAGE (dev stage) for the quality gates ..."
    docker build --target dev -t "$DEV_IMAGE" ./backend >/dev/null
  fi
  local pg network
  pg="$(docker compose ps -q postgres)"
  if [ -z "$pg" ]; then
    echo "ERROR: postgres is not running; pytest needs it. Run ./scripts/dev-up.sh first." >&2
    exit 1
  fi
  network="$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}' "$pg")"
  # Mounted at /w, not /app: the image keeps its virtualenv at /app/.venv, and
  # mounting over /app would hide the very tools we came here to run.
  docker run --rm --network "$network" \
    -v "$PWD/backend:/w" -w /w \
    -e DJANGO_SETTINGS_MODULE=config.settings.test \
    -e POSTGRES_HOST=postgres -e POSTGRES_PORT=5432 \
    -e "POSTGRES_DB=${POSTGRES_DB:-asset_inventory}" \
    -e "POSTGRES_USER=${POSTGRES_USER:-asset_inventory}" \
    -e "POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-local-dev-password}" \
    -e POSTGRES_SSLMODE=disable \
    "$DEV_IMAGE" "$@"
}

if [ "$MODE" = "compose" ]; then
  if backend_has_dev_tools; then
    RUNNER=exec
  else
    RUNNER=one-off
    echo "==> Running backend container has no dev tools; using a one-off dev-stage container."
  fi
fi

run() {
  if [ "$MODE" = "local" ]; then
    (cd backend && "$@")
  elif [ "$RUNNER" = "exec" ]; then
    docker compose exec -T -e DJANGO_SETTINGS_MODULE=config.settings.test backend "$@"
  else
    one_off_run "$@"
  fi
}

echo "==> [1/6] ruff format --check"
run ruff format --check .

echo "==> [2/6] ruff check"
run ruff check .

echo "==> [3/6] mypy"
run mypy apps config manage.py

echo "==> [4/6] makemigrations --check --dry-run"
run python manage.py makemigrations --check --dry-run

echo "==> [5/6] check --deploy (safe test settings)"
run python manage.py check --deploy

echo "==> [6/6] pytest"
run pytest

echo "==> All backend quality gates passed."
