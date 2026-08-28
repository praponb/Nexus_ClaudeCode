# scripts/

Operational scripts for the generated Asset Inventory application. Owned by the
Backend Developer agent (see [ASSUMPTIONS.md](../ASSUMPTIONS.md) for the
ownership rationale — the spec's concurrency rules don't explicitly assign this
directory).

For what each script does and when to run it, see
[ScriptUserGuide.md](ScriptUserGuide.md), or the summary table in
[UserManual.md](../UserManual.md#16-scripts-reference).

| File | Purpose |
|---|---|
| `install-root-files.sh` | One-time: install root `compose.yaml`/`.env` from `templates/` |
| `dev-up.sh` / `dev-down.sh` | Start / stop the Docker Compose stack |
| `migrate.sh` / `seed-dev.sh` | Apply migrations / seed demo data |
| `check.sh` | The six backend quality gates |
| `export-openapi.sh` | Regenerate `backend/openapi.json` |
| `backup.sh` / `restore.sh` | Database backup and restore (see `backend/docs/BACKUP_RESTORE.md`) |
| `com.praponb.inventory.backup.plist` | launchd agent that runs `backup.sh` daily |
| `templates/` | Canonical `compose.yaml` and `.env` for a fresh checkout |

`templates/` must stay in sync with the canonical `backend/compose.yaml` and
`backend/.env`. A stale template silently reintroduces old defaults on a new
checkout — that is how a missing `POSTGRES_SSLMODE` once crash-looped the stack.
