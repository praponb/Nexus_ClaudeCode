# Backup & Restore Procedure (NFR-012)

**Interim targets:** RTO ≤ 8 hours, RPO ≤ 24 hours.

## What is backed up

| Data | Mechanism | Schedule |
|---|---|---|
| PostgreSQL (all business data, audit chain, idempotency keys, jobs) | `scripts/backup.sh` → gzipped `pg_dump` | Daily (RPO ≤ 24h) |
| Attachment files (`backend_media` volume / S3 bucket in production) | Volume snapshot / bucket versioning | Same schedule as DB |

Backups must be encrypted at rest (KMS-managed volume or S3 SSE) and copied to
a second failure domain. Local dev backups land in `backups/` (git-ignored).

## Create a backup

```bash
./scripts/backup.sh
# -> backups/asset-inventory-<UTC timestamp>.sql.gz
```

`backup.sh` prunes to the newest `BACKUP_KEEP` dumps (default 48) after each
run — without that, scheduling it would grow the directory without bound.

### Scheduled backups (macOS)

Installed as a user LaunchAgent, so it needs no root:

```bash
cp scripts/com.praponb.inventory.backup.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.praponb.inventory.backup.plist
```

Runs daily (`StartInterval 86400`) with `BACKUP_KEEP=14`, plus once at load so
a machine that was asleep is not left a full day behind. Log:
`~/Library/Logs/com.praponb.inventory.backup.log`.

Two things that will silently break it if changed: `PATH` must be set
explicitly in the plist (launchd gives a job a minimal `PATH` with no `docker`),
and `KeepAlive` must stay absent (this is a periodic task, not a daemon — with
`KeepAlive` launchd would restart it the moment it exits and back up in a loop).

> **Verify a backup, don't assume it.** Restore into a scratch database and
> compare row counts, rather than pointing `restore.sh` at the live one:
>
> ```bash
> docker compose exec -T postgres psql -U asset_inventory -d postgres \
>   -c "CREATE DATABASE restore_probe;"
> gunzip -c backups/<file>.sql.gz | \
>   docker compose exec -T postgres psql -q -U asset_inventory -d restore_probe
> docker compose exec -T postgres psql -tA -U asset_inventory -d restore_probe \
>   -c "SELECT count(*) FROM assets_asset;"
> docker compose exec -T postgres psql -U asset_inventory -d postgres \
>   -c "DROP DATABASE restore_probe;"
> ```

## Restore (documented drill — perform once per release)

1. Stop writers: `docker compose stop backend celery-worker celery-beat`.
2. Run: `./scripts/restore.sh backups/asset-inventory-<stamp>.sql.gz`
   (refuses to run with `APP_ENV=production`).
3. Apply pending migrations: `./scripts/migrate.sh`.
4. Restore the attachment volume snapshot taken at the same time.
5. Restart: `docker compose start backend celery-worker celery-beat`.
6. Verify (drill checklist):
   - `curl -fsS http://localhost:8000/api/v1/health/ready/`
   - Sign in as a demo user; open an asset detail page and its history feed.
   - Download one attachment and one CSV export.
   - Audit chain integrity: `python manage.py shell -c \
     "from apps.audit.services import verify_chain; print(verify_chain())"`
     inside the backend container — must print `True`.
7. Record drill date, dataset size, and elapsed time (target ≤ 8h RTO).

## Rollback after a failed deploy

Previous image + the most recent backup. Migrations are backward-compatible
within a release, so a code rollback does not require a data restore unless
stated in the release notes.

## Notes

- The audit log is hash-chained; a successful `verify_chain()` after restore
  is the tamper-evidence check (FR-025).
- Retention of archived records is configured via `ARCHIVE_RETENTION_DAYS`
  (default ~7 years). No operational function physically deletes business
  records (FR-030); assets under `legal_hold` must never be purged by any
  future retention job.
