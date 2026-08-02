#!/usr/bin/env bash
# Start the local development stack (docker compose) and wait for readiness.
set -euo pipefail

echo "==> Target environment: LOCAL DEVELOPMENT (docker compose)"
cd "$(dirname "$0")/.."

# ADR-006 bootstrap: the canonical compose/env files live under backend/
# (agent write scopes cannot create repo-root files). On a clean checkout,
# copy them into place so the documented bootstrap works unchanged.
if [ ! -f compose.yaml ] && [ -f backend/compose.yaml ]; then
  cp backend/compose.yaml compose.yaml
  echo "==> Created repo-root compose.yaml from backend/compose.yaml (canonical; ADR-006)."
fi
if [ ! -f .env ]; then
  if [ -f backend/.env ]; then
    cp backend/.env .env
    echo "==> Created .env from backend/.env (placeholders only; review values)."
  else
    echo "==> WARNING: no .env present and no backend/.env template found; compose defaults will be used."
  fi
fi

docker compose up -d --build

echo "==> Waiting for backend readiness at http://localhost:8000/api/v1/health/ready/ ..."
for attempt in $(seq 1 60); do
  if curl -fsS "http://localhost:8000/api/v1/health/ready/" >/dev/null 2>&1; then
    echo "==> Backend is ready. Frontend: http://localhost:3000  API: http://localhost:8000/api/v1/"
    exit 0
  fi
  sleep 2
done

echo "ERROR: backend did not become ready in time. Inspect: docker compose logs backend" >&2
exit 1
