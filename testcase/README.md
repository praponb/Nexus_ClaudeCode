# QA Test Cases — Asset Inventory Web Application

This directory is owned by the QA agent. It contains the cross-system test plan and
test cases derived from `requirements/*` and `detail-design-specification.md`.

## Structure

```
testcase/
├── README.md                     (this file)
├── test-plan-cycle-1.md          Cycle 1 test plan: scope, traceability, environments, entry/exit criteria
└── cycle-1/
    └── test-cases.json           Master machine-readable test-case list for Cycle 1
```

## Conventions

- Test IDs follow `TC-<REQID>-<nn>` per design spec §15.2 (e.g. `TC-FR-001-03`).
  Journey-level E2E tests use `TC-J<n>-<nn>`; cross-cutting API-convention tests use `TC-API-<nn>`;
  stack/installation tests use `TC-STK-<nn>`.
- Every test case carries: `test_id`, `requirement_ids`, `title`, `objective`, `priority`
  (P0 critical / P1 high / P2 medium), `type`, `preconditions`, `test_data`, `steps`,
  `expected_result`, `status`, `automation_status`.
- Status lifecycle: `NOT_RUN` → `PASSED` / `FAILED` / `BLOCKED` / `MANUAL`.
  A test is **never** marked PASSED without executed evidence (command output, screenshot,
  log excerpt) referenced in the cycle execution report.
- Automation status values:
  - `AUTOMATED_API` — backend pytest / direct HTTP against the compose stack
  - `AUTOMATED_E2E` — Playwright against the compose stack
  - `AUTOMATED_UNIT` — Vitest / pytest unit-level
  - `SEMI_AUTOMATED` — scripted part + manual verification (e.g. axe + manual keyboard pass)
  - `MANUAL` — requires human execution (documented steps retained)
- Requirement IDs: FR-001…FR-030, NFR-001…NFR-014, BR-001…BR-010 (specification.md),
  LAY-1…LAY-8 (layout.md), STK-1…STK-6 (front-back-end-stack.md).

## Cycle 1 scope reminder

Per `runs/run-1c738338ee96/cycle-1/cycle-plan.md`: auth, core data model, asset CRUD/search/
register/detail/create/edit, reference data read + basic admin API, saved views, dashboard
summary (basic counts), audit for auth + asset mutations, app shell + dark theme, E2E J-6 and
the registration slice of J-1. Tests for Cycle 2/3 features (assignment, transfer, stocktake,
import/export, approvals, notifications, reports, attachments, QR) are **out of scope** this
cycle and are not authored yet; where a stub UI exists, it must be permission-gated or marked
"coming soon" (verified by TC-FR-002-08).
