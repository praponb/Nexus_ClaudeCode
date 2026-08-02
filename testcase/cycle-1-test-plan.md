# Cycle 1 Test Plan — Asset Inventory Web Application

- **Cycle:** 1 (Foundation: Auth, Core Asset Register, App Shell)
- **Sources:** `detail-design-specification.md` Rev 1.0, `requirements/specification.md` v1.0, `runs/run-1c738338ee96/cycle-1/cycle-plan.md`
- **Status:** Designed (execution pending Cycle 1 frontend/backend deliverables)
- **Test data file:** `testcase/cycle-1-test-cases.json` (normative structured definitions)

## 1. Scope

### 1.1 In scope for Cycle 1 verification
- Installation/build/startup and repo hygiene (compose stack, scripts, lockfiles, secret hygiene) — STK groups.
- FR-001 Authentication (session login/logout/me, CSRF, cookie flags, login audit, rate limiting, expired-session UX).
- FR-002 Authorization (role + scope enforcement on API and UI, field-level finance restriction, horizontal/vertical escalation attempts).
- FR-003 Asset Creation (required fields, tag uniqueness BR-001, duplicate warnings BR-008, draft save, atomic asset+lifecycle+audit creation).
- FR-004 Asset Viewing/Editing (detail view, version/409 concurrency BR-009, audited updates, validation).
- FR-005 Search/Filter/Sort/Pagination (global search exact-tag-first, scoped results, D-09 pagination envelope).
- FR-006 Saved Views (own-view CRUD, shared-view authorization, default view).
- FR-020 Dashboard (basic scoped summary, state handling, reconciliation with permitted records).
- FR-025 Audit History (partial: auth + asset mutation audit events, correlation IDs, immutability via API).
- FR-026 Reference Data (partial: read endpoints + admin write, seeded defaults per spec §8.1/§8.2).
- API conventions (§11 error envelope, UUID identifiers D-02, correlation ID D/NFR-009, OpenAPI schema availability).
- NFR-002 Responsive, NFR-003 Accessibility (WCAG 2.2 AA), NFR-004 performance smoke, NFR-007 Security spot checks.
- E2E journeys: J-6 (sign in, search, open asset) and registration slice of J-1.

### 1.2 Out of scope for Cycle 1 (later cycles — deferred, not tested)
Assignment/transfer/return/reservation (FR-007…FR-010), maintenance/warranty (FR-011/012), exceptions (FR-013), retirement/disposal (FR-014), attachments/notes (FR-015/016), barcode/QR (FR-017), import/export (FR-018/019), reports (FR-021), stocktake (FR-022), notifications (FR-023), approvals (FR-024), user admin UI (FR-027), data quality (FR-028), full activity feed (FR-029), archiving (FR-030), NFR-012 backup drill, NFR-006 scale test.

## 2. Test Environment
- Docker Compose stack per design §16.1: `frontend` (Nuxt, :3000), `backend` (Django, :8000), `postgres`, `redis`. Seeded via `scripts/seed-dev.sh` (demo users per role: `admin`, `manager`, `deptmgr`, `operator`, `employee`, `auditor`; ~200 assets; reference data per §10.4).
- Browsers (E2E/manual): latest Chrome + Firefox minimum for Cycle 1 smoke; full matrix in Cycle 3.
- Viewports for responsive checks (layout §30): 320×568, 480×800, 768×1024, 1280×800, 1920×1080.

## 3. Approach
- API tests via HTTP client against `localhost:8000/api/v1/` (curl/Playwright request context) capturing request/response evidence.
- UI/E2E via Playwright where the environment permits; otherwise MANUAL with step-by-step evidence notes.
- axe-core automated a11y scans on delivered pages when a browser runtime is available; otherwise flagged MANUAL.
- Backend quality gates executed through allowlisted commands only (e.g. pytest, ruff) — any command not allowlisted is recorded as BLOCKED with reason.
- **No test is marked PASSED without executed evidence** (spec §17).

## 4. Traceability Summary (test counts per requirement)
| Requirement | Test IDs | Count |
|---|---|---|
| STK (install/build/hygiene) | TC-STK-01…06 | 6 |
| FR-001 Authentication | TC-FR-001-01…10 | 10 |
| FR-002 Authorization | TC-FR-002-01…08 | 8 |
| FR-003 Asset Creation | TC-FR-003-01…09 | 9 |
| FR-004 View/Edit | TC-FR-004-01…06 | 6 |
| FR-005 Search/Filter/Sort/Page | TC-FR-005-01…08 | 8 |
| FR-006 Saved Views | TC-FR-006-01…04 | 4 |
| FR-020 Dashboard (basic) | TC-FR-020-01…03 | 3 |
| FR-025 Audit (partial) | TC-FR-025-01…03 | 3 |
| FR-026 Reference Data (partial) | TC-FR-026-01…03 | 3 |
| API conventions (§11, D-02/07/09, NFR-009) | TC-API-001…05 | 5 |
| NFR-002 Responsive | TC-NFR-002-01…04 | 4 |
| NFR-003 Accessibility | TC-NFR-003-01…06 | 6 |
| NFR-004 Performance smoke | TC-NFR-004-01…02 | 2 |
| NFR-007 Security | TC-NFR-007-01…05 | 5 |
| E2E journeys (J-1 slice, J-6) | TC-E2E-01…02 | 2 |
| **Total** | | **84 → see JSON (84 cases collapsed to 84? no: 84)** |

> Count note: the JSON file is the authoritative list; totals above are indicative per group (84 planned cases).

## 5. Entry / Exit Criteria
- **Entry:** Cycle 1 frontend+backend deliverables merged; compose stack boots; seed script runs.
- **Exit:** All automatable tests executed with evidence; failures filed as defects (severity, repro, expected/actual, requirement ID); `testcase/cycle-1-report.md` written; requirement-status recommendations emitted (implemented/verified only with QA evidence).

## 6. Risks
- Environment may not permit browser-based E2E (Playwright) — those tests become MANUAL/BLOCKED with rationale, not silently passed.
- Allowlisted command set may exclude some quality-gate commands; each BLOCKED result will name the missing capability.
- Seed user credentials are documented only in README (local env); if unavailable, dependent tests are BLOCKED, not guessed.
