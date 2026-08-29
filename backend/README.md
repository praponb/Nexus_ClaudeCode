# Asset Inventory — Backend

Django 6 + Django REST Framework + PostgreSQL backend for the Asset Inventory
Web Application. Implements the contracts in `detail-design-specification.md`
(Rev 1.2).

## Stack decisions and deviations (A-06 policy)

- **Django**: dependency range `>=5.2,<6.2`; the resolver selects **Django 6.0.x**
  (verified with 6.0.7 on Python 3.12–3.14), matching the stack baseline. If a
  deployment platform cannot run 6.0, pin the newest 5.2 LTS patch and record
  an ADR (`front-back-end-stack.md` §4 rule 4).
- **uv.lock**: generated and committed (`uv.lock`). The Docker build copies
  `uv.lock` and uses `uv sync --frozen` for reproducible, locked builds
  (resolving ADR-003/DEF-103).
- **Trailing slashes**: all API endpoints use DRF-standard trailing slashes
  (`/api/v1/assets/`, `/api/v1/auth/login/`, …). This is a deliberate contract
  clarification of design §11.3 (which omitted slashes).
- **compose.yaml / .env placement (ADR-006)**: the canonical files live
  at `backend/compose.yaml` and `backend/.env` (checked-in, placeholder-only
  template; agent write scopes cannot create repo-root files).
  `scripts/dev-up.sh` auto-copies both to the repo root when absent, so the
  documented clean-checkout bootstrap works.

## Layout

```
config/settings/{base,local,test,production}.py   env-driven settings; production fails fast
config/celery.py    Celery app (eager fallback in local/test per D-10)
apps/core           error envelope, pagination, permissions, throttling, idempotency,
                    middleware, health, seed + generate_volume commands
apps/accounts       custom User, roles, scopes, session auth, user admin (FR-027)
apps/reference_data categories, statuses, conditions, locations, departments, ...
apps/assets         Asset, AssetTagSequence, LifecycleEvent, Attachment, Note, services, API
apps/assignments    Assignment/Transfer/Reservation/ExceptionReport + workflow services
                    (incl. FR-014 retire/dispose/reopen)
apps/maintenance    MaintenanceRecord + services (FR-011/FR-012)
apps/stocktakes     StocktakeSession/Observation + reconciliation services (FR-022)
apps/bulk           ImportJob/ExportJob, CSV services, Celery tasks (FR-018/FR-019)
apps/approvals      ApprovalRequest + decision services (FR-024, Cycle 3)
apps/notifications  Notification/Preference + dispatch + due-reminder task (FR-023, Cycle 3)
apps/audit          AuditEvent (hash-chained, append-only) + query API (FR-025)
apps/reporting      SavedView, dashboard, data-quality queue, reports catalog (FR-021)
docs/               BACKUP_RESTORE.md (NFR-012)
tests/              pytest suite (needs PostgreSQL; skips cleanly without Django)
openapi.json        committed OpenAPI contract for frontend type generation
compose.yaml        canonical dev stack — auto-copied to repo root by scripts/dev-up.sh
.env                 canonical env reference (placeholders only) — auto-copied to repo root
mypy.ini            mypy + django-stubs plugin config (TOML cannot express it)
```

## Commands (from repo root, via scripts/)

```bash
./scripts/dev-up.sh       # bootstrap (auto-copies canonical root files), build + start stack
./scripts/migrate.sh      # apply migrations inside the backend container
./scripts/seed-dev.sh     # seed dev reference data, demo users, ~200 assets
./scripts/check.sh        # ruff format --check, ruff check, mypy, makemigrations --check,
                          # check --deploy (test settings), pytest
./scripts/export-openapi.sh   # regenerate backend/openapi.json
./scripts/backup.sh       # gzipped pg_dump into backups/ (NFR-012)
./scripts/restore.sh      # restore a backup (non-production guard)
./scripts/dev-down.sh
```

Locally without Docker (requires Python ≥3.12 + PostgreSQL):

```bash
cd backend
pip install -e '.[dev]'                  # or: uv sync --extra dev
export DJANGO_SETTINGS_MODULE=config.settings.local POSTGRES_HOST=localhost
python manage.py migrate
python manage.py seed_dev
python manage.py runserver 0.0.0.0:8000
```

Running `pytest` without compose: `config.settings.test` uses the `POSTGRES_*`
env vars when set (CI/compose), and otherwise falls back to the local
PostgreSQL role matching the current OS user against `localhost:5432`.

## Demo users (local dev only)

`seed_dev` creates `admin`, `manager`, `deptmgr`, `operator`, `employee`,
`auditor`. Passwords come from `SEED_DEMO_PASSWORD`; if unset, a random password
is generated and printed once. Note it only sets a password when it *creates* a
user, so re-running it will not reset an existing account. Never use these users
outside local dev.

`seed_dev` does not create a `viewer`; add one by hand to exercise that role.

On the deployed instance these seeded accounts are **deactivated** — only a
read-only `demo` account and a renamed administrator are active.

## Auth model

Session-cookie auth (`POST /api/v1/auth/login/`), CSRF cookie via
`GET /api/v1/auth/csrf/`, session bootstrap via `GET /api/v1/auth/me/`. Session
keys rotate on login. Local auth is disabled in production settings unless
`LOCAL_AUTH_ENABLED=true` **and** `LOCAL_AUTH_ALLOW_IN_PRODUCTION=true`
(design D-01). OIDC SSO is the documented production target (deferred).

Three controls guard the login, since on a public deployment it is the only gate:

- **Per-IP throttle** — `LoginThrottle`, 10/minute, HTTP 429 `RATE_LIMITED`.
  Identity comes from `apps/core/client_ip.py`, which trusts only
  `TRUSTED_CLIENT_IP_HEADER` then `REMOTE_ADDR` and **never** `X-Forwarded-For`
  (caller-supplied; keying on it allows a fresh bucket per request).
- **Per-account lockout** — `apps/core/login_guard.py`, counted per username in
  the cache so a distributed attack cannot sidestep the per-IP limit. Failures
  only, cleared on success, HTTP 429 `ACCOUNT_LOCKED`. Unknown usernames are
  counted too so the lockout cannot enumerate accounts. Unlock early with
  `login_guard.reset('<username>')`.
- **TOTP second factor** — `apps/accounts/mfa.py` (pyotp), required for roles in
  `MFA_REQUIRED_ROLES`. `POST /auth/login/` returns
  `{"mfa_required": true, "stage": "setup"|"verify"}` and **does not sign the
  user in**; the flow completes via `POST /auth/2fa/setup/`,
  `POST /auth/2fa/confirm/`, or `POST /auth/2fa/verify/` (which also accepts a
  single-use `recovery_code`). Between the two steps the caller holds only an
  unauthenticated session carrying a pending user id and a 5-minute deadline.

| Setting | Default | Purpose |
|---|---|---|
| `LOGIN_LOCKOUT_THRESHOLD` | `10` | Failed attempts per account before refusal |
| `LOGIN_LOCKOUT_WINDOW_SECONDS` | `900` | Window the count applies over |
| `LOGIN_LOCKOUT_EXEMPT_USERNAMES` | `demo` | Never lockable — shared public accounts |
| `MFA_REQUIRED_ROLES` | `system_admin` | Roles obliged to hold a second factor |
| `MFA_ISSUER` | `Asset Inventory` | Name shown in the authenticator app |
| `TRUSTED_CLIENT_IP_HEADER` | *(empty)* | META key the edge overwrites, e.g. `HTTP_CF_CONNECTING_IP` |
| `CACHE_URL` | `redis://localhost:6379/3` | Backs the throttle counters; **must be shared**, not per-process |

`config.settings.local` overrides the cache with `LocMemCache` so bare-metal
development needs no Redis; compose and production use Redis db 3 (dbs 1 and 2
are the Celery broker/results).

## API conventions

- Errors: `{"error": {code, message, field_errors, correlation_id, retryable}}`.
- Pagination: `?page=&page_size=` (default 25, max 100), envelope
  `{count, next, previous, results}`.
- Money: `{"amount": "1234.56", "currency": "USD"}` — never floats.
- Related resources: write with the related object's UUID string; read returns a
  compact object (`{"uuid": ..., ...}`).
- Optimistic concurrency: send `If-Match: <version>` or `version` in the PATCH
  body; mismatch → `409 VERSION_CONFLICT`.
- Correlation: send/expect `X-Correlation-ID` (UUIDv4); echoed on every response.
- Idempotency-Key (D-08): supported on asset create and all lifecycle/transition
  POSTs including retire/dispose/reopen. Same key + same payload within 24h
  replays the original response; key reuse with a different payload →
  `409 IDEMPOTENCY_KEY_REUSED`.
- Approval-gated actions (transfer/dispose with a `requires_approval` transition
  rule) return `202 {"approval": {...}}` and mutate nothing until approved.

## Cycle 3 additions

- **Reservations list** (`GET /reservations`, filters `status`/`asset`/
  `requester`/`overdue=true`) completing FR-010 overdue identification.
- **Retirement/disposal/reopen** (FR-014, J-5): BR-006 blockers →
  `409 DISPOSAL_BLOCKED` (manager/admin `force` override), disposed terminal,
  admin-only reopen with mandatory recorded justification; disposal history
  preserved (BR-003).
- **Approvals** (FR-024): `GET /approvals`,
  `POST /approvals/:uuid/{approve|reject|return}`; gating configured per
  transition rule (`requires_approval`), disableable via `APPROVALS_ENABLED=false`;
  separation of duties (`APPROVAL_SEPARATION_OF_DUTIES`, default on); immutable
  decisions (`409 APPROVAL_ALREADY_DECIDED`).
- **Notifications** (FR-023): in-app center (`GET /notifications`,
  `POST /notifications/:uuid/read`), preferences
  (`GET/PATCH /notifications/preferences`; mandatory compliance types cannot be
  muted), dedupe per event, email when SMTP configured (failures logged without
  content), daily warranty/maintenance reminder task.
- **Reports** (FR-021): `GET /reports` (14-report catalog),
  `GET /reports/:type` (scoped, finance-gated, date filters), audited CSV
  export with formula-injection mitigation.
- **User admin** (FR-027): `GET/PATCH /admin/users[/:uuid]` (roles, scopes,
  activation; `409 LAST_ADMIN` guard), and the audit query API
  `GET /admin/audit-events` (FR-025 read path, `audit.read` capability).
- **Archiving/retention** (FR-030): `legal_hold` flag (admin-only changes),
  `ARCHIVE_RETENTION_DAYS` config, no physical delete anywhere;
  `docs/BACKUP_RESTORE.md` + `scripts/backup.sh`/`restore.sh` (NFR-012).
- **Performance** (NFR-004/006): `generate_volume` command for planning-volume
  datasets; list endpoint query-count bounded by test (N+1 guard).
- **ADR-006 bootstrap**: `scripts/dev-up.sh` auto-copies canonical
  `backend/compose.yaml` + `backend/.env` to the repo root.

## Cycle 2 additions

- Lifecycle workflows (assign/return/transfer/reserve/checkout/exception),
  maintenance, attachments/notes/activity/QR label, stocktakes, CSV
  import/export, dashboard aggregates, data-quality queue v1, reference-data
  deactivate (BR-004), Idempotency-Key (D-08), rate limiting
  (`ScopedSimpleRateThrottle` — the previous `ScopedRateThrottle` subclasses
  silently no-oped).

## OpenAPI contract

`backend/openapi.json` is committed and used for frontend type generation.
`tests/test_openapi_contract.py` regenerates and fails once on drift (commit
the updated file and re-run); `scripts/export-openapi.sh` regenerates it from
the compose stack. The live schema is served at `/api/v1/schema/`.
