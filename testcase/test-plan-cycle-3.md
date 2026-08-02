# Cycle 3 Test Plan — Asset Inventory Web Application

- **Version:** 1.0 (Cycle 3 design phase)
- **Sources:** `detail-design-specification.md` Rev 1.2 (§18 Delivery Plan — Cycle 3, §2.5 carried-defect register, §11.3 endpoint status). NOTE: `runs/run-1c738338ee96/cycle-3/cycle-plan.md` was not present in the workspace at design time (same as Cycle 2); scope derives from the approved design Rev 1.2 and will be reconciled if the plan file appears.
- **Owner:** QA agent

## 1. Scope

### 1.1 Cycle 3 delivers (per design §18 Rev 1.2)
1. **Defect closure first:** ADR-006 bootstrap auto-copy in `scripts/dev-up.sh` (closes DEF-101/DEF-102 procedurally); DEF-103 uv.lock if a uv-capable environment exists; DEF-005 npm-audit disposition (still allowlist-blocked).
2. **FR-010 completion:** `GET /reservations` (scoped, `overdue=true` filter) + `/reservations` page.
3. **FR-024 approvals** incl. separation of duties, approve/reject/return with comments, immutable history.
4. **FR-023 notifications** in-app center + email when SMTP configured; dedupe; preferences; mandatory non-disableable.
5. **FR-021 reports catalog** (14 default reports, filters/date ranges, reconciliation, authorized export).
6. **Admin:** FR-027 user admin (roles/scopes/activate/deactivate, final-admin protection), FR-026 admin UI polish, FR-030 archiving/retention (legal hold).
7. **FR-014 retirement/disposal/reopen** with BR-006 blockers (J-5), Idempotency-Key on retire/dispose/reopen.
8. **Mandatory backend tests** (QA findings, §2.5): FR-028 queue coverage, dashboard KPI completion (TC-FR-020-04), idempotency replay on transfer/return/reserve.
9. **Hardening:** NFR-004/006 performance at planning volumes (~100k-asset generation command), NFR-012 backup/restore procedure + drill, security scan + fixes, release docs + release-readiness statement.
10. **Final attempt** at responsive/a11y/E2E execution (else documented manual procedures per §17).

### 1.2 QA housekeeping this cycle
- Renumber duplicate `TC-FR-020-01` in `activity-dataquality.json` → `TC-FR-020-07` (dashboard.json owns 01–06).

### 1.3 Out of scope
Offline stocktake (D-03), OIDC production integration (D-01), light theme (D-05), employee self-service reservation requests (post-v1 per §14 rule 7), native mobile/RFID/etc. (§1.3).

## 2. New Suite Files (Cycle 3)

| Suite file | Requirements | Focus |
|---|---|---|
| `test-cases/defect-closure-c3.json` | DEF-101/102 (ADR-006), DEF-103, DEF-005 | Bootstrap auto-copy verification, uv.lock, npm-audit disposition |
| `test-cases/reservations.json` | FR-010 | Scoped list, overdue filter, page UI, regression on overlap rules |
| `test-cases/approvals.json` | FR-024, FR-008, FR-014 | Approval lifecycle, separation of duties, immutability, effect on underlying actions |
| `test-cases/notifications.json` | FR-023, NFR-008 | In-app center, dedupe, read, preferences, mandatory vs optional, deep links, email/failure logging |
| `test-cases/reports.json` | FR-021, FR-012, FR-002 | 14 reports, filters, totals reconciliation, scoped visibility, authorized export |
| `test-cases/admin.json` | FR-027, FR-030, FR-026, FR-025 | User admin, final-admin protection, audit-events read API, retention/hold |
| `test-cases/retirement.json` | FR-014, BR-006, BR-003, D-08 | Retire/dispose/reopen, DISPOSAL_BLOCKED, terminal state, reopen justification, J-5 |
| `test-cases/hardening-c3.json` | NFR-004, NFR-006, NFR-012, NFR-007, FR-028, FR-020 | Mandatory backend tests, perf at volume, backup/restore drill, security scan, release readiness |

Existing C1/C2 suites remain valid; previously BLOCKED browser/Docker cases get their final execution attempt.

## 3. Environment & Preconditions
Unchanged from C2 plan. Additionally: volume-generation command output (~100k assets) for perf tests; SMTP stub/config for notification email tests; backup/restore procedure document for the drill.

## 4. Entry / Exit Criteria
- **Entry:** all C2 gates still green; ADR-006 script change merged; C3 endpoints in OpenAPI (drift guard green).
- **Exit:** all Critical/High executed or explicitly BLOCKED/MANUAL with justification; DEF-101/102/103 disposition recorded; `testcase/cycle-3-report.md` + release-readiness input filed.

## 5. Evidence / Status Policy
Unchanged: no PASSED without executed evidence; `NOT_RUN | PASSED | FAILED | BLOCKED | MANUAL`.
