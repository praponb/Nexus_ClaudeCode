# User Manual: Asset Inventory Application

A step-by-step guide to using the application once it's running. For setup,
login credentials, and troubleshooting, see [FAQ.md](FAQ.md) first — this
manual assumes the app is already up at http://localhost:3000 and you're
signed in.

## Contents

1. [Signing in and the app shell](#1-signing-in-and-the-app-shell)
2. [Dashboard](#2-dashboard)
3. [Assets — register, find, and view](#3-assets--register-find-and-view)
4. [Asset lifecycle actions](#4-asset-lifecycle-actions)
5. [Assignments & Reservations](#5-assignments--reservations)
6. [Maintenance](#6-maintenance)
7. [Stocktakes](#7-stocktakes)
8. [Bulk import & export](#8-bulk-import--export)
9. [Scan](#9-scan)
10. [Approvals](#10-approvals)
11. [Notifications](#11-notifications)
12. [Reports](#12-reports)
13. [Data quality](#13-data-quality)
14. [Administration](#14-administration)
15. [Roles at a glance](#15-roles-at-a-glance)
16. [Scripts reference](#16-scripts-reference)

---

## 1. Signing in and the app shell

Go to `/login` and sign in (see [FAQ.md](FAQ.md#what-do-i-log-in-with) for the
account list) — `http://localhost:3000/login` for a local stack, or
<https://inventory.praponb.com/login> for the deployed one. After signing in
you land on the Dashboard.

**If your account requires two-factor authentication** (administrators do),
sign-in is two steps. The password step alone does not sign you in:

- **First time:** the app shows a QR code. Scan it with an authenticator app
  (Google Authenticator, 1Password, Authy…), enter the 6-digit code, then
  **save the 10 recovery codes it shows** — they are displayed only once, and
  each works exactly once.
- **Afterwards:** enter the current 6-digit code. If you don't have your
  authenticator to hand, choose *Use a recovery code instead*.

You have 5 minutes to complete the second step before the attempt expires and
you have to start again.

The app shell has:
- **Top bar** — search, notification bell, help, account menu (sign out is
  here), and a **New asset** shortcut.
- **Sidebar** (desktop) / **bottom nav** (mobile) — Home, Assets, Scan,
  Tasks (assignments/reservations/maintenance/approvals), More (everything
  else).
- Every list screen keeps its filters/sort/page in the URL, so you can
  bookmark or share a specific filtered view.

## 2. Dashboard

The landing page (`/`) shows, scoped to what your role can see:
- **Key figures**: total assets, assigned, unassigned, distinct status
  types — each links to a pre-filtered asset list.
- **Attention needed**: overdue returns, maintenance due, warranty
  expiring, missing/lost/stolen — only shown when relevant.
- **Assets by status** / **by category** — ranked lists (not charts, so
  they stay screen-reader accessible) linking to filtered views.
- **Recent activity** — latest lifecycle events across assets in your
  scope.

## 3. Assets — register, find, and view

### Registering an asset
1. Click **New asset** (top bar) or go to `/assets/new`.
2. Fill in **Identity**: name and category are required; asset tag is
   optional (auto-generated if left blank).
3. Selecting a **Category** may reveal a **Category attributes** section
   with fields specific to that category (e.g. Laptop → RAM (GB), CPU).
   Required category attributes must be filled in to save (unless the
   asset's status is Draft).
4. Fill in **Status and placement** — condition, department, location, and
   **Acquisition type** (free text, e.g. "purchased", "leased", "donated")
   are all required unless saving as Draft.
5. If your role can view finance fields, fill in **Financial and
   warranty** (purchase price, warranty dates) as needed.
6. Click **Save asset**. If the system finds possible duplicates (matching
   serial/manufacturer/model), it shows a non-blocking warning — review
   them, then click **Save asset anyway** if this is genuinely a new item.

### Finding assets
- `/assets` — searchable, filterable, sortable register. Toggle between
  table and card view; save your current filter combination as a **saved
  view** for quick reuse later.
- The top-bar search does exact-tag-first lookup across assets in your
  scope.

### Viewing an asset
Click any asset to open its detail page, with sub-tabs for **Overview**,
**Maintenance**, **Documents**, **History**. The overview shows identity,
placement, and (if permitted) financial/warranty info, plus a warning
banner if the warranty has expired.

## 4. Asset lifecycle actions

From an asset's detail page, the action bar offers (availability depends
on your role and the asset's current state):

| Action | What it does |
|---|---|
| **Assign** | Give the asset to a person; automatically closes any prior active assignment first. |
| **Transfer** | Move the asset to a new location/department, optionally with recipient confirmation, or route through approval if configured. |
| **Return** | Check the asset back in — record condition/damage, closes the active assignment. |
| **Reserve / checkout** | Book the asset for a future window (conflict-checked) or check out an existing reservation immediately. |
| **Report exception** | Log it as lost, stolen, missing, or damaged, with evidence; resolving later preserves the original report. |
| **Retire / Dispose / Reopen** | End-of-life actions — disposal enforces blockers (e.g. still assigned) unless you have override permission; reopening a disposed asset requires a justification. |
| **Maintenance** | View/add maintenance records; overdue work is flagged. |
| **Documents** | Upload attachments (validated type/size) and notes; downloads are permission-checked and every action is audited. |
| **QR label** | Print a scannable label for the asset. |

All of these are audited, and unsafe actions are retried safely if your
connection drops mid-request (no duplicate side effects).

## 5. Assignments & Reservations

- `/assignments` — assignment history/current assignments list, scoped to
  what your role can see.
- `/reservations` — all reservations with status and overdue filters;
  overdue reservations are visually flagged.

## 6. Maintenance

`/maintenance` — a work list of maintenance records across assets in your
scope, with overdue items flagged. Individual records are also visible
and addable from each asset's **Maintenance** tab.

## 7. Stocktakes

`/stocktakes` — physical inventory verification sessions.
1. A manager starts a **stocktake session** (scoped by location/department).
2. Operators record observations via `/stocktakes/[id]/count` — scan or
   manually enter each asset's tag, note its condition, and flag any
   discrepancy.
3. The session owner reviews the **variance report** and reconciles
   discrepancies before closing the session.

## 8. Bulk import & export

- **Import** (`/imports`): template → upload your CSV → validate/preview
  (see exactly what will change) → choose a duplicate-handling policy →
  commit asynchronously → get a row-level result report. Nothing is
  written until you confirm after the preview step.
- **Export** (`/exports`): async export jobs that respect your current
  filters and role's field permissions (e.g. finance fields excluded if
  you can't view them); poll status and download when ready.

## 9. Scan

`/scan` — camera-based QR/barcode scanning (falls back to your browser's
native scanner, then to manual tag entry if no camera is available).
Scanning is read-only lookup — nothing is committed by scanning alone; it
just takes you to the matching asset, or tells you the tag wasn't found.

## 10. Approvals

`/approvals` — your approval inbox. Defaults to **Pending**; switch the
status filter to see Approved/Rejected/Returned history. Opening a pending
request lets you approve, reject, or return it with comments (comments are
mandatory for anything other than a straight approval). If your
organization has separation-of-duties enabled, you can't approve your own
request — it needs another approver.

## 11. Notifications

`/notifications` — in-app alerts for events in your scope (assignments,
approvals, stocktakes, etc.). Click **Preferences** to mute individual
optional notification types; compliance-related types are mandatory and
can't be muted. There is currently no email delivery — everything is
in-app only.

## 12. Reports

`/reports` (visible to Asset Managers, Department Managers, System Admins,
and Auditors) — a catalog of 14 built-in reports:

Asset register · Assets by status · Assets by category · Assets by
location · Assets by department · Current assignments · Overdue returns ·
Assignment history · Warranty expiry · Maintenance due · Maintenance
history · Lost/stolen/missing/damaged report · Stocktake variance ·
Retirement and disposal

Each report supports date ranges and its own relevant filters, shows
reconciled totals, and can be exported if you have export permission.

## 13. Data quality

`/data-quality` (visible to roles that can manage assets) — a work queue
of records with detected issues (e.g. missing required data, likely
duplicates, inconsistent lifecycle state), split into errors and
warnings. Resolve issues through the asset's normal edit/workflow screens
— resolutions preserve the record's audit history rather than silently
overwriting it.

## 14. Administration

`/admin` (System Administrators, generally) has five sections:

- **User administration** — view users, assign roles/scopes, activate or
  deactivate accounts. The system prevents removing the last active admin.
- **Reference data** — manage categories (including their dynamic
  attribute schemas), statuses, conditions, locations, departments, cost
  centers, suppliers. Deleting deactivates rather than hard-deletes, so
  historical records stay valid.
- **Workflow rules** — read-only view of the status transition rules that
  govern lifecycle changes.
- **Audit log** — tamper-evident, append-only log of security-sensitive
  and business-significant actions (actor, action, target, correlation
  ID). Searchable; nothing here can be edited or deleted through the UI.
- **Settings & retention** — archiving/retention policy for business
  records (records are archived, never physically deleted, by normal
  application operations).

## 15. Roles at a glance

| Role | Can do |
|---|---|
| System Administrator | Everything, including user and reference-data administration |
| Asset Manager | Manage assets, approve requests, view finance fields, see reports |
| Department Manager | Same as Asset Manager, scoped to their department |
| Inventory Operator | Register/edit assets, run stocktakes; no finance/reports/admin access |
| Employee | View and act on their own assigned assets only |
| Auditor | Read-only everywhere, plus full audit log and reports access |
| Viewer | Read-only across the whole register — no writes, no finance fields, no audit log. Used for the public demo account |

Exact capabilities are always re-checked server-side — the UI hiding a
button is a convenience, not the actual security boundary.

## 16. Scripts reference

Everything below lives in `scripts/` at the repo root, and (except
`install-root-files.sh`) targets the **Docker Compose stack** by default
— run `./scripts/dev-up.sh` first. All scripts are safe to re-run.

| Script | What it does | When to use it |
|---|---|---|
| `install-root-files.sh` | One-time: copies the canonical `compose.yaml` and `.env` templates to the repo root, without overwriting anything already there. | Once, on a fresh checkout, before first use. |
| `dev-up.sh` | Builds and starts the full stack (Postgres, Redis, backend, Celery worker, frontend), then polls the backend health endpoint until it's ready. Also auto-bootstraps root `compose.yaml`/`.env` from the backend's canonical copies if they're missing. | Start of every dev session. |
| `dev-down.sh` | Stops the stack (`docker compose down --remove-orphans`). Data volumes are preserved — add `-v` yourself to `docker compose down -v` if you actually want to wipe data. | End of a dev session, or to restart clean. |
| `migrate.sh` | Runs `python manage.py migrate` inside the running backend container. Forwards any extra args. | After pulling changes that include new backend migrations. |
| `seed-dev.sh` | Runs the `seed_dev` management command (creates demo users + ~200 sample assets). Idempotent — safe to re-run. | After a fresh `migrate`, or to reset demo data. |
| `check.sh` | Runs all six backend quality gates in order: `ruff format --check`, `ruff check`, `mypy`, `makemigrations --check --dry-run`, `check --deploy`, `pytest`. Prefers the running backend container, but that only carries ruff/mypy/pytest when built from the `dev` stage — against a `BACKEND_BUILD_TARGET=production` stack it automatically falls back to a one-off dev-stage container. Set `CHECK_MODE=local` to run against a host-installed venv instead. | Before committing/pushing backend changes. |
| `export-openapi.sh` | Regenerates `backend/openapi.json` from the live schema (via drf-spectacular) and validates it. | After changing any backend API (serializers/views/urls). |
| `backup.sh` | Dumps the Postgres database with `pg_dump`, gzips it to `backups/<timestamp>.sql.gz` (git-ignored), then prunes to the newest `BACKUP_KEEP` dumps (default 48). Reminds you to also snapshot the attachment media volume on the same schedule. | Runs daily on its own via the `com.praponb.inventory.backup` LaunchAgent; run it by hand before risky changes. See `backend/docs/BACKUP_RESTORE.md`. |
| `restore.sh <file.sql.gz>` | **Destructive.** Drops and recreates the database, then restores the given backup into it. Refuses to run if `APP_ENV=production`. Run `migrate.sh` afterward for any migrations created since that backup. | Disaster recovery, or restoring a known-good snapshot locally. |

For the full backup/restore drill procedure (including the audit-chain
integrity check to run after a restore), see
[`backend/docs/BACKUP_RESTORE.md`](backend/docs/BACKUP_RESTORE.md).

If you're running **without Docker** (see [FAQ.md](FAQ.md#option-b-local-dev-no-docker)),
these scripts won't work as-is since they all call `docker compose exec`
— run the equivalent `manage.py`/`npm`/`pytest` commands directly instead,
using the same env vars documented there.
