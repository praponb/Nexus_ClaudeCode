# Cycle 1 Test Plan — Foundation (Auth, Core Asset Register, App Shell)

- **Cycle:** 1 of 3
- **Design baseline:** `detail-design-specification.md` Rev 1.0
- **Cycle plan:** `runs/run-1c738338ee96/cycle-1/cycle-plan.md`
- **Master test-case file:** `testcase/cycle-1/test-cases.json`

## 1. Objectives

Verify that the Cycle 1 foundation is functionally correct, secure by default, and meets the
design contract: session auth with audit, role+scope authorization, asset CRUD with optimistic
concurrency and duplicate pre-checks, scoped search/filter/pagination, saved views, basic
dashboard summary, reference data APIs, error-envelope/pagination/correlation conventions,
dark-theme responsive app shell meeting WCAG 2.2 AA targets, and a reproducible
install/build/startup path.

## 2. In Scope (Cycle 1)

| Area | Requirements | Test suite |
|---|---|---|
| Authentication (session, CSRF, audit) | FR-001, FR-025 (partial), NFR-007 | TC-FR-001-* |
| Authorization (roles, scopes, field-level) | FR-002, NFR-007, NFR-008 | TC-FR-002-* |
| Asset creation + duplicate checks + idempotency | FR-003, BR-001, D-08 | TC-FR-003-* |
| Asset view/edit + optimistic concurrency + history | FR-004, BR-009, D-07 | TC-FR-004-* |
| Search / filter / sort / pagination | FR-005, D-09 | TC-FR-005-* |
| Saved views (own views) | FR-006 | TC-FR-006-* |
| Dashboard summary (basic counts) | FR-020 (basic) | TC-FR-020-* |
| Reference data read + admin write | FR-026 (partial), BR-004 | TC-FR-026-* |
| Audit events for auth + asset mutations | FR-025 (partial), NFR-009 | TC-FR-025-* |
| API conventions (envelope, correlation, OpenAPI, health) | §11, §14, NFR-005, NFR-009 | TC-API-* |
| Security headers / CORS / injection / cookies | NFR-007 | TC-NFR-007-* |
| Responsive behavior | NFR-002, LAY groups | TC-NFR-002-* |
| Accessibility (WCAG 2.2 AA) | NFR-003, LAY groups | TC-NFR-003-* |
| Install / build / startup / repo hygiene | STK-1…STK-6, §16 | TC-STK-* |
| E2E journeys J-6 and J-1 (registration slice) | spec §11.1, §3.2 | TC-J6-01, TC-J1-01 |

## 3. Out of Scope (Cycle 1)

Assignment/transfer/return/reservation (FR-007…FR-010), maintenance/warranty (FR-011/012),
exceptions (FR-013), retirement/disposal (FR-014), attachments (FR-015), notes (FR-016),
barcode/QR (FR-017), import/export (FR-018/019), reports (FR-021), stocktake (FR-022),
notifications (FR-023), approvals (FR-024), data quality (FR-028), activity feed beyond
lifecycle+audit (FR-029), archiving (FR-030), user admin UI (FR-027), performance at volume
(NFR-004/006 full validation), backup/restore drill (NFR-012).

## 4. Test Environment

- Docker Compose stack per §16.1: `frontend` (Nuxt, :3000), `backend` (Django, :8000),
  `postgres`, `redis` (wired, not required). Started via `scripts/dev-up.sh`, migrated via
  `scripts/migrate.sh`, seeded via `scripts/seed-dev.sh`.
- Seed users per design §10.4: `admin`, `manager`, `deptmgr`, `operator`, `employee`,
  `auditor` (dev passwords, local only).
- Backend test mode: `config.settings.test`; frontend: production build + dev server as applicable.

## 5. Execution Approach

1. **Repo hygiene & install** (TC-STK-*) first — blocks everything else.
2. **Backend API tests** via pytest suite delivered by backend agent plus direct HTTP checks
   (allowlisted commands only) against the compose stack: auth, RBAC, CRUD, concurrency,
   envelope, pagination.
3. **Frontend unit/component tests** via `pnpm test`; lint/typecheck/build gates.
4. **E2E** via Playwright (sign-in, create asset, search→detail, stale-version conflict,
   responsive matrix smoke, axe-core on delivered pages).
5. **Manual/semi-automated**: keyboard-only passes on sign-in/register/detail, contrast spot
   check of theme tokens, security-header inspection.

## 6. Entry Criteria

- Frontend and backend Cycle 1 deliverables merged in workspace; compose stack boots;
  migrations + seed run cleanly; OpenAPI schema exportable.

## 7. Exit Criteria (maps to cycle Definition of Done)

- All P0 tests executed; no open Critical/High defects without a recorded risk decision.
- Every requirement claimed "implemented" for Cycle 1 has at least one PASSED test with evidence.
- `testcase/cycle-1-report.md` filed: per-test status, evidence paths, defects, and
  requirement-status recommendations for traceability.

## 8. Traceability Matrix (requirement → test IDs)

| Requirement | Test IDs |
|---|---|
| FR-001 Authentication | TC-FR-001-01 … TC-FR-001-11 |
| FR-002 Authorization | TC-FR-002-01 … TC-FR-002-08 |
| FR-003 Asset creation | TC-FR-003-01 … TC-FR-003-09 |
| FR-004 Asset view/edit | TC-FR-004-01 … TC-FR-004-07 |
| FR-005 Search/filter/sort/pagination | TC-FR-005-01 … TC-FR-005-08 |
| FR-006 Saved views | TC-FR-006-01 … TC-FR-006-03 |
| FR-020 Dashboard (basic) | TC-FR-020-01 … TC-FR-020-03 |
| FR-025 Audit (partial) | TC-FR-025-01 … TC-FR-025-03 |
| FR-026 Reference data (partial) | TC-FR-026-01 … TC-FR-026-03 |
| BR-001 Tag uniqueness | TC-FR-003-03, TC-FR-003-05 |
| BR-004 Deactivate-not-delete | TC-FR-026-03 |
| BR-009 Optimistic concurrency | TC-FR-004-03 |
| NFR-002 Responsive | TC-NFR-002-01 … TC-NFR-002-03 |
| NFR-003 Accessibility | TC-NFR-003-01 … TC-NFR-003-07 |
| NFR-005 Health endpoints | TC-API-006 |
| NFR-007 Security | TC-NFR-007-01 … TC-NFR-007-05 |
| NFR-009 Correlation/audit | TC-API-002, TC-FR-025-01 |
| STK-1…STK-6 Stack/install | TC-STK-001 … TC-STK-006 |
| API conventions (D-06…D-09, §11/§14) | TC-API-001 … TC-API-007 |
| Journey J-6 | TC-J6-01 |
| Journey J-1 (registration slice) | TC-J1-01 |

## 9. Risks / Notes

- Version-availability deviations (Nuxt 4, Django 6, Postgres 18) may occur per A-06; verify
  any ADR/ASSUMPTIONS.md entries exist rather than failing on version numbers themselves.
- Celery/redis are placeholders in Cycle 1 (D-10); eager fallback acceptable — do not fail on
  absent workers, do fail if compose references missing services fatally.
- Local auth must be inert in production settings (D-01/D-13) — covered by TC-FR-001-11 and
  TC-STK-006.
