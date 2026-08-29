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
| `pull-backups.sh` | Copy the server's dumps to this Mac — the offsite half of `backup.sh` |
| `com.praponb.inventory.backup.plist` | launchd agent that runs `backup.sh` daily (macOS) |
| `com.praponb.inventory.pull-backups.plist` | launchd agent for `pull-backups.sh` (not installed by default) |
| `inventory-backup.service` / `.timer` | systemd equivalent for the Ubuntu host |
| `export-app-env.sh` | Extract the app-only subset of the root `.env` for deployment |
| `provision-ubuntu.sh` | Provision an Ubuntu 26.04 LTS host (Docker, cloudflared, ufw) |
| `sync-to-server.sh` | rsync this working tree to the deployment host (refuses a dirty tree) |
| `templates/` | Canonical `compose.yaml`, `.env`, and cloudflared ingress config |

`templates/` must stay in sync with the canonical `backend/compose.yaml` and
`backend/.env`. A stale template silently reintroduces old defaults on a new
checkout — that is how a missing `POSTGRES_SSLMODE` once crash-looped the stack.

`backup.sh` writes to the same disk it dumps, which is no defence against
drive failure. `pull-backups.sh` is the other half and runs on the Mac; a
backup that only exists on the machine it came from is not yet a backup.
