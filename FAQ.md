# FAQ: Asset Inventory Application

This FAQ covers the **generated Asset Inventory web application** (`frontend/`
+ `backend/`) — the thing you actually log into and use. It's separate from
`agentic_builder` (`src/`), the orchestrator tool that generated it; if
you're looking for orchestrator docs, see the root [README.md](README.md)
instead.

For deep technical detail beyond this FAQ, see:
- [`detail-design-specification.md`](detail-design-specification.md) — full functional/non-functional spec, API contracts, data model
- [`backend/README.md`](backend/README.md) / [`frontend/README.md`](frontend/README.md) — stack-specific setup and architecture notes
- [`runs/<run-id>/final-report.md`](runs/) — requirement-by-requirement implementation and test status

---

## What is this?

A full-lifecycle company asset inventory system: register assets, assign
them to people or locations, track maintenance/warranty, run stocktakes,
approve controlled actions, and report on all of it — with role-based
permissions and a full audit trail.

- **Backend**: Django 6 + Django REST Framework + PostgreSQL (+ Celery, run
  in eager/synchronous mode for local dev so Redis isn't required)
- **Frontend**: Nuxt 4 + Vue 3 + TypeScript, dark theme, WCAG 2.2 AA target

## How do I run it?

### Option A: Docker (the documented default)

```bash
./scripts/install-root-files.sh   # one-time: installs root compose.yaml/.env
./scripts/dev-up.sh               # builds + starts postgres, redis, backend, celery, frontend
```

Then visit http://localhost:3000. Requires Docker Desktop running.

### Option B: Local dev (no Docker)

Useful if Docker isn't available. Needs Python ≥3.12, Node ≥20, and a local
PostgreSQL instance.

**Backend:**
```bash
cd backend
python3 -m venv .venv && ./.venv/bin/pip install -e '.[dev]'
# create a Postgres role + db matching backend/.env, then:
export DJANGO_SETTINGS_MODULE=config.settings.local
export POSTGRES_HOST=localhost POSTGRES_DB=asset_inventory POSTGRES_USER=asset_inventory POSTGRES_PASSWORD=local-dev-password
export DJANGO_SECRET_KEY=local-dev-only-not-a-secret CELERY_TASK_ALWAYS_EAGER=true
./.venv/bin/python3 manage.py migrate
./.venv/bin/python3 manage.py seed_dev
./.venv/bin/python3 manage.py runserver 0.0.0.0:8000
```

**Frontend** (separate terminal):
```bash
cd frontend
npm install
NUXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 npm run dev
```

Your Postgres role needs `CREATEDB` if you also want to run the backend
test suite (`pytest` spins up a throwaway `test_*` database).

## Is this deployed anywhere?

Yes — <https://inventory.praponb.com>, publicly reachable by anyone since
2026-08-28. There is **no Cloudflare Access gate**: the Django login is the only
thing in front of it.

Since **2026-08-29** it runs on a dedicated **Ubuntu 26.04 LTS server on the
LAN**, not on a laptop. Docker Compose there serves the same six services, and a
systemd `cloudflared` service carries the same Cloudflare Tunnel, so the public
URL never changed. The MacBook that used to host it is a **cold standby** —
stopped, with its data frozen at the moment of cutover.

The public demo account is read-only:

```
demo / PublicDemo2026!
```

- Deployment, operations, and rollback: [`DEPLOY-UBUNTU.md`](DEPLOY-UBUNTU.md)
- Account list, security controls, and history:
  [`SESSION-2026-08-28-SECURITY.md`](SESSION-2026-08-28-SECURITY.md)

## How do I deploy a change to the live site?

The server has **no git remote** — code gets there by rsync from the machine you
develop on:

```bash
git commit -am "..."                # commit FIRST, see the warning below
./scripts/sync-to-server.sh         # rsync to the server

ssh prapon@192.168.1.49
cd ~/inventory
./scripts/backup.sh                 # always, before anything else
docker compose build && docker compose up -d
./scripts/migrate.sh
```

> **Commit before you sync.** Because the server has no git history, an
> uncommitted change that gets synced is untraceable afterwards.
> `sync-to-server.sh` refuses to run on a dirty tree for that reason; pass
> `--allow-dirty` only when you are knowingly iterating against the server.
> Each sync also writes `~/inventory/DEPLOYED_COMMIT` on the server, recording
> the SHA, branch and dirty flag it was deployed from.

`node_modules` and `.venv` are deliberately excluded from the sync: they hold
compiled binaries for the developer machine's architecture, and the Docker build
recreates them correctly inside the images.

## What do I log in with?

**On the deployed site**, only two accounts are active: `demo` (above) and the
administrator account, which requires a TOTP code from an authenticator app in
addition to its password. (The TOTP secret lives in the database, so it survived
the 2026-08-29 server move — the same authenticator entry still works.) The other five seeded accounts are **deactivated** —
they were unused and every live account is attack surface.

**On a fresh local checkout**, `seed_dev` creates six demo users:

| Username | Role | Notes |
|---|---|---|
| `admin` | System Administrator | full access, including user/reference-data admin |
| `manager` | Asset Manager | can manage assets, approve, view finance fields |
| `deptmgr` | Department Manager | scoped to their department, can approve |
| `operator` | Inventory Operator | can register/edit assets, run stocktakes |
| `employee` | Employee | can view/report on their own assigned assets |
| `auditor` | Auditor | read-only + full audit log access |

`seed_dev` does not create a `viewer` account; make one by hand if you want to
exercise that role locally.

Password: whatever you set `SEED_DEMO_PASSWORD` to before running
`seed_dev`. If you didn't set it, `seed_dev` generates a random one and
prints it once to the console — check your terminal output, it isn't
stored anywhere retrievable afterward. Note that `seed_dev` only sets a
password when it *creates* a user, so re-running it will not reset an
existing account's password.

## Where does my data live, and is it backed up?

On the Ubuntu server, in Docker volumes: PostgreSQL for the records, plus a
separate volume for attachments. Neither is published to the network — the
database has no exposed port at all, and the app itself is bound to localhost so
only the tunnel can reach it.

`scripts/backup.sh` produces a timestamped, gzipped database dump **and** a
matching tarball of the attachment volume, under `backups/`. A database dump
alone would be a half backup: restoring it would leave every attachment record
pointing at a file that no longer exists. A systemd timer runs it daily and
keeps the newest 14 of each.

Restores are rehearsed, not assumed — the migration itself was a full restore
onto a new machine, which came back with all 100,213 assets and zero errors.

One gap worth knowing: the backups sit on the **same disk** as the database they
protect. That covers accidental deletion and bad migrations, not drive failure.
Copying them to another machine is still outstanding.

## What stops someone brute-forcing the login?

Three things, since the site is public and the login is the only gate:

- **Per-IP rate limit** — 10 login attempts per minute per client IP.
- **Per-account lockout** — failed attempts are counted per *username* and
  refused past a threshold (default 10 per 15 minutes), so spreading an attack
  across many IPs doesn't help. Failures only; a successful sign-in clears the
  counter. The public `demo` account is exempt, because its password is
  published and locking it would deny every visitor at once.
- **Two-factor authentication** — accounts with the `system_admin` role must
  present a TOTP code, so a stolen admin password alone is not enough.

If you lock yourself out, it clears on its own after the window, or
immediately with:

```bash
docker compose exec backend python -c "import django; django.setup(); \
  from apps.core.login_guard import reset; reset('<username>')"
```

## What can I actually do in the app?

- **Dashboard** (`/`) — KPIs, alerts (overdue returns, maintenance due,
  warranty expiring), recent activity feed
- **Assets** (`/assets`) — register, search/filter, view/edit, full detail
  view with lifecycle actions: assign, transfer, return, reserve/checkout,
  report exception, retire/dispose/reopen, maintenance records,
  attachments, notes, full activity history, QR label + camera scan
- **Assignments** (`/assignments`) / **Reservations** (`/reservations`)
- **Maintenance** (`/maintenance`) — work list with overdue flagging
- **Stocktakes** (`/stocktakes`) — sessions, mobile count workflow,
  variance reconciliation
- **Imports** (`/imports`) / **Exports** (`/exports`) — CSV bulk workflows
- **Approvals** (`/approvals`) — pending/history, approve/reject/return
- **Notifications** (`/notifications`) — in-app alerts + mute preferences
  per event type (mandatory compliance types can't be muted)
- **Reports** (`/reports`) — catalog of reports with filters and export
- **Data quality** (`/data-quality`) — flagged records needing attention
- **Admin** (`/admin`) — users, reference data (categories/statuses/etc.),
  workflow transition rules, audit log search

## Why does the "Category" dropdown change what other fields show up?

Each category (Laptop, Desktop, Furniture, ...) has its own set of
extra attributes defined by an admin (e.g. Laptop → RAM (GB), CPU).
Selecting a category loads that category's specific fields dynamically —
switching categories clears whatever you'd entered for the previous one,
since a different category has a different schema.

## I got "This asset was changed by someone else" — is that a bug?

No — that's optimistic concurrency control working as intended (every
asset has a `version`; edits are rejected if the version you're editing
against is stale). It means someone else (or another browser tab/session)
saved a change to that exact asset after you loaded it. Click **"Reload
latest data"**, reapply your change, and save again.

## Something says "Network error — check your connection, then try again." What do I check?

This has always meant the browser's CORS **preflight** silently blocked
the request before it reached Django — not a real connectivity problem.
It happens when the frontend sends a header the backend hasn't explicitly
allowlisted. Currently allowed custom headers: `X-Correlation-ID` (every
request), `Idempotency-Key` (unsafe POSTs), `If-Match` (asset updates).

If you (or a future change) add a *new* custom header anywhere in
`frontend/app/services/api/` or `useApi.ts`, add it to `CORS_ALLOW_HEADERS`
in `backend/config/settings/base.py` too, or every browser request using
it will fail exactly this way. `curl` won't reproduce this — curl doesn't
enforce CORS preflight, so always test new endpoints in a real browser,
not just via curl, before considering them verified.

## Why do I see "no configurable notification types" or similar mismatches if I hand-edit the API?

The backend's real contract for notification preferences is a simple
mute-list: `GET/PATCH /notifications/preferences/` exchange
`{muted_types, optional_types, mandatory_types}` (flat type-code arrays) —
there's no per-type label/description from the server and no persisted
"send by email" toggle (email/SMTP delivery itself isn't implemented yet).
The frontend already adapts this into a friendlier per-type checkbox list;
if you're calling the API directly, match that flat shape, not a richer
one you might expect.

## Do I need Redis for local development?

No. Celery tasks run in eager (synchronous, in-process) mode locally via
`CELERY_TASK_ALWAYS_EAGER=true`, so background jobs (bulk import/export,
due-date reminders) execute immediately without a broker. The Docker
compose stack does run Redis + a Celery worker for a closer-to-production
setup, but it's optional for local dev.

## What's not finished yet?

Honestly, per the latest run's [final report](runs/):

- **Browser/E2E test coverage** (accessibility scans, full cross-browser
  matrix, camera-scanning E2E) is authored but was environment-blocked
  during automated QA. The sign-in paths — including the two-step 2FA
  enrolment and verification flow — have since been driven end to end in a
  real browser, but the rest of the suite still has not been executed. (This is exactly the category of gap that surfaced the
  real bugs fixed during manual testing — see git history / conversation
  log for specifics: dashboard activity rendering, notification
  preferences, missing form fields, CORS headers.)
- **Email notification delivery** is not implemented (in-app notifications
  work; SMTP dispatch is backlog).
- Full-scale (~100k record) performance verification wasn't run in this
  environment; query-count discipline was verified at seeded volume only.

Two further defects were found on 2026-08-29 while migrating the app to its own
server. Both were **pre-existing**, neither was caused by the move, and both
were resolved on 2026-08-30:

- **Attaching a file to an asset failed.** `/app/media` did not exist in the
  image, so Docker created the volume mount point as `root` while the app runs
  as an unprivileged user, and every upload raised `PermissionError`. That is
  why no attachment had ever been stored. **Fixed and deployed** — verified in
  production by writing and removing a real file.
- **The audit log's tamper-evident chain does not verify.** `verify_chain()`
  still returns `False`, and that is now known to be harmless. Seven `auth.*`
  events belonged to a user account that was later deleted; the actor link is
  `SET_NULL` and the record hash covers the actor's UUID, so removing the user
  invalidated their rows while every link between records stayed intact. It is
  bookkeeping, not tampering. `python manage.py audit_chain_report` shows which
  rows and why, read-only. `reseal_chain()` would make the check pass but would
  overwrite the evidence, so it has deliberately not been run.

Details: [`SESSION-2026-08-29-ISSUES.md`](SESSION-2026-08-29-ISSUES.md) §2.

None of these block normal use of the app in a dev/demo environment.

## What's currently broken or outstanding?

`SESSION-2026-08-29-ISSUES.md` is the consolidated, verified list. Its §0 is the
short answer: what remains is Cloudflare edge protection (dashboard work), a
credentials file to move into a password manager, two unmanaged package installs
on the server, and an untested reboot. No open defect affects users.

## Where do I report a real problem?

Every API error response includes a `correlation_id` (shown in the UI as
"Support reference"). Cross-reference it against the backend server log
(structured JSON, includes `correlation_id`) to find the exact request and
stack trace.
