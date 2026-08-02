# Cycle 1 Test Plan — Asset Inventory Web Application

- **Version:** 1.0 (Cycle 1 design phase)
- **Sources:** `detail-design-specification.md` Rev 1.0, `runs/run-1c738338ee96/cycle-1/cycle-plan.md`
- **Owner:** QA agent

## 1. Scope

Cycle 1 delivers: reproducible local environment, session-cookie auth, core data model, asset register (list/create/edit/detail), global search, saved views, basic dashboard summary, reference-data read APIs, audit events for auth + asset mutations, dark-themed app shell.

In-scope requirement IDs: **FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-020 (basic), FR-025 (auth + asset mutation events only), FR-026 (read + basic admin API), NFR-002, NFR-003, NFR-004 (smoke only), NFR-007, LAY-1…LAY-8, STK-1…STK-6** (build/hygiene).

Explicitly out of scope for Cycle 1 (per cycle plan): assignment/transfer/return/reservation workflows, maintenance, stocktake, approvals, notifications, import/export, barcode/QR, attachments, reports, admin UIs, Celery jobs, S3. Any test touching these is deferred to later cycles.

## 2. Test ID Convention

`TC-<REQID>-<nn>` per design §15.2. Suites:

| Suite file | Requirement | Focus |
|---|---|---|
| `test-cases/auth.json` | FR-001 | Login, logout, session, CSRF, audit of auth |
| `test-cases/authz.json` | FR-002 | Role + scope enforcement, horizontal/vertical escalation, field-level finance restriction |
| `test-cases/asset-crud.json` | FR-003, FR-004 | Create/read/update, tag uniqueness, duplicate warnings, optimistic concurrency, validation |
| `test-cases/search.json` | FR-005 | Global search, filters, sort, pagination, URL state |
| `test-cases/saved-views.json` | FR-006 | Saved view CRUD, apply, default |
| `test-cases/dashboard.json` | FR-020 | Summary KPIs, scope correctness, states |
| `test-cases/audit.json` | FR-025 | Audit events for login/asset mutations, append-only, hash chain presence |
| `test-cases/api-contract.json` | FR-002/FR-005, STK | Error envelope, pagination envelope, correlation IDs, OpenAPI |
| `test-cases/ui-responsive-a11y.json` | NFR-002, NFR-003, LAY-1…8 | App shell, responsive matrix, keyboard, axe, theme/contrast |
| `test-cases/security.json` | NFR-007 | Cookies, headers, injection, XSS, rate limiting, secrets |
| `test-cases/build-hygiene.json` | STK-1…6, NFR-005 | Scripts, lockfiles, quality gates, health endpoints |

## 3. Environment & Preconditions (all tests)

- Stack started via `./scripts/dev-up.sh && ./scripts/migrate.sh && ./scripts/seed-dev.sh`.
- Backend at `http://localhost:8000`, frontend at `http://localhost:3000`.
- Seed users per design §10.4: `admin` (system_admin), `manager` (asset_manager), `deptmgr` (department_manager), `operator`, `employee`, `auditor` — dev passwords from README only.
- Seed data: ~200 assets, departments/locations/categories/statuses/conditions, saved views, 1 open stocktake.
- API client: curl/HTTPie or automated pytest/Playwright; browser: latest Chrome/Firefox for UI tests.

## 4. Entry / Exit Criteria

- **Entry:** backend + frontend quality gates pass (`pytest`, `pnpm lint/typecheck/test/build`); OpenAPI schema exported; seed script idempotent.
- **Exit:** all Critical/High tests executed; no unresolved Critical/High defects without recorded risk decision; `testcase/cycle-1-report.md` filed with evidence paths.

## 5. Evidence Policy

No test is marked PASSED without executed evidence (command output, screenshot, HAR/log excerpt) stored under `testcase/evidence/cycle-1/`. Tests that cannot run in this environment are BLOCKED or MANUAL with justification.

## 6. Status Values

`NOT_RUN | PASSED | FAILED | BLOCKED | MANUAL` — matching the QA execution report schema.
