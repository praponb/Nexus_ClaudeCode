# Cycle 2 Test Plan — Asset Inventory Web Application

- **Version:** 1.0 (Cycle 2 design phase)
- **Sources:** `detail-design-specification.md` Rev 1.1 (§18 Delivery Plan — Cycle 2 scope). NOTE: `runs/run-1c738338ee96/cycle-2/cycle-plan.md` was not present in the workspace at design time; this plan derives Cycle-2 scope from the approved design spec §18, §2.3 ADRs, and §11.3 endpoint status table, and will be reconciled against the cycle plan if it appears.
- **Owner:** QA agent

## 1. Scope

### 1.1 Cycle 2 delivers (per design §18)
1. **Defect closure first:** DEF-001 (root `compose.yaml`), DEF-002 (root `.env.example`), DEF-003/ADR-004 (Idempotency-Key D-08 on asset create + all lifecycle/transition endpoints), DEF-004/ADR-003 (`backend/uv.lock` committed), DEF-006 (reference-data DELETE → deactivate semantics per BR-004), Cycle-1 critical npm-audit transitive dev dependency (NFR-007).
2. **Workflows:** assignment (FR-007), transfer (FR-008), return/check-in (FR-009), reservation/checkout (FR-010), exception reports lost/stolen/missing/damaged (FR-013).
3. **Maintenance + warranty:** FR-011, FR-012.
4. **Attachments + notes:** FR-015, FR-016.
5. **QR labels + scanning:** FR-017, D-14.
6. **CSV import/export (Celery):** FR-018, FR-019, D-10.
7. **Stocktake:** FR-022 sessions + observations (reconciliation polish in C3).
8. **Full activity feed:** FR-029; dashboard completion (FR-020); data-quality checks v1 (FR-028).
9. **Carry-over from Cycle 1:** re-execute the 36 BLOCKED QA cases where the environment permits (browser runner / Docker availability), esp. security headers/CORS (TC-NFR-007-01, -06), CSRF rejection (TC-FR-001-05), rotation (TC-FR-001-10), rate limiting (TC-FR-001-09), combined filter/sort cases in `search.json`, UI/E2E cases (TC-FR-001-06/07, TC-E2E-J6-01, TC-E2E-J1-01), and responsive/a11y matrix cases in `ui-responsive-a11y.json`.

### 1.2 Explicitly out of scope for Cycle 2
Approvals engine + separation of duties (FR-024), notifications (FR-023), reports catalog (FR-021), admin UIs (FR-027), archiving/retention (FR-030), retirement/disposal/reopen endpoints (FR-014 — C3), offline stocktake (D-03), OIDC production integration (D-01), light theme (D-05).

## 2. New/Updated Suite Files (Cycle 2)

| Suite file | Requirements | Focus |
|---|---|---|
| `test-cases/defect-closure-c2.json` | DEF-001…DEF-006, D-08, BR-004, STK | Verification of Cycle-1 defect fixes |
| `test-cases/idempotency.json` | D-08, FR-003, FR-007–FR-010, FR-018 | Idempotency-Key behavior on all retry-sensitive POSTs |
| `test-cases/workflows.json` | FR-007, FR-008, FR-009, FR-010, FR-013, BR-002, BR-003 | Assignment/transfer/return/reservation/exception workflows |
| `test-cases/maintenance.json` | FR-011, FR-012 | Maintenance records, under-maintenance status, next-due, warranty/expiry |
| `test-cases/attachments-notes.json` | FR-015, FR-016, D-04, NFR-007 | Upload validation, authorized download, audit; append-only notes |
| `test-cases/qr-scan.json` | FR-017, D-14 | QR label generation/print, scan flow, manual fallback, unknown codes |
| `test-cases/import-export.json` | FR-018, FR-019, D-10 | CSV template, wizard, validation, policies, async commit, formula-injection mitigation |
| `test-cases/stocktake.json` | FR-022 | Session lifecycle, observations, outcome classification, variance |
| `test-cases/activity-dataquality.json` | FR-029, FR-028, FR-020 | Combined activity feed, data-quality flags v1, dashboard completion |

Existing Cycle-1 suites remain valid; carried-over BLOCKED cases are re-run in place with Cycle-2 evidence.

## 3. Environment & Preconditions
Unchanged from Cycle 1 plan (§3): compose stack, seed users per role, ~200 seeded assets. Cycle 2 additionally requires: `redis` + `celery-worker` services running (import/export async), `minio` or local media volume for attachments, and the seed's 1 open stocktake session.

## 4. Entry / Exit Criteria
- **Entry:** all Cycle-1 quality gates still green; DEF-001…DEF-006 fixes merged; new endpoints present in exported OpenAPI schema (drift guard green).
- **Exit:** all Critical/High Cycle-2 tests executed or explicitly BLOCKED with justification; defect-verification cases closed; `testcase/cycle-2-report.md` filed with evidence under `testcase/evidence/cycle-2/`.

## 5. Evidence / Status Policy
Unchanged: no PASSED without executed evidence; statuses `NOT_RUN | PASSED | FAILED | BLOCKED | MANUAL`.
