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
