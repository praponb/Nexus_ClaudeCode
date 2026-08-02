# Cycle 1 — Authentication Tests (FR-001, NFR-007; design §12)

Preconditions for all tests in this file (unless overridden):
- Compose stack running; migrations + seed applied.
- Demo users exist: `admin`, `manager`, `deptmgr`, `operator`, `employee`, `auditor` with documented dev passwords.
- API base: `http://localhost:8000/api/v1`; frontend: `http://localhost:3000`.

---

### TC-FR-001-01 — Successful login establishes secure session
- **requirement_ids:** FR-001, NFR-007
- **priority:** Critical | **type:** Functional/API | **automation_status:** AUTOMATED_CANDIDATE
- **objective:** Valid credentials create a session with hardened cookie attributes and return the user profile.
- **test_data:** `operator` user + dev password.
- **steps:**
  1. `GET /api/v1/auth/csrf` — capture `csrftoken` cookie.
  2. `POST /api/v1/auth/login` with username/password and `X-CSRFToken` header.
  3. Inspect response status, `Set-Cookie` for `sessionid`.
  4. `GET /api/v1/auth/me` with session cookie.
- **expected_result:**
  - Login returns 200 with user profile (no password/hash fields).
  - `sessionid` cookie: `HttpOnly`; `SameSite=Lax`; `Secure` when not local HTTP; session rotated (new ID vs any pre-login session).
  - `/auth/me` returns 200 with id/uuid, display name, role, scopes/capability flags.
- **status:** NOT_RUN

### TC-FR-001-02 — Invalid credentials rejected with generic message
- **requirement_ids:** FR-001, NFR-007
- **priority:** Critical | **type:** Security/API | **automation_status:** AUTOMATED_CANDIDATE
- **objective:** Failed login must not reveal whether the account exists.
- **test_data:** (a) valid username + wrong password; (b) nonexistent username.
- **steps:** Attempt login with (a), then (b); compare status codes, error envelopes, and response bodies.
- **expected_result:** Both return identical 401 with error envelope code (e.g., `AUTHENTICATION_FAILED`/`VALIDATION_FAILED`), identical generic message, no distinction between unknown-user and wrong-password; no stack trace; no user record data.
- **status:** NOT_RUN

### TC-FR-001-03 — CSRF enforced on unsafe methods
- **requirement_ids:** FR-001, NFR-007
- **priority:** Critical | **type:** Security/API | **automation_status:** AUTOMATED_CANDIDATE
- **objective:** Cookie-authenticated state-changing requests without a valid CSRF token are rejected.
- **test_data:** logged-in `operator` session.
- **steps:**
  1. Login normally; keep session cookie.
  2. `POST /api/v1/assets` (or `POST /auth/logout`) without `X-CSRFToken` header.
  3. Repeat with an invalid token; repeat with a valid token.
- **expected_result:** Missing/invalid CSRF → 403 with error envelope; valid token → request processed normally.
- **status:** NOT_RUN

### TC-FR-001-04 — Unauthenticated API access denied
- **requirement_ids:** FR-001, NFR-007
- **priority:** Critical | **type:** Security/API | **automation_status:** AUTOMATED_CANDIDATE
- **objective:** All business endpoints require authentication.
- **steps:** Without any cookies, request: `GET /auth/me`, `GET /assets`, `GET /assets/{uuid}` (any uuid), `GET /dashboard/summary`, `GET /reference-data/categories`, `GET /saved-views`, `GET /search/assets?q=x`.
- **expected_result:** All return 401 with error envelope code `AUTHENTICATION_REQUIRED`; no data leakage; no redirect HTML from the API.
- **status:** NOT_RUN

### TC-FR-001-05 — Logout terminates session
- **requirement_ids:** FR-001
- **priority:** High | **type:** Functional/API | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Login; verify `/auth/me` = 200; `POST /auth/logout` (with CSRF); retry `/auth/me` with the same cookie.
- **expected_result:** Logout returns 200/204; subsequent `/auth/me` returns 401; session cookie invalidated/expired.
- **status:** NOT_RUN

### TC-FR-001-06 — Expired session redirects to sign-in with return URL (UI)
- **requirement_ids:** FR-001, NFR-001
- **priority:** High | **type:** UI/Integration | **automation_status:** MIXED
- **objective:** 401 handling drives the SPA to `/login?next=…` and honors deep links after re-auth.
- **steps:**
  1. Login via UI; navigate to a deep link (e.g., `/assets/<uuid>`).
  2. Invalidate the session server-side (logout in second client / delete session) or wait/shorten session timeout if configurable.
  3. Trigger a navigation or API call in the first client.
  4. Complete sign-in again.
- **expected_result:** User is redirected to `/login` with `next` preserving the original URL; after successful login the user lands on the original deep link; no raw error JSON shown to the user.
- **status:** NOT_RUN

### TC-FR-001-07 — Login rate limiting / backoff
- **requirement_ids:** FR-001, NFR-007
- **priority:** High | **type:** Security/API | **automation_status:** AUTOMATED_CANDIDATE
- **objective:** Repeated failed logins are throttled per documented policy.
- **steps:** Submit 10+ rapid failed login attempts for one account from one client.
- **expected_result:** After the configured threshold, responses return 429 with error envelope code `RATE_LIMITED` and `retryable` indication; message remains generic (no account-existence leak); legitimate login succeeds after backoff window (or document the configured lockout behavior).
- **status:** NOT_RUN

### TC-FR-001-08 — Login success/failure/logout audited
- **requirement_ids:** FR-001, FR-025, NFR-009
- **priority:** High | **type:** API/Data | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Perform one failed login, one successful login, one logout as `operator`. Query the audit trail via the authorized query path (admin audit API if present, else Django shell/DB inspection as test evidence).
- **expected_result:** Three audit events exist with action types for login-failure, login-success, logout; each has actor identity (or attempted identifier for failures), UTC timestamp, outcome, correlation ID; no password material recorded.
- **status:** NOT_RUN

### TC-FR-001-09 — Sign-in page UX states (UI)
- **requirement_ids:** FR-001, NFR-001, LAY-4, LAY-5
- **priority:** High | **type:** UI | **automation_status:** MIXED
- **steps:** Open `/login` unauthenticated; submit empty form; submit wrong credentials; submit valid credentials.
- **expected_result:** Visible labels (not placeholder-only); required markers; client validation messages; server failure shown as inline alert without revealing account existence; loading state prevents duplicate submit; success navigates to dashboard or `next` target; focus management moves to error summary/alert on failure.
- **status:** NOT_RUN
