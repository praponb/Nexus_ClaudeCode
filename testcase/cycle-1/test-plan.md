# Cycle 1 Test Plan — Foundation: Auth, Core Asset Register, App Shell

## Scope (per `runs/.../cycle-1/cycle-plan.md` and design §18)

In scope for Cycle 1 verification:

- Local environment & stack quality gates (compose, scripts, lockfiles, lint/typecheck/test/build, migrations check).
- Authentication (session cookie, CSRF, logout, me, expired session, rate limiting, login audit).
- Authorization: role + department scope, direct-API attempts, field-level financial restrictions.
- Asset CRUD: create (required fields, tag uniqueness, duplicate warnings, draft), detail, edit with optimistic concurrency (409), history endpoint.
- Search/filter/sort/pagination (server-side, scoped, pagination envelope).
- Saved views (own CRUD, shared, default).
- Dashboard summary (basic counts, scope-correct).
- Reference data read + basic admin API authorization.
- Audit slice: auth events + asset create/update events, hash-chain fields, restricted read.
- API platform conventions: error envelope, correlation IDs, OpenAPI schema, UUIDs, money representation, security headers, health endpoints.
- Frontend: dark-theme app shell (desktop/tablet/mobile), sign-in, asset register (table↔cards), filters, pagination, asset detail + history, create/edit forms, global search, saved views, 403/404/error pages, loading/empty/error states.
- Responsive matrix (layout §30) for delivered pages only; keyboard-only pass on sign-in/register/detail; axe-core on delivered pages; theme contrast spot check.
- Repo hygiene: no secrets, `.env` ignored, lockfiles, re-runnable scripts.

Explicitly out of scope this cycle (per cycle plan): assignment/transfer/return/reservation, maintenance, stocktake execution, approvals, notifications, import/export, QR/barcode, attachments, reports, admin UIs, Celery jobs, S3. Stubs, if present, must be clearly marked and permission-inaccessible (spot-checked in TC-FR-002-10).

## Requirement group references

LAY groups (layout.md): LAY-1 §4 viewports; LAY-2 §5 theme/status; LAY-3 §6–9 shell/nav/header; LAY-4 §10–13 dashboard/list/detail/forms; LAY-5 §19–21 components/feedback/states; LAY-6 §22–24 accessibility/motion/copy; LAY-7 §27/§30 print+responsive matrix; LAY-8 §29 acceptance criteria.

STK groups (front-back-end-stack.md): STK-1 §5 repo structure/lockfiles; STK-2 §6 frontend stack & quality commands; STK-3 §7 backend stack & quality commands; STK-4 §13 compose/scripts; STK-5 §11–12 security config & secrets; STK-6 §14/§17 CI gates & docs.

## Test environment

- Docker Compose stack from repo root: frontend `http://localhost:3000`, backend `http://localhost:8000`, PostgreSQL, Redis.
- Seeded dev data per design §10.4: demo users `admin`, `manager`, `deptmgr`, `operator`, `employee`, `auditor`; ~200 assets; reference data.
- Seed credentials must come from the project README (dev-only). If seed users or README credentials are missing, affected tests are BLOCKED and a defect is raised.

## Execution strategy (execute phase)

1. Run stack quality gates via allowlisted commands (lint/format/typecheck/tests/builds/scripts) — see `09-install-stack-tests.md`.
2. Execute backend automated checks (pytest) where available; QA-level API checks are executed as scripted HTTP calls where the environment permits, otherwise BLOCKED with reason.
3. UI/responsive/a11y cases: run via available tooling; anything requiring a real browser not available in this environment is marked MANUAL with justification.
4. Record every result in `cycle-1-report.md` via the QA reporting tool; no PASSED without evidence.

## Traceability (cycle-1 test files → requirements)

| File | Requirements covered |
|---|---|
| 01-auth-tests.md | FR-001, NFR-007 |
| 02-authorization-tests.md | FR-002, BR-007, NFR-007, NFR-008 |
| 03-asset-crud-tests.md | FR-003, FR-004, FR-029 (slice), BR-001, BR-005, BR-008, BR-009, NFR-014 |
| 04-search-savedviews-dashboard-tests.md | FR-005, FR-006, FR-020 (basic), FR-026 (slice) |
| 05-platform-api-tests.md | FR-025 (slice), NFR-005, NFR-007, NFR-009, NFR-011, STK-3, design §11/§13 |
| 06-ui-shell-forms-tests.md | NFR-001, LAY-2…LAY-5, FR-001 (UI), FR-003/004 (UI) |
| 07-responsive-a11y-tests.md | NFR-002, NFR-003, LAY-1, LAY-6, LAY-7, LAY-8 |
| 08-journeys-e2e-tests.md | J-6 (FR-001/004/005), J-1 registration slice (FR-003) |
| 09-install-stack-tests.md | STK-1…STK-6, NFR-004 (smoke), NFR-010 |

## Entry criteria

- Frontend and backend cycle-1 deliverables merged per cycle plan.
- `./scripts/dev-up.sh && ./scripts/migrate.sh && ./scripts/seed-dev.sh` succeeds (TC-STK-4-01 is the gate).

## Exit criteria (cycle-1 DoD)

- All Critical/High priority tests executed; no unresolved critical/high defects without a recorded risk decision.
- `cycle-1-report.md` filed with evidence and requirement-status recommendations (implemented / partially-implemented / deferred).
