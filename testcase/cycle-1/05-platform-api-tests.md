# Cycle 1 — Platform/API Convention, Audit, Health, Security-Header Tests (FR-025 slice, NFR-005/007/009/011; STK-3; design §11, §13)

Preconditions: stack running; admin + operator users; at least one asset created and updated during the run.

---

### TC-FR-025-01 — Audit event completeness for asset create/update
- **requirement_ids:** FR-025, NFR-009
- **priority:** Critical | **type:** Data | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Perform one asset create and one update as `operator`. Retrieve the audit events (admin audit query API if delivered; otherwise direct DB/Django-shell read as evidence).
- **expected_result:** Each event contains: actor (user identity), actor_type, action, target_type/target_uuid, before/after JSON (create: before empty), outcome, correlation_id, created_at UTC.
- **status:** NOT_RUN

### TC-FR-025-02 — Hash-chain tamper evidence fields
- **requirement_ids:** FR-025
- **priority:** High | **type:** Data | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Fetch the most recent N audit events in order; recompute `record_hash` from documented canonical fields and verify `prev_hash` linkage.
- **expected_result:** `prev_hash` of each record equals `record_hash` of its predecessor; recomputed hashes match stored values (chain intact). If hash-chaining is deferred past Cycle 1, mark BLOCKED citing design §10.1 and recommend status accordingly.
- **status:** NOT_RUN

### TC-FR-025-03 — Audit read restricted; no edit/delete via application
- **requirement_ids:** FR-025, NFR-007
- **priority:** High | **type:** Security | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** As non-privileged roles, attempt to read audit events via any exposed endpoint; as `admin`, attempt HTTP PUT/PATCH/DELETE against the audit endpoint/resource.
- **expected_result:** Read restricted to authorized roles (403/404 otherwise); mutation verbs rejected (405/403/404); application exposes no edit/delete path. (DB-level UPDATE/DELETE revocation per design §10.1 is verified in TC-FR-025-04 if the DB role is available.)
- **status:** NOT_RUN

### TC-FR-025-04 — Audit table append-only at database level
- **requirement_ids:** FR-025, BR-003
- **priority:** Medium | **type:** Data/Security | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Using the application's DB role (from compose env), attempt `UPDATE` and `DELETE` on the audit_event table via psql inside the postgres container (read-only verification only — use a transaction rolled back, or verify permission denial).
- **expected_result:** UPDATE/DELETE denied for the app role, or design-documented alternative enforcement (e.g., trigger) demonstrably blocks modification; evidence captured. If the local env uses a superuser for the app (dev-only), record as an observation/defect with severity per policy.
- **status:** NOT_RUN

---

### TC-API-001 — Error envelope shape on all error classes
- **requirement_ids:** NFR-007, spec §15, design §11.2, STK-3
- **priority:** Critical | **type:** API/Contract | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Provoke: 400 (bad payload), 401 (no auth), 403 (insufficient role), 404 (random uuid), 409 (stale version), 405 (wrong method), 415/413 (bad upload if attachments stub exists — else skip), 429 (login rate limit per TC-FR-001-07).
- **expected_result:** Every non-2xx JSON response matches `{ "error": { code, message, field_errors, correlation_id, retryable } }`; codes are stable strings from the documented set; messages are user-safe (no stack traces, paths, SQL, settings).
- **status:** NOT_RUN

### TC-API-002 — Correlation ID propagation (NFR-009)
- **requirement_ids:** NFR-009, NFR-011
- **priority:** High | **type:** API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Send `X-Correlation-ID: <uuid>` on a request that succeeds and one that fails; send none on another request.
- **expected_result:** Provided ID echoed in response headers and in the error envelope; absent ID → server generates one and returns it; the ID appears in structured backend logs for those requests.
- **status:** NOT_RUN

### TC-API-003 — OpenAPI schema published and exportable
- **requirement_ids:** STK-3, design §11.1, NFR-010
- **priority:** High | **type:** Contract | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** `GET /api/v1/schema/` (authenticated or as documented); run the documented export script/command producing `backend/openapi.json`; validate the document parses (e.g., as JSON/YAML) and includes the cycle-1 endpoints, error envelope component, and pagination envelope.
- **expected_result:** Schema endpoint returns a valid OpenAPI 3.x document; exported file exists, is current (regeneration produces no diff), and covers auth, assets, search, dashboard, saved-views, reference-data endpoints.
- **status:** NOT_RUN

### TC-API-004 — UUID public identifiers; no sequential IDs exposed
- **requirement_ids:** NFR-007, design D-02, STK-3
- **priority:** High | **type:** Security/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Inspect asset/reference-data/saved-view responses and URLs; attempt `GET /assets/1`, `GET /assets/2`.
- **expected_result:** All public identifiers are UUIDs; numeric-ID guesses return 404; internal bigint PK never serialized.
- **status:** NOT_RUN

### TC-API-005 — Money representation (D-06)
- **requirement_ids:** BR-007, design D-06, STK-3 (§10 contract)
- **priority:** High | **type:** API/Contract | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Create/read an asset with `purchase_price` 1234.56 USD (as authorized role); check serialized form and a value with many decimals input (e.g., `19.999`).
- **expected_result:** Representation `{ "amount": "1234.56", "currency": "USD" }` as decimal strings; no binary float artifacts (`19.999` rejected or rounded per documented rule — never `19.998999...`); currency always present with amounts.
- **status:** NOT_RUN

### TC-API-006 — Datetime and Unicode conventions
- **requirement_ids:** BR-010, NFR-014, STK-3 (§10)
- **priority:** Medium | **type:** API/Contract | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Inspect timestamps in asset/audit responses.
- **expected_result:** All datetimes ISO 8601 with timezone (UTC `Z` or offset); consistent across endpoints; JSON is UTF-8 without mojibake for non-ASCII data.
- **status:** NOT_RUN

### TC-API-007 — Security response headers
- **requirement_ids:** NFR-007, STK-5
- **priority:** High | **type:** Security | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Inspect response headers from backend API and frontend pages (curl -i / dev tools).
- **expected_result:** `X-Content-Type-Options: nosniff`, `Referrer-Policy` set, restrictive `Content-Security-Policy` present (at least on frontend), `X-Frame-Options`/CSP `frame-ancestors 'none'`; no `Server`/`X-Powered-By` version leakage beyond acceptable defaults; CORS: `Access-Control-Allow-Origin` reflects only the allowlisted frontend origin, never `*` with credentials.
- **status:** NOT_RUN

### TC-API-008 — 500 handling: no internals leaked
- **requirement_ids:** NFR-007, spec §15
- **priority:** Medium | **type:** Security | **automation_status:** MANUAL
- **steps:** If a reliably failing endpoint/input is found during testing (or via a temporary debug trigger documented by backend), observe the 500 response.
- **expected_result:** Generic `INTERNAL_ERROR` envelope with correlation ID; no stack trace, settings, SQL, or paths; stack trace exists only in server logs.
- **status:** NOT_RUN

---

### TC-NFR-005-01 — Health endpoints unauthenticated and safe
- **requirement_ids:** NFR-005, FR-001
- **priority:** High | **type:** API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** `GET /api/v1/health/live` and `GET /api/v1/health/ready` without credentials.
- **expected_result:** Both return 200 with minimal infra-only status (e.g., `{status: "ok"}`); `ready` reflects DB connectivity; no version internals, settings, or sensitive data exposed.
- **status:** NOT_RUN

### TC-NFR-005-02 — Readiness reflects dependency failure
- **requirement_ids:** NFR-005
- **priority:** Medium | **type:** Reliability | **automation_status:** MANUAL
- **steps:** Stop the postgres container; call `/health/ready`; restart postgres; re-check.
- **expected_result:** Ready returns non-200 while DB is down and recovers after restart; live remains 200 (process alive); app recovers without manual intervention.
- **status:** NOT_RUN

### TC-NFR-011-01 — Structured logs with correlation IDs, no secrets
- **requirement_ids:** NFR-011, NFR-007
- **priority:** Medium | **type:** Observability | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Perform login + asset create; inspect backend container logs (`docker compose logs backend`).
- **expected_result:** JSON-structured entries with timestamp, level, service, correlation_id, path, status; password/token/financial values absent or masked; audit events not substituted by diagnostic logs.
- **status:** NOT_RUN
