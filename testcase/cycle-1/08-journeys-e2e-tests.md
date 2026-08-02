# Cycle 1 — End-to-End Journey Tests (J-6; J-1 registration slice; design §3.2)

Preconditions: full stack running with seed data; Playwright or manual browser; test credentials from README.

---

### TC-J6-01 — Sign in, search, and open an asset (J-6)
- **requirement_ids:** FR-001, FR-005, FR-004
- **priority:** Critical | **type:** E2E | **automation_status:** MIXED
- **test_data:** known seeded asset tag (record at runtime from the register).
- **steps:**
  1. Open app root unauthenticated → redirected/presented with sign-in.
  2. Sign in as `operator`.
  3. Land on dashboard; KPIs load.
  4. Use global search with the asset tag → exact match first.
  5. Open the asset → detail page shows identity header, status/condition badges, overview.
  6. Open history tab → registration event visible.
  7. Sign out → returned to sign-in; protected route now redirects.
- **expected_result:** Journey completes without errors; each step shows correct state (loading → content); sign-out fully terminates access.
- **status:** NOT_RUN

### TC-J6-02 — Deep link through authentication
- **requirement_ids:** FR-001, FR-005
- **priority:** High | **type:** E2E | **automation_status:** MIXED
- **steps:** While logged out, open `/assets/<known-uuid>` directly; complete sign-in.
- **expected_result:** Redirected to sign-in with `next` preserved; after login lands on the requested asset detail (not the dashboard default).
- **status:** NOT_RUN

### TC-J6-03 — Scoped user journey
- **requirement_ids:** FR-001, FR-002, FR-005, FR-020
- **priority:** High | **type:** E2E | **automation_status:** MIXED
- **steps:** Sign in as `deptmgr` (scoped); view dashboard KPIs; open register; search for a known out-of-scope asset tag.
- **expected_result:** Dashboard and register show only in-scope data; out-of-scope search yields a clear no-results state (not an error); no unauthorized actions visible.
- **status:** NOT_RUN

---

### TC-J1-01 — Register a new laptop (J-1 registration slice)
- **requirement_ids:** FR-003, FR-004, BR-001, BR-008
- **priority:** Critical | **type:** E2E | **automation_status:** MIXED
- **test_data:** laptop category; serial matching an existing asset (to trigger duplicate warning); then corrected serial.
- **steps:**
  1. Sign in as `operator`; open `/assets/new` (via quick-create or register action).
  2. Select laptop category → category-driven fields render.
  3. Submit with missing required fields → correct errors; verify values preserved.
  4. Enter duplicate serial → duplicate warning panel appears (non-blocking).
  5. Correct serial; save.
  6. Land on created asset detail; verify server-generated tag, status, and history registration event.
  7. Return to register; find the asset via search by tag.
- **expected_result:** Form behavior per TC-FR-004-09; duplicate warning displayed before save; asset created with unique tag; registration lifecycle event shown in history; asset searchable immediately.
- **status:** NOT_RUN

### TC-J1-02 — Concurrent edit conflict during registration workflow (BR-009)
- **requirement_ids:** FR-004, BR-009
- **priority:** High | **type:** E2E | **automation_status:** MIXED
- **steps:** Two sessions open the same asset edit page (created in TC-J1-01). Session A saves a change. Session B saves a different change.
- **expected_result:** Session B sees a clear conflict prompt with option to reload/review; no silent overwrite; after reload, B can re-apply intentionally.
- **status:** NOT_RUN

### TC-J1-03 — Draft save and resume (if Draft flow in UI)
- **requirement_ids:** FR-003
- **priority:** Medium | **type:** E2E | **automation_status:** MIXED
- **steps:** Start `/assets/new`, fill minimal draft fields, save as Draft; find the draft in the register (status filter Draft); reopen and complete registration.
- **expected_result:** Draft saved with Draft status; editable later; completing required fields allows saving to an active status; audit trail shows both events. If the UI defers draft to a later cycle, mark BLOCKED with reference.
- **status:** NOT_RUN
