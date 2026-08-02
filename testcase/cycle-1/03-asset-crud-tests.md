# Cycle 1 — Asset Create/View/Edit Tests (FR-003, FR-004, FR-029 slice; BR-001/005/008/009; NFR-014; design §10–§11)

Preconditions: stack running; seeded reference data (categories incl. one with required category attributes, statuses incl. Draft, conditions, departments, locations); `operator` and `admin` users.

---

### TC-FR-003-01 — Create asset: happy path with server-generated tag
- **requirement_ids:** FR-003, BR-001
- **priority:** Critical | **type:** Functional/API | **automation_status:** AUTOMATED_CANDIDATE
- **test_data:** valid payload for category "Laptop" (or seeded equivalent) with all required fields; no `tag` provided.
- **steps:** As `operator`: `POST /api/v1/assets` (+CSRF, +`Idempotency-Key` if supported). Then `GET /assets/{uuid}`.
- **expected_result:** 201; server-generated unique human-readable tag; response includes `uuid`, `version: 1`, timestamps UTC; subsequent GET matches submitted data; initial status per defaults.
- **status:** NOT_RUN

### TC-FR-003-02 — Create asset: atomic side records (lifecycle + audit)
- **requirement_ids:** FR-003, FR-025, BR-003
- **priority:** Critical | **type:** API/Data | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Create asset (as TC-FR-003-01). Fetch `GET /assets/{uuid}/history`; inspect audit trail (authorized path).
- **expected_result:** Exactly one initial LifecycleEvent (type registration/created) with actor = operator, UTC timestamp; one AuditEvent with before=null/absent, after=snapshot, outcome success, correlation ID; both created atomically with the asset.
- **status:** NOT_RUN

### TC-FR-003-03 — Required-field validation with per-field errors
- **requirement_ids:** FR-003, NFR-001, spec §15
- **priority:** Critical | **type:** Validation/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** `POST /assets` with missing required fields (name, category, status, condition, department, location, acquisition type per seed config); and with invalid FK references (random UUIDs).
- **expected_result:** 400 envelope code `VALIDATION_FAILED`; `field_errors` names each offending field with a corrective message; no asset created; error count matches omissions.
- **status:** NOT_RUN

### TC-FR-003-04 — Duplicate asset tag rejected (BR-001)
- **requirement_ids:** FR-003, BR-001
- **priority:** Critical | **type:** Functional/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Create asset with explicit tag `QA-TAG-0001`; repeat create with the same tag (different name/serial). Also verify case/whitespace normalization behavior if specified.
- **expected_result:** Second create → 400/409 with stable code `DUPLICATE_TAG`; no second record; message identifies the tag conflict.
- **status:** NOT_RUN

### TC-FR-003-05 — Duplicate-detection pre-check warnings (BR-008)
- **requirement_ids:** FR-003, BR-008
- **priority:** High | **type:** Functional/API | **automation_status:** AUTOMATED_CANDIDATE
- **test_data:** existing asset with serial `SN-EXIST-1`, manufacturer+model `Acme/LaptopPro 14`.
- **steps:** `POST /assets/check-duplicates` (or documented pre-check endpoint) with (a) same serial; (b) same manufacturer+model; (c) completely novel data. Then create with (a) anyway.
- **expected_result:** (a)/(b) return 200 with non-blocking `warnings` identifying the candidate duplicates; (c) returns empty warnings; save with duplicate serial succeeds with warnings returned (unless category enforces serial uniqueness — then 400, document behavior); no automatic merging.
- **status:** NOT_RUN

### TC-FR-003-06 — Draft save permitted
- **requirement_ids:** FR-003
- **priority:** High | **type:** Functional/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Create an asset in `Draft` status omitting operational fields that are required only for non-draft statuses (per seed transition/field rules).
- **expected_result:** Draft save succeeds (201) with status Draft; fields required for active statuses still validated when transitioning out of Draft (spot-check via PATCH status change → 400 listing missing data, if transitions are in scope this cycle; otherwise document).
- **status:** NOT_RUN

### TC-FR-003-07 — Category-driven required attributes validated
- **requirement_ids:** FR-003, FR-026 (attribute definitions)
- **priority:** High | **type:** Validation/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Pick a seeded category with a required `CategoryAttributeDefinition`. POST without that attribute; POST with a wrong data type (e.g., string for `number`); POST correctly.
- **expected_result:** Missing required attribute → 400 with field error; wrong type → 400; valid → 201 and attribute stored in `category_attributes`.
- **status:** NOT_RUN

### TC-FR-003-08 — Unicode and special-character data integrity
- **requirement_ids:** FR-003, NFR-014
- **priority:** Medium | **type:** Data/API | **automation_status:** AUTOMATED_CANDIDATE
- **test_data:** name `Laptop — Ünïcodé 测试 💻`, description with emoji, newlines, and `<script>alert(1)</script>`; location notes with RTL text.
- **steps:** Create asset with the above; GET it back; render in UI detail page.
- **expected_result:** Data round-trips exactly (UTF-8); script content stored inert and rendered escaped in UI (no execution); no 500s.
- **status:** NOT_RUN

### TC-FR-003-09 — Idempotent create with Idempotency-Key (D-08, if implemented in C1)
- **requirement_ids:** FR-003, design D-08
- **priority:** Medium | **type:** API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** `POST /assets` twice with the same `Idempotency-Key` and identical body; then with the same key but a different body.
- **expected_result:** Same key + same body → single asset created, second response replays the first (same uuid); same key + different body → 409/422 per contract. If idempotency is deferred to Cycle 2, mark BLOCKED with design reference.
- **status:** NOT_RUN

---

### TC-FR-004-01 — Asset detail completeness and versioning
- **requirement_ids:** FR-004
- **priority:** Critical | **type:** Functional/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** `GET /assets/{uuid}` for a seeded asset as `admin`.
- **expected_result:** Identity (tag, name, serial, manufacturer, model, category), status, condition, department, location, custodian, dates, `version`, `created_at/updated_at` (ISO 8601 with TZ), `created_by/updated_by`; financial fields per permission (see TC-FR-002-06).
- **status:** NOT_RUN

### TC-FR-004-02 — Edit asset: happy path increments version and audits
- **requirement_ids:** FR-004, FR-025, BR-009
- **priority:** Critical | **type:** Functional/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** GET asset (version N). `PATCH /assets/{uuid}` changing name + condition with `version: N` (or `If-Match: N`). GET again; check history + audit.
- **expected_result:** 200; `version` = N+1; changes persisted; LifecycleEvent/AuditEvent record actor, UTC timestamp, before/after of changed fields only.
- **status:** NOT_RUN

### TC-FR-004-03 — Stale version → 409 VERSION_CONFLICT (BR-009)
- **requirement_ids:** FR-004, BR-009
- **priority:** Critical | **type:** Concurrency/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Two clients GET the same asset (both version N). Client A PATCHes successfully (version N+1). Client B PATCHes with version N.
- **expected_result:** Client B receives 409 with envelope code `VERSION_CONFLICT`; B's changes NOT applied (A's values intact); message prompts review/reload; conflict audited or logged per contract.
- **status:** NOT_RUN

### TC-FR-004-04 — Missing version/If-Match on update rejected or documented
- **requirement_ids:** FR-004, BR-009, design D-07
- **priority:** High | **type:** API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** `PATCH /assets/{uuid}` with neither `version` in body nor `If-Match` header.
- **expected_result:** 400/428 per contract (silent unversioned overwrite must NOT occur); behavior matches OpenAPI documentation.
- **status:** NOT_RUN

### TC-FR-004-05 — Validation errors identify field and correction
- **requirement_ids:** FR-004, spec §15, NFR-001
- **priority:** High | **type:** Validation/API | **automation_status:** AUTOMATED_CANDIDATE
- **test_data:** warranty_end before warranty_start (BR-005); invalid status/condition uuid; overlong string; malformed date.
- **steps:** PATCH the asset with each invalid payload (correct version, re-fetch between attempts).
- **expected_result:** 400 `VALIDATION_FAILED` with per-field messages explaining the rule (e.g., "warranty end must not precede warranty start"); no partial persistence of the invalid fields.
- **status:** NOT_RUN

### TC-FR-004-06 — History endpoint: reverse-chronological, actor/timestamp/type
- **requirement_ids:** FR-004, FR-029 (slice)
- **priority:** High | **type:** Functional/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Create asset → edit twice → `GET /assets/{uuid}/history`.
- **expected_result:** Events ordered newest first; each shows type, actor, UTC timestamp, meaningful summary; creation event present last; pagination envelope if list-shaped.
- **status:** NOT_RUN

### TC-FR-004-07 — History hides sensitive details by permission
- **requirement_ids:** FR-004, FR-029, NFR-008
- **priority:** Medium | **type:** Security/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** As `admin`, create/edit an asset changing a financial field. Fetch history as a role without finance permission.
- **expected_result:** Event visible but sensitive before/after values (price) masked/omitted for unauthorized role; no leakage in `details` JSON.
- **status:** NOT_RUN

### TC-FR-004-08 — UI: edit form conflict prompt (BR-009, integration rule 6)
- **requirement_ids:** FR-004, BR-009, NFR-001
- **priority:** High | **type:** UI/Integration | **automation_status:** MIXED
- **steps:** Open the same asset edit form in two browser sessions. Save in session 1. Save in session 2 (stale version).
- **expected_result:** Session 2 shows a clear conflict prompt (not silent overwrite), offers reload/review, preserves the user's entered values; no raw error JSON; correlation ID shown for support.
- **status:** NOT_RUN

### TC-FR-004-09 — UI: create/edit form behavior standards
- **requirement_ids:** FR-003, FR-004, NFR-001, LAY-4, LAY-5
- **priority:** High | **type:** UI | **automation_status:** MIXED
- **steps:** Open `/assets/new`: submit empty; fill some fields then trigger a server-side validation error; attempt navigation away with unsaved changes; double-click Save rapidly.
- **expected_result:** Required markers (text + symbol); error summary at top with focus moved to it + per-field errors; valid entries preserved after failed submit; unsaved-changes guard warns; duplicate submission prevented (single request, button busy state); duplicate-warning panel shown when pre-check warnings exist; success shows the created record or clear next step.
- **status:** NOT_RUN
