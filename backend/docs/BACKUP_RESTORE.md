# Backup & Restore Procedure (NFR-012)

**Interim targets:** RTO ≤ 8 hours, RPO ≤ 24 hours.

## What is backed up

| Data | Mechanism | Schedule |
|---|---|---|
| PostgreSQL (all business data, audit chain, idempotency keys, jobs) | `scripts/backup.sh` → gzipped `pg_dump` | Daily (RPO ≤ 24h) |
| Attachment files (`backend_media` volume) | `scripts/backup.sh` → `…-media-<stamp>.tar.gz`, same run, matching timestamp | Daily, with the DB |

Backups must be encrypted at rest (KMS-managed volume or S3 SSE) and copied to
a second failure domain. Local dev backups land in `backups/` (git-ignored).

## Create a backup

```bash
./scripts/backup.sh
# -> backups/asset-inventory-<UTC timestamp>.sql.gz          (database)
# -> backups/asset-inventory-media-<UTC timestamp>.tar.gz    (attachments)
```

Both artefacts share one timestamp so a restore can pair them without guessing.
A database dump on its own is a half backup: restoring it leaves every
attachment row pointing at a file that is not there.

`backup.sh` prunes each kind to the newest `BACKUP_KEEP` (default 48) after
every run — without that, scheduling it would grow the directory without bound.

### Scheduled backups — production (Linux, systemd)

Production runs on Ubuntu since 2026-08-29; this is the live schedule:

```bash
sudo cp scripts/inventory-backup.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now inventory-backup.timer
systemctl list-timers inventory-backup.timer
```

Daily at 03:15 with `Persistent=true`, so a host that was off at 03:15 runs the
backup at next boot. `BACKUP_KEEP=14`. Logs go to the journal:
`journalctl -u inventory-backup.service`.

### Scheduled backups — macOS (development / standby only)

Installed as a user LaunchAgent, so it needs no root:

```bash
cp scripts/com.praponb.inventory.backup.plist ~/Library/LaunchAgents/
launchctl enable gui/$(id -u)/com.praponb.inventory.backup
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.praponb.inventory.backup.plist
```

> The `launchctl enable` line matters: this job is currently **disabled** on the
> standby Mac, and `bootstrap` silently does nothing against a disabled job.

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
4. Restore the attachments from the tarball with the matching timestamp. `-u root`
   is required — the volume is root-owned while the container runs as `appuser`:
   ```bash
   docker compose exec -T -u root backend sh -c 'tar -xzf - -C /app/media' \
     < backups/asset-inventory-media-<stamp>.tar.gz
   ```
5. Restart: `docker compose start backend celery-worker celery-beat`.
6. Verify (drill checklist):
   - `curl -fsS -H 'Host: inventory.praponb.com' -H 'X-Forwarded-Proto: https' \
       http://127.0.0.1:8000/api/v1/health/ready/`
     (both headers are needed against a production-settings stack: it answers
     only to its real hostname, and `SECURE_SSL_REDIRECT` 301s plain HTTP)
   - Sign in as a demo user; open an asset detail page and its history feed.
   - Download one attachment and one CSV export.
   - Audit chain integrity: `python manage.py shell -c \
     "from apps.audit.services import verify_chain; print(verify_chain())"`
     inside the backend container.

     > **This currently prints `False`, and that is not a restore failure.**
     > Seven pre-existing `auth.*` events (ids 403-409) carry a hash that does
     > not recompute, because their actor was deleted: `AuditEvent.actor` is
     > `on_delete=SET_NULL` and the payload hashes `actor.uuid`, so removing a
     > user invalidates that user's rows while every `prev_hash` link stays
     > intact. Compare the result against the source system instead of expecting
     > `True` — if the source says `False` and the restore says `False`, the
     > restore is faithful. `python manage.py audit_chain_report` (read-only)
     > prints which rows and why. Do not run `reseal_chain()` to make this
     > green: it would overwrite the evidence. See
     > `SESSION-2026-08-29-ISSUES.md` §2.2.
7. Record drill date, dataset size, and elapsed time (target ≤ 8h RTO).

## Rollback after a failed deploy

Previous image + the most recent backup. Migrations are backward-compatible
within a release, so a code rollback does not require a data restore unless
stated in the release notes.

## Notes

- The audit log is hash-chained; `verify_chain()` after restore is the
  tamper-evidence check (FR-025). It is currently `False` for a known,
  pre-existing reason — a deleted actor, not tampering — see the drill note
  above before treating that as a restore problem. `audit_chain_report` is the
  command that tells the two apart.
- Retention of archived records is configured via `ARCHIVE_RETENTION_DAYS`
  (default ~7 years). No operational function physically deletes business
  records (FR-030); assets under `legal_hold` must never be purged by any
  future retention job.
