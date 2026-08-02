# Cycle 1 — Search, List, Saved Views, Dashboard, Reference Data (FR-005, FR-006, FR-020 basic, FR-026 slice; design D-09)

Preconditions: seeded ~200 assets across multiple categories/statuses/departments/locations; seeded custodians; scoped users available.

---

### TC-FR-005-01 — Global search across supported fields
- **requirement_ids:** FR-005
- **priority:** Critical | **type:** Functional/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** As `admin`, `GET /search/assets?q=` with: (a) a known asset tag; (b) a serial number; (c) a name fragment; (d) a model; (e) a custodian name; (f) a location name.
- **expected_result:** Each query returns the matching asset(s); response uses the standard list envelope; no 500 on special characters (`%`, `_`, quotes, emoji) — treated as literal text.
- **status:** NOT_RUN

### TC-FR-005-02 — Exact tag match ranked first
- **requirement_ids:** FR-005
- **priority:** High | **type:** Functional/API | **automation_status:** AUTOMATED_CANDIDATE
- **test_data:** assets with tags such that one is an exact match and others are partial matches (e.g., tag `LT-1000` vs `LT-1000X`, `LT-10001`; create if seed lacks them).
- **steps:** `GET /search/assets?q=LT-1000`.
- **expected_result:** Exact-tag asset is the first result (or clearly flagged as exact match per contract).
- **status:** NOT_RUN

### TC-FR-005-03 — List filters: category, status, condition, department, location
- **requirement_ids:** FR-005
- **priority:** Critical | **type:** Functional/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** `GET /assets` with each filter singly; verify every returned row matches; then combine 3 filters; verify intersection semantics.
- **expected_result:** Results strictly match filter values; combined filters AND together; invalid filter values → 400 (not silent ignore).
- **status:** NOT_RUN

### TC-FR-005-04 — Sorting server-side
- **requirement_ids:** FR-005
- **priority:** High | **type:** Functional/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Sort by `tag`, `name`, `updated_at` ascending and descending; verify ordering across at least 2 pages.
- **expected_result:** Ordering correct and stable across pages; unsupported sort field → 400 or documented default.
- **status:** NOT_RUN

### TC-FR-005-05 — Pagination envelope and limits (D-09)
- **requirement_ids:** FR-005, design D-09
- **priority:** High | **type:** API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** `GET /assets` default; `?page=2`; `?page_size=100`; `?page_size=101`; `?page=9999`; `?page=0`; `?page_size=-1`.
- **expected_result:** Envelope `{count, next, previous, results}` always present; default page_size 25; page_size above max (100) clamped or 400 per contract (consistent); out-of-range page → empty results (not 500); invalid params → 400.
- **status:** NOT_RUN

### TC-FR-005-06 — Search/list respect permission scope
- **requirement_ids:** FR-005, FR-002
- **priority:** Critical | **type:** Security/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Repeat TC-FR-005-01 queries as a department-scoped user; compare `count` with admin for the same unfiltered list.
- **expected_result:** Scoped user sees strictly a subset; counts differ as expected; no out-of-scope asset appears in any page.
- **status:** NOT_RUN

### TC-FR-005-07 — UI: filter bar, chips, URL state, clear-all
- **requirement_ids:** FR-005, NFR-001, LAY-4
- **priority:** High | **type:** UI | **automation_status:** MIXED
- **steps:** On `/assets`: apply category + status filters; reload the page; copy URL into a new tab; remove one chip; Clear all.
- **expected_result:** Active filters shown as removable chips with result count; filter/sort/page state encoded in URL query params (bookmarkable, survives reload); Clear all resets; list announces changes accessibly (live region) without moving focus unexpectedly; mobile: Filter button with active count, Apply/Clear always visible in the sheet.
- **status:** NOT_RUN

### TC-FR-005-08 — UI: register responsive table↔cards and pagination
- **requirement_ids:** FR-005, NFR-002, LAY-4
- **priority:** High | **type:** UI/Responsive | **automation_status:** MIXED
- **steps:** View `/assets` at 1440px and at 390px; paginate in both.
- **expected_result:** Desktop: table with tag, name, category, status, condition, custodian/department/location, updated, sortable headers with visible sort direction, sticky header on scroll. Mobile: cards with tag, name, status badge, category/model, custodian, location, action menu; numbered pagination on desktop, prev/next on mobile; no infinite scroll; no horizontal page scroll.
- **status:** NOT_RUN

---

### TC-FR-006-01 — Saved view CRUD (own views)
- **requirement_ids:** FR-006
- **priority:** High | **type:** Functional/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** As `operator`: `POST /saved-views` (name + filter config); `GET /saved-views`; `PATCH /saved-views/{uuid}` rename; apply via list endpoint params; `DELETE /saved-views/{uuid}`.
- **expected_result:** Full CRUD works; list returns only own + published shared views; deleted view gone (404 on refetch).
- **status:** NOT_RUN

### TC-FR-006-02 — Cannot modify or delete another user's view
- **requirement_ids:** FR-006, FR-002
- **priority:** High | **type:** Security/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** User A creates a private view. User B: GET/PATCH/DELETE that view's UUID.
- **expected_result:** B gets 404 (private, not visible) or 403 (if visible but not owned) — never a successful mutation; A's view unchanged.
- **status:** NOT_RUN

### TC-FR-006-03 — Shared views published by authorized roles only
- **requirement_ids:** FR-006, FR-002
- **priority:** Medium | **type:** Security/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** As a role permitted to publish (per capability map, e.g., manager/admin): create shared view. As `employee`: attempt to publish a shared view; verify the manager's shared view is visible and usable read-only.
- **expected_result:** Authorized publish succeeds and is visible to others; unauthorized publish → 403; consumers cannot edit the shared view.
- **status:** NOT_RUN

### TC-FR-006-04 — Default view selection
- **requirement_ids:** FR-006
- **priority:** Medium | **type:** Functional | **automation_status:** MIXED
- **steps:** Mark a view as default; reopen `/assets`; change default; unset default.
- **expected_result:** Default view auto-applies on register load; changing/unsetting behaves consistently; only one default per user.
- **status:** NOT_RUN

---

### TC-FR-020-01 — Dashboard summary counts reconcile with scoped list
- **requirement_ids:** FR-020, spec §12
- **priority:** High | **type:** Functional/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** As `admin`: `GET /dashboard/summary`; independently compute total assets and by-status counts via `GET /assets` (count + filtered counts). Repeat as a scoped user.
- **expected_result:** KPI totals equal list counts for the same permission scope; by-status breakdown sums to total; no cross-scope inflation for scoped users.
- **status:** NOT_RUN

### TC-FR-020-02 — UI: dashboard KPI cards and states
- **requirement_ids:** FR-020, NFR-001, LAY-4
- **priority:** High | **type:** UI | **automation_status:** MIXED
- **steps:** Load `/` as operator; simulate backend failure (if feasible) and empty scope user.
- **expected_result:** KPI cards show label + value + context; loading skeletons while fetching; error state with Retry + correlation ID on failure; empty state explains why no data; cards link to the corresponding filtered asset list; last-refreshed timestamp shown; mobile: single column with readable 2-col KPI grid.
- **status:** NOT_RUN

---

### TC-FR-026-01 — Reference data read endpoints (all cycle-1 types)
- **requirement_ids:** FR-026
- **priority:** High | **type:** Functional/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** As `operator`: GET each of `categories`, `statuses`, `conditions`, `departments`, `locations`, `cost-centers`, `suppliers` (+ `transition-rules` if delivered).
- **expected_result:** All return 200 with seeded data, standard envelope/fields (uuid, name/code, active flag); inactive values flagged, not missing.
- **status:** NOT_RUN

### TC-FR-026-02 — Deactivate-not-delete for in-use reference values (BR-004)
- **requirement_ids:** FR-026, BR-004
- **priority:** High | **type:** Functional/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** As `admin`: attempt to delete (or deactivate) a department/location that has assets referencing it, per the admin API contract; then deactivate an unused value.
- **expected_result:** In-use value cannot be hard-deleted (405/409/400 per contract with clear message) — deactivation path offered; historical assets still display the deactivated value; deactivated value unavailable in create/edit selectors (UI spot-check).
- **status:** NOT_RUN

### TC-FR-026-03 — Reference data changes audited
- **requirement_ids:** FR-026, FR-025
- **priority:** Medium | **type:** API/Data | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** As `admin`, create + update + deactivate one reference record; inspect audit trail.
- **expected_result:** Each change produces an audit event with actor, action, before/after, timestamp, correlation ID.
- **status:** NOT_RUN
