# Cycle 1 — Authorization / RBAC Tests (FR-002, BR-007, NFR-007, NFR-008; design §9.3)

Preconditions: stack running, seeded users and scopes. Department-scoped users (e.g., `deptmgr`, `operator`, `employee`) must have at least one in-scope and one out-of-scope department in seed data for scope tests. If seed scopes are absent, scope tests are BLOCKED with a defect against seed data.

---

### TC-FR-002-01 — Vertical escalation: low-privilege role cannot create assets
- **requirement_ids:** FR-002, FR-003, NFR-007
- **priority:** Critical | **type:** Security/API | **automation_status:** AUTOMATED_CANDIDATE
- **test_data:** `employee` and `auditor` sessions; valid asset payload.
- **steps:** As `employee`, `POST /api/v1/assets` with valid payload + CSRF. Repeat as `auditor`.
- **expected_result:** 403 with envelope code `PERMISSION_DENIED`; no asset created (verify via admin list count unchanged); response reveals no data.
- **status:** NOT_RUN

### TC-FR-002-02 — Auditor is read-only on all mutation endpoints
- **requirement_ids:** FR-002, NFR-007
- **priority:** Critical | **type:** Security/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** As `auditor`: `GET /assets` (expect 200); `PATCH /assets/{uuid}` with current version; `POST /assets/{uuid}/notes`; `POST /saved-views` (allowed if views are personal — document behavior); `DELETE /saved-views/{other-user-view}`.
- **expected_result:** Asset mutations denied (403); personal saved-view behavior matches design (own views allowed, others denied); no state changes observable.
- **status:** NOT_RUN

### TC-FR-002-03 — Horizontal/scope filtering on asset list
- **requirement_ids:** FR-002, FR-005, NFR-008
- **priority:** Critical | **type:** Security/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Login as `deptmgr` (department-scoped). `GET /assets` and record count and departments present. Attempt filter on an out-of-scope department (`?department=<out-of-scope-uuid>`).
- **expected_result:** List contains only assets within the user's scopes; explicit out-of-scope filter returns empty results (not other departments' data); `admin` sees the full set (contrast check).
- **status:** NOT_RUN

### TC-FR-002-04 — Out-of-scope asset detail returns 404 (no existence leak)
- **requirement_ids:** FR-002, NFR-007
- **priority:** Critical | **type:** Security/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** As `admin`, pick an asset UUID outside `deptmgr`'s scope. As `deptmgr`, `GET /assets/{that-uuid}`; also try a random nonexistent UUID.
- **expected_result:** Both return identical 404 `NOT_FOUND` envelopes — out-of-scope and nonexistent are indistinguishable; no fields leaked.
- **status:** NOT_RUN

### TC-FR-002-05 — Reference-data write restricted to admin
- **requirement_ids:** FR-002, FR-026, NFR-007
- **priority:** High | **type:** Security/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** As `operator`: `POST /reference-data/departments` (and one PATCH). As `admin`: same operations with valid payloads.
- **expected_result:** Non-admin → 403; admin → 201/200; writes audited (cross-check TC-FR-025-01).
- **status:** NOT_RUN

### TC-FR-002-06 — Financial fields hidden from unauthorized roles (BR-007)
- **requirement_ids:** FR-002, BR-007, NFR-008
- **priority:** Critical | **type:** Security/API | **automation_status:** AUTOMATED_CANDIDATE
- **test_data:** seeded asset with `purchase_price`/currency set.
- **steps:** `GET /assets/{uuid}` as `employee`/`operator` (whichever lacks `finance.view` per the capability map) and as `admin`/`manager`. Compare serialized fields.
- **expected_result:** Unauthorized roles: `purchase_price`, residual/financial fields absent (or explicitly nulled per contract — must be consistent list+detail); authorized roles: money object `{"amount": "1234.56", "currency": "USD"}` decimal-string form, never float.
- **status:** NOT_RUN

### TC-FR-002-07 — Field-level write restriction enforced server-side
- **requirement_ids:** FR-002, FR-004, BR-007
- **priority:** High | **type:** Security/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** As a role without finance permission, `PATCH /assets/{uuid}` with correct `version` attempting to set `purchase_price`.
- **expected_result:** Request rejected (403) or field ignored per documented contract — verify persisted value unchanged via authorized read; audit event does not record a financial change.
- **status:** NOT_RUN

### TC-FR-002-08 — Capability flags drive UI, backend re-enforces
- **requirement_ids:** FR-002, NFR-001
- **priority:** High | **type:** UI/Integration | **automation_status:** MIXED
- **steps:** Login as `employee` in the UI: check nav and asset pages for hidden create/edit actions; then (as in TC-FR-002-01) attempt the same action directly against the API.
- **expected_result:** UI hides unauthorized actions (navigation, buttons); direct API attempt still denied; no console errors or broken layout from hidden elements.
- **status:** NOT_RUN

### TC-FR-002-09 — Scope applied to search and dashboard
- **requirement_ids:** FR-002, FR-005, FR-020
- **priority:** High | **type:** Security/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** As scoped user: `GET /search/assets?q=<term-matching-out-of-scope-asset>`; `GET /dashboard/summary`. Compare totals with admin view.
- **expected_result:** Search returns no out-of-scope assets; dashboard aggregates reflect only permitted records (no misleading cross-scope totals).
- **status:** NOT_RUN

### TC-FR-002-10 — Deferred modules inaccessible
- **requirement_ids:** FR-002, cycle-plan non-goals
- **priority:** Medium | **type:** Security/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** As `admin` and as `operator`, probe Cycle-2+ routes/endpoints if any stub exists: `/api/v1/assets/{uuid}/assign`, `/api/v1/stocktakes`, `/api/v1/imports`, `/api/v1/reports`, `/api/v1/admin/users`, and frontend routes `/imports`, `/reports`, `/admin/users`.
- **expected_result:** Either 404 (not implemented) or 403 with a clear "not available" state; never 200 with functional behavior; UI shows an accessible "coming soon" empty state or hides the entry.
- **status:** NOT_RUN

### TC-FR-002-11 — Session-cookie auth only; no tokens in browser storage
- **requirement_ids:** FR-002, NFR-007, STK-5
- **priority:** Medium | **type:** Security/UI | **automation_status:** MANUAL
- **steps:** After UI login, inspect browser dev tools: localStorage, sessionStorage, cookies.
- **expected_result:** No access/refresh tokens or sensitive profile data in web storage; only HttpOnly session/CSRF cookies; no secrets in page source or network responses.
- **status:** NOT_RUN
