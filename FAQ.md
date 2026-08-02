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

## What do I log in with?

`seed_dev` creates six demo users, all local-only (session-cookie auth, not
for production):

| Username | Role | Notes |
|---|---|---|
| `admin` | System Administrator | full access, including user/reference-data admin |
| `manager` | Asset Manager | can manage assets, approve, view finance fields |
| `deptmgr` | Department Manager | scoped to their department, can approve |
| `operator` | Inventory Operator | can register/edit assets, run stocktakes |
| `employee` | Employee | can view/report on their own assigned assets |
| `auditor` | Auditor | read-only + full audit log access |

Password: whatever you set `SEED_DEMO_PASSWORD` to before running
`seed_dev`. If you didn't set it, `seed_dev` generates a random one and
prints it once to the console — check your terminal output, it isn't
stored anywhere retrievable afterward.

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
  during automated QA — it was never actually executed in a real browser
  by the agents. (This is exactly the category of gap that surfaced the
  real bugs fixed during manual testing — see git history / conversation
  log for specifics: dashboard activity rendering, notification
  preferences, missing form fields, CORS headers.)
- **Email notification delivery** is not implemented (in-app notifications
  work; SMTP dispatch is backlog).
- One **High-severity npm audit finding** (transitive dev dependency) is
  open with a recorded, conditional risk acceptance — not yet patched.
- `backend/uv.lock` isn't committed yet (accepted risk; `package-lock.json`
  for the frontend is committed and pinned).
- Full-scale (~100k record) performance verification wasn't run in this
  environment; query-count discipline was verified at seeded volume only.

None of these block normal use of the app in a dev/demo environment.

## Where do I report a real problem?

Every API error response includes a `correlation_id` (shown in the UI as
"Support reference"). Cross-reference it against the backend server log
(structured JSON, includes `correlation_id`) to find the exact request and
stack trace.
