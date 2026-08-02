#!/usr/bin/env bash
# Run all backend quality gates. Default: inside the compose backend container.
# Set CHECK_MODE=local to run on the host instead (requires pip install -e '.[dev]').
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

run() {
  if [ "$MODE" = "local" ]; then
    (cd backend && "$@")
  else
    docker compose exec -T -e DJANGO_SETTINGS_MODULE=config.settings.test backend "$@"
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
