# QA Test Cases — Asset Inventory Web Application

This directory is owned by the QA agent. It contains the cross-system test plan and
test cases derived from `requirements/*` and `detail-design-specification.md`.

## Structure

```
testcase/
├── README.md                     (this file)
├── test-plan.md                  Master cross-cycle test plan
├── test-plan-cycle-1.md          Cycle 1 plan: scope, traceability, environments, entry/exit criteria
├── test-plan-cycle-2.md          Cycle 2 plan
├── test-plan-cycle-3.md          Cycle 3 plan
├── execution-status.json         Per-test-case status across all cycles (259 cases)
├── cycle-1-test-cases.json       Cycle 1 machine-readable case list
├── cycle-1-test-plan.md
├── cycle-1/                      Cycle 1 working files
├── test-cases/                   Suite-level case lists (e.g. help-guided-ui.json)
├── help-ui-mcp-run-guide.md      How to drive the Help-page suite via the Playwright MCP
└── evidence/                     Screenshots and artefacts captured during execution
```

**Execution status as of 2026-08-29** (`execution-status.json`): 259 cases —
183 passed, 69 blocked, 5 failed, 2 manual. Most blocks are "browser
unavailable" carried from the original automated runs. The Help-page suite has
since been executed against a real browser: 60 of 62 passed, with
`TC-HELP-05` (accessibility scan) and `TC-HELP-77` (forbidden-register alert)
still blocked.

> Some recorded failures are themselves stale — e.g. `TC-DEF-001-01` asserts the
> root `compose.yaml` is absent (it exists) and `TC-DEF-002-01` expects a
> `.env.example` that was removed deliberately. Re-run before acting on them.

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
