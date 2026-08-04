# Scripts User Guide

Operational scripts for running, checking, and maintaining the Asset
Inventory app locally (Docker Compose) and in CI. All scripts:

- live in `scripts/` and are meant to be run from anywhere in the repo
  (each one `cd`s to the repo root itself via `cd "$(dirname "$0")/.."`)
- use `set -euo pipefail` — they stop on the first error
- print a `==> Target environment: ...` line so it's always clear what
  they're about to touch (local Docker Compose vs. something else)

## Quick start (fresh checkout)

```bash
./scripts/install-root-files.sh   # 1. create root compose.yaml + .env from templates
#    review/edit .env now if you need non-default values
./scripts/dev-up.sh               # 2. build + start the stack, wait for readiness
./scripts/seed-dev.sh             # 3. load demo/reference data
```

After that, `http://localhost:3000` is the app and
`http://localhost:8000/api/v1/` is the API.

---

## Script reference

### `install-root-files.sh`
Copies `scripts/templates/compose.yaml` and `scripts/templates/.env` to
the repository root as `compose.yaml` and `.env`, **only if those files
don't already exist** — it never overwrites. Run this once on a fresh
checkout, before `dev-up.sh`.

```bash
./scripts/install-root-files.sh
```

> **Note:** the templates in `scripts/templates/` are the plain local-dev
> defaults (`DJANGO_SETTINGS_MODULE=config.settings.local`, `DJANGO_DEBUG=true`,
> frontend build `target: dev`, no `POSTGRES_SSLMODE`). If you've since
> hardened your root `compose.yaml`/`.env` for a real deployment (production
> Django settings, `target: production`, Cloudflare Access, etc.), **do not
> delete and re-run this script** — since it only acts when the root files
> are missing, deleting them and re-running would silently regenerate the
> insecure dev-mode versions. Treat the templates as a starting point for a
> brand-new checkout only, not a way to reset an existing deployment.

### `dev-up.sh`
Starts the full stack (`docker compose up -d --build`) and polls
`http://localhost:8000/api/v1/health/ready/` (up to 60 × 2s = 2 minutes)
until the backend answers. Also has the same bootstrap fallback as
`install-root-files.sh` (copies `backend/compose.yaml` → `compose.yaml`
and `backend/.env` → `.env` if they're missing), so it works standalone
even if you skip `install-root-files.sh`.

```bash
./scripts/dev-up.sh
```

Exits non-zero with a hint to check `docker compose logs backend` if the
backend never becomes ready.

### `dev-down.sh`
Stops the stack (`docker compose down --remove-orphans`). Named volumes
(`postgres_data`, `backend_media`) are preserved — your data survives.

```bash
./scripts/dev-down.sh
docker compose down -v   # add -v yourself if you actually want to wipe data
```

### `seed-dev.sh`
Runs `manage.py seed_dev` inside the `backend` container — loads
non-sensitive demo/reference data. Idempotent (safe to run repeatedly).
Any arguments are passed through to the management command.

```bash
./scripts/seed-dev.sh
```

Demo user passwords come from `SEED_DEMO_PASSWORD` in `.env`; if left
empty, the command prints a generated password once.

### `migrate.sh`
Runs `manage.py migrate` inside the `backend` container. Arguments pass
through, so you can target a specific app/migration.

```bash
./scripts/migrate.sh
./scripts/migrate.sh assets 0012   # example: migrate one app to a specific migration
```

### `check.sh`
Runs all backend quality gates in order: `ruff format --check`,
`ruff check`, `mypy`, `makemigrations --check --dry-run`,
`check --deploy`, `pytest`. Stops at the first failure (numbered
`[1/6]`–`[6/6]` progress lines).

```bash
./scripts/check.sh
```

By default it runs each step inside the `backend` container via
`docker compose exec`. Set `CHECK_MODE=local` to run directly on the host
instead (requires `pip install -e '.[dev]'` in `backend/`):

```bash
CHECK_MODE=local ./scripts/check.sh
```

### `export-openapi.sh`
Regenerates `backend/openapi.json` from the running backend
(`manage.py spectacular --file openapi.json --validate`). Run this after
changing any API views/serializers so the committed schema stays current.

```bash
./scripts/export-openapi.sh
```

### `backup.sh`
Dumps the Postgres database with `pg_dump`, gzips it, and writes it to
`backups/<timestamp>.sql.gz` (git-ignored directory, created if needed).

```bash
./scripts/backup.sh
```

This only backs up the database. Attachment files live in the
`backend_media` Docker volume and are **not** included — snapshot that
volume on the same schedule if you need a full recovery point. See
`backend/docs/BACKUP_RESTORE.md` for the full backup/restore plan.

### `restore.sh`
**Destructive.** Drops and recreates the database, then restores it from
a `backup.sh`-produced file. Refuses to run if `APP_ENV=production`, as a
safety guard against pointing this at a live environment.

```bash
./scripts/restore.sh backups/asset-inventory-20260803-120000Z.sql.gz
```

After restoring, run `./scripts/migrate.sh` to apply any migrations added
since the backup was taken. Read `backend/docs/BACKUP_RESTORE.md` before
using this for anything that matters — there is no confirmation prompt.

---

## Templates (`scripts/templates/`)

| File | Purpose |
|---|---|
| `compose.yaml` | Canonical Docker Compose stack definition (postgres, redis, backend, celery-worker, celery-beat, frontend). This is the source of truth per ADR-006 — the copy at the repo root (`compose.yaml`) should be treated as derived from this, under `backend/compose.yaml`. |
| `.env` | Canonical environment variable reference with safe local-dev placeholder values and comments explaining each section. |

These exist under `scripts/templates/` (rather than shipping as
`.env.example`/`compose.yaml` directly at the repo root) because of how
this project's write ownership is scoped — see the comments at the top of
each file for the full rationale. `backend/compose.yaml` and
`backend/.env` are equivalent canonical copies for the same reason.

## Common pattern: the ADR-006 bootstrap

Every script except `install-root-files.sh` itself contains this block
near the top:

```bash
if [ ! -f compose.yaml ] && [ -f backend/compose.yaml ]; then
  cp backend/compose.yaml compose.yaml
  echo "==> Created repo-root compose.yaml from backend/compose.yaml (canonical; ADR-006)."
fi
```

This means **every script works standalone** on a clean checkout, in any
order — you don't strictly have to run `install-root-files.sh` or
`dev-up.sh` first. The tradeoff is the same one noted above: this only
creates the file when it's *missing*, never overwrites an existing one,
so a hardened root `compose.yaml` you've customized for a real deployment
is safe from being clobbered by routinely running these scripts.
