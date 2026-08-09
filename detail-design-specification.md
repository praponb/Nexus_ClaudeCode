# Detail Design Specification — Asset Inventory Web Application

- **Document:** `detail-design-specification.md`
- **Version:** 1.2 (Cycle 2 — review revision)
- **Status:** Active design baseline
- **Sources:** `requirements/specification.md`, `requirements/layout.md`, `requirements/front-back-end-stack.md`

---

## 1. Goals, Scope, and Non-Goals

### 1.1 Goals

Build a secure, responsive, dark-themed web application that is the single source of truth for company assets across their lifecycle: registration, assignment, transfer, return, maintenance, verification (stocktake), retirement, and disposal — with full audit history, role/scope-based access control, dashboards, reports, CSV import/export, and notifications.

### 1.2 In Scope (initial release)

Per `specification.md` §4.1: authn/authz, asset registration/editing, unique tags, configurable reference data, assignment/transfer/return/reservation/checkout, status/condition management, maintenance records, warranty/expiry tracking, retirement/loss/theft/disposal workflows, attachments/notes/images, search/filter/sort/pagination, barcode/QR representation and browser-based scanning, CSV bulk import/export, dashboard/reports/saved views, stocktake sessions, notifications, full audit history, validation and duplicate detection, responsive accessible UI.

### 1.3 Non-Goals (initial release)

Per `specification.md` §4.2: native mobile apps, network device discovery, remote control/software deployment, procurement/PO processing, accounting/depreciation/GL posting, advanced contract management, GPS tracking, RFID hardware integration, external customer asset management, predictive maintenance. Architecture must not preclude these later.

### 1.4 Delivery strategy and current state (updated in Rev 1.2)

Original three-cycle sequencing: C1 = foundation + core asset workflows; C2 = operations; C3 = hardening. The workspace contains a feature-complete implementation of all three cycles (provenance: run `run-1c738338ee96`, adopted in Rev 1.1), with executed QA evidence of backend 155 pytest + frontend 88 Vitest tests green at adoption time.

**Cycle-2 review finding (Rev 1.2):** this run's cycle-2 work closed the two release-gating engineering items, verified by workspace inspection:

- **DEF-104 closed:** npm-audit critical transitive dev dependency fixed — `happy-dom` bumped to `^20.11.2`, `npm audit fix` executed, re-audit reports **0 vulnerabilities**; documented in `frontend/README.md` "Governance & Vulnerability Audit (DEF-104)". Frontend unit suite now 101 tests (was 88).
- **DEF-103 / ADR-003 closed:** `backend/uv.lock` committed (revision 3 lockfile; `uv sync --frozen` builds are now reproducible).

**New risk introduced (I-10):** the fresh `uv.lock` resolved **Django 6.1 / DRF 3.18.0** while all executed backend test evidence (155 tests) was gathered against **Django 6.0.7 / DRF 3.17.1**. The frozen dependency set has not been regression-tested; cycle 3 must either verify the suite against the locked versions or constrain the lock to Django 6.0.x per the stack version policy.

**Process issue persists (I-8):** this run's cycle-2 agent summaries and QA execution reports were again not filed under `runs/run-a1e626552a49/cycle-2/`. Cycle 3 makes filing them a hard DoD item.

Remaining for cycle 3 (final): re-execution of all gates against the locked workspace with evidence filed under this run; the still-missing activity-feed union (FR-029) and notification email-path (FR-023) tests; duplicate QA test-ID renumber; the consolidated environment-limited verification register; final per-requirement traceability and release-readiness statement.

---

## 2. Assumptions and Unresolved Questions

### 2.1 Assumptions adopted (from `specification.md` §20, confirmed for design)

1. Internal organizational use; English UI only (i18n-ready structure).
2. No external OIDC provider is available in the generated environment. **Decision:** production-grade session-cookie authentication backed by Django is the built-in mechanism; an OIDC integration seam (settings-driven) is designed but not wired to a live provider (§15). Local auth is inert in production unless double opt-in (`LOCAL_AUTH_ENABLED` + `LOCAL_AUTH_ALLOW_IN_PRODUCTION`).
3. CSV is sufficient for bulk exchange; UTF-8 with BOM-tolerant parsing.
4. Scanning uses browser camera APIs with manual entry fallback; no dedicated hardware.
5. Financial depreciation/accounting is out of scope; monetary fields are stored as decimal + ISO currency, visibility-restricted.
6. Approval workflows are configurable (per-transition `requires_approval`, global `APPROVALS_ENABLED=false` escape hatch) with sensible defaults (disposal requires approval; transfers optional). Separation of duties defaults on.
7. Planning volume: 100k assets, 5k users, 250 concurrent users, 1M lifecycle/audit events, 25k-row imports.
8. Hosting platform is not fixed; delivery targets container images runnable under Docker Compose locally, documented for generic container hosting.

### 2.2 Detected issues in inputs and their resolutions

| # | Issue | Resolution |
|---|-------|------------|
| I-1 | Stack doc mandates Nuxt 4, Django 6.0, PostgreSQL 18, which may postdate available stable releases at implementation time. | Stack doc §4 rule 4 applied. Delivered: Nuxt 4, postgres:18 image, Django 6.x (see I-10 for the 6.0→6.1 lockfile drift under cycle-3 verification). Backend range `>=5.2,<6.2` permits pinning 5.2 LTS with an ADR where required. |
| I-2 | OIDC "preferred" but no provider defined; local auth "may be supplied". | Session-cookie auth shipped as default behind an auth-backend seam; OIDC settings optional; local auth production-gated (D-01/D-13). |
| I-3 | Malware scanning of attachments conditional ("when available"). | Attachment validation (type/extension/signature/size) shipped; scanner-service integration remains a deployment decision. |
| I-4 | `requirements/README.md` "starts empty" placeholder. | Template boilerplate, not a requirement. |
| I-5 | Offline stocktake undecided. | Excluded from initial release; observation provenance fields preserved for later offline queueing. |
| I-6 | Tag vs serial-number uniqueness ambiguity. | Tags globally unique forever (BR-001, DB-enforced, `409 DUPLICATE_TAG`); serial uniqueness configurable per category; warning-level duplicate detection otherwise. |
| I-7 | Dashboard targets (3 s) vs 1M-event audit volumes. | Scoped aggregate endpoint + indexed/paginated feeds; N+1 guard test; `generate_volume` for planning-volume datasets. |
| I-8 | Agent summaries/QA reports for this run are repeatedly not filed under `runs/run-a1e626552a49/cycle-*/` (observed in cycles 1 and 2); review relies on workspace inspection and a prior run's artifacts. | Standing process defect. Cycle 3 DoD makes filing summaries/reports under the current run directory a hard requirement with named file paths. |
| I-9 | The QA/implementation environment has no Docker and no browser runner; E2E, responsive/a11y matrix, compose boot, backup drill, and perf-at-volume cannot be executed here. | Standing constraint. Tracked as BLOCKED (never silently skipped) and consolidated into the environment-limited verification register (cycle 3) for release sign-off. |
| I-10 | **(Rev 1.2)** The newly committed `backend/uv.lock` resolved Django 6.1 / DRF 3.18.0, but all executed backend evidence was gathered on Django 6.0.7 / DRF 3.17.1 (`backend/README.md` still cites 6.0.7). | Cycle 3 must run the full gate suite against the frozen lock set and update the README's verified-versions claim; if incompatibilities appear, constrain the lock to Django 6.0.x per stack doc §4 rule 4 and record an ADR. |

### 2.3 Open questions deferred to the product owner (do not block the build)

Tag format/label dimensions beyond the default (`AST-000001`, QR, 50×25 mm label), final permission matrix per organization, notification channels and timing, retention periods, RTO/RPO confirmation, whether logical assets (licenses) are enabled, live HR/finance integrations. Defaults are chosen in this design and are configurable.

---

## 3. Personas and User Journeys

Personas (from `specification.md` §5): **System Administrator**, **Asset Manager**, **Department Manager**, **Inventory Operator/Technician**, **Employee/Custodian**, **Auditor (read-only)**.

The five user journeys in `specification.md` §11 (register-and-assign, transfer between offices, stocktake, repair-and-return-to-service, retire-and-dispose) plus sign-in/deep-link (J-6) are the canonical E2E test scenarios. All are implemented at API level with executed tests; browser-level E2E remains environment-blocked (I-9).

---

## 4. Functional Requirements and Acceptance Criteria

Requirement IDs `REQ-F001`–`REQ-F030` map 1:1 to `specification.md` FR-001–FR-030; acceptance criteria are inherited verbatim from the source and are not weakened. Business rules BR-001–BR-010 become `REQ-B001`–`REQ-B010`. Design elaborations below add the implementation contract.

### 4.1 Core lifecycle rules (design elaboration)

- **Asset creation (F003):** `POST /api/v1/assets/` validates category-configured required fields; the tag is server-generated when omitted (or validated for uniqueness when supplied); duplicate detection runs via `POST /api/v1/assets/check-duplicates/` (and the edit-time variant) returning candidate warnings — never auto-merging (BR-008). Draft save allowed with `status=Draft`. Create response shape: `201 {"asset": {...}, "warnings": [...]}`.
- **Transitions:** `LifecycleStatus.allowed_transitions` is evaluated in the service layer; invalid transition → `409 STATUS_TRANSITION_INVALID`. Controlled transitions require `reason` and, when the transition rule sets `requires_approval`, return `202 {"approval": {...}}` and mutate nothing until the approval decision executes atomically.
- **Concurrency (BR-009):** mutable entities carry `version`; updates send `If-Match: <version>` or `version` in the body; stale → `409 VERSION_CONFLICT`; missing → `400`. UI offers a reload-and-review flow.
- **Idempotency (D-08):** `Idempotency-Key` supported on asset create and all lifecycle/transition POSTs (assign, transfer, return, reserve, maintenance create, stocktake observation, retire/dispose/reopen). Same key + same payload within 24 h replays the original response; key reuse with a different payload → `409 IDEMPOTENCY_KEY_REUSED`. Verified by executed replay tests.

### 4.2 Notifications (F023)

In-app notification center (`GET /notifications`, mark-read idempotent, own-only isolation), per-user preferences with mandatory compliance types non-mutable (`400` on mute attempt), dedupe per event, daily warranty/maintenance reminder task. Email is sent only when SMTP is configured; delivery failures are logged without content. **Evidence gap (carried to cycle 3):** the SMTP send/failure path needs a locmem-backend test.

### 4.3 Stocktake (F022)

`StocktakeSession` snapshots expected items at start; operators record observations (scan or manual); the reconciliation service computes found / not-found / unexpected / duplicate-scan / moved / condition-mismatch; master-data updates apply only after authorized review, each emitting lifecycle + audit events; closing requires permission and retains the variance report. Offline queueing excluded (I-5) with provenance fields preserved.

### 4.4 Import/export (F018/F019)

Imports: template → upload → server-side parse/validate (cells as text, no formula execution) → preview with row/field errors → commit with explicit duplicate policy (`reject|update|create`) and partial-success policy → auditable result file (created/updated/skipped/failed). Exports: honor active filters and field permissions, CSV UTF-8 with formula-injection mitigation (dangerous leading characters prefixed), audited, asynchronous for large volumes via Celery with job status.

---

## 5. Non-Functional Requirements

`REQ-N001`–`REQ-N014` map to `specification.md` NFR-001–NFR-014. Design specifics:

- **Performance (NFR-004 refined):** p75 dashboard < 3 s, p75 filtered search < 2 s, p75 asset detail < 2 s, interaction feedback < 500 ms on the planning baseline (100k assets). Delivered mitigations: indexed queries, list endpoint N+1-bounded by test (≤5 queries), `generate_volume` for volume datasets. Full perf-at-volume run remains environment-blocked (I-9).
- **Availability (NFR-005):** stateless web processes, `/healthz/` + `/readyz/` (the only unauthenticated endpoints), transactional integrity for all multi-record lifecycle writes.
- **Localization (NFR-014):** English catalog, i18n-ready structure; UTC storage, ISO 8601 transport, client-locale rendering; money = decimal string + ISO 4217.
- **Browser support (NFR-013):** latest two stable majors of Edge/Chrome/Firefox/Safari — verification environment-blocked (I-9).

---

## 6. Page Inventory and Navigation

Role-aware navigation; inaccessible modules are hidden in the UI **and** denied in the API. All pages below are delivered; browser-level verification is pending (I-9).

| Route | Page | Roles (minimum) | Status |
|---|---|---|---|
| `/login` | Sign in | public | delivered |
| `/` | Dashboard (KPIs, ranked lists, tasks, data-quality link) | all authenticated | delivered |
| `/assets` | Asset register (table/cards, filters, saved views, export view) | all (scoped) | delivered |
| `/assets/new`, `/assets/[id]/edit` | Create/edit asset | Operator+ | delivered |
| `/assets/[id]` | Asset detail (identity header, finance gating, tabs, full activity feed) | all (scoped, field-restricted) | delivered |
| `/assets/[id]/assign`, `/transfer`, `/return` | Workflow forms/dialogs | Operator+ | delivered |
| `/scan` | Scanner (qr-scanner + BarcodeDetector fallback) + manual entry | Operator+ | delivered (camera path browser-blocked) |
| `/reservations` | Reservations list with overdue filters | Operator+ | delivered |
| `/maintenance` | Maintenance work queue | Operator+ | delivered |
| `/stocktakes`, `/stocktakes/[id]` | Stocktake list/session/count/reconcile/close | Manager/Operator | delivered |
| `/approvals` | Approval inbox (pending/history, decision dialogs) | Dept Manager+ | delivered |
| `/reports`, `/reports/[type]` | Reports catalog (14 types) + viewer | per report permission | delivered |
| `/imports`, `/exports` | Bulk jobs (wizard, async status, result files) | Manager/Operator | delivered |
| `/notifications` | Notification center + preferences | all | delivered |
| `/data-quality` | Data-quality work queue (errors vs warnings) | Manager/Operator | delivered |
| `/admin/*` | Users, reference data, transition rules, audit search, retention policy | Admin | delivered (API verified; UI browser-blocked) |
| `/help`, `/403`, `/404`, `/error` | Support pages | public/authenticated | delivered |

Navigation: desktop persistent collapsible sidebar; tablet collapsed icons/drawer; mobile bottom nav (Home, Assets, Scan, Tasks, More) + drawer. Breadcrumbs on desktop; mobile back action. Filters/sort/pagination in URL query params; saved views persist server-side.

---

## 7. Responsive and Accessibility Requirements

- Breakpoints (guidance): 320–479, 480–767, 768–1023, 1024–1439, ≥1440. Usable at 320 px without page-level horizontal scroll; 200% zoom; touch targets ≥ 44×44 px; safe-area insets; dialogs become full-screen sheets on compact screens.
- Desktop asset list = data table (sticky header, sortable, keyboard-reachable actions); mobile = summary cards. No harmful infinite scroll.
- WCAG 2.2 AA: skip link, landmarks, logical tab order, visible focus ring, focus containment/restoration in modals, Escape dismissal, associated labels/errors, live-region announcements, no color-only meaning (icon + text badges — unit-tested), reduced-motion support.
- QA matrix (layout.md §30): the 8-viewport × 10-page-type matrix remains the acceptance standard; it is currently **environment-blocked** (I-9) and will be consolidated in the cycle-3 verification register.

---

## 8. Theme and Visual Design

Dark theme is the default and only required theme; tokens exactly per `layout.md` §5.2 implemented as Tailwind `@theme` tokens — never hard-coded per component; dark `color-scheme` set in SSR head (no unthemed flash). Status presentation: icon + text label + semantic treatment. Typography: system sans-serif, 16 px body, 14 px minimum, monospace for identifiers. Print styles: light background, no chrome, scannable codes at label size (50×25 mm QR label delivered; output evidence spot-check in cycle 3). **Deviation (delivered):** hand-rolled accessible components instead of the Nuxt UI library — explicitly permitted by layout.md §31; ADR-002.

---

## 9. Frontend Architecture

### 9.1 Stack and structure

Nuxt 4 + Vue 3 Composition API + TypeScript strict, `<script setup lang="ts">`, Tailwind CSS v4, ESLint flat config, Vitest + Vue Test Utils (101 tests green at Rev 1.2), Playwright + axe-core specs authored (environment-blocked). **Deviation:** npm + `package-lock.json` instead of pnpm (ADR-001).

### 9.2 Rendering strategy

SSR shell + client-only private data fetching; no private inventory data rendered into SSR payloads; `/login`, `/help`, error pages may SSR.

### 9.3 State management

Typed service modules + composables (`useAuth`, `usePermissions`, `useReferenceData`, `useAssetFilters`, `useSavedViews`, `useToast`) over a single API client; backend is the source of truth; filters/pagination in URL query params.

### 9.4 API client contract (delivered as `useApi`)

One configurable base URL, `X-Correlation-ID` per request, `X-CSRFToken` on unsafe methods, credentials included, 15 s timeout, **GET-only retry** (unsafe methods never retried — pairs with Idempotency-Key), error envelope → typed `ApiError`, 401 → session-expired redirect preserving deep link.

### 9.5 Component hierarchy

AppShell (sidebar/bottom-nav/topbar), PageHeader, KpiCard, AssetTable/AssetCardList, badges, FilterBar/Drawer, AssetIdentityHeader, AssetActivityTimeline, form sections, StickyActionBar, ConfirmActionDialog, sheets, workflow forms — delivered as project-specific accessible components (ADR-002).

### 9.6 Frontend testing

Vitest suite (101 tests: error mapping, filters, badges, empty/alert/pagination, scan states, reservation/report logic, activity timeline and offline-state additions from cycle 2). Playwright E2E specs authored but environment-blocked (I-9).

---

## 10. Backend Architecture

### 10.1 Stack and project layout

Django 6.x + DRF + Python ≥3.12 + Psycopg 3; drf-spectacular OpenAPI (committed `backend/openapi.json` with drift-guard test); Celery + Redis (eager fallback in local/test); django-storages for S3-compatible production storage, local media in dev; Argon2 password hashing. **`backend/uv.lock` is committed (Rev 1.2)**; Docker builds use `uv sync --frozen`. Locked versions (Django 6.1 / DRF 3.18.0) are pending regression verification (I-10). Apps: `core`, `accounts`, `reference_data`, `assets`, `assignments`, `maintenance`, `stocktakes`, `bulk`, `approvals`, `notifications`, `audit`, `reporting`.

### 10.2 Service boundaries

Serializers = representation + boundary validation. Multi-record lifecycle behavior in explicit services under `transaction.atomic()` with row locking where invariants require it; every transition emits `LifecycleEvent` + `AuditEvent` atomically. No business side effects in signals.

### 10.3 Cross-cutting

- Correlation-ID middleware (`X-Correlation-ID` accepted/generated, echoed, attached to logs and errors).
- Error envelope: `{"error": {code, message, field_errors, correlation_id, retryable}}`.
- Pagination: `?page=&page_size=` (default 25, max 100), envelope `{count, next, previous, results}`.
- **Audit trail is hash-chained:** each `AuditEvent` links to its predecessor via SHA-256; `verify_chain()` detects tampering; no mutation surface in the API schema.
- Rate limiting via working scoped throttles (`ScopedSimpleRateThrottle`; login 429 `RATE_LIMITED`, search/import/export).
- Structured logging; Celery jobs idempotent with bounded retries and persisted status.

---

## 11. Data Model

All entities: UUID PK, `created_at`/`created_by`, `updated_at`/`updated_by`, `version` where mutable; tz-aware UTC timestamps.

### 11.1 Core entities (delivered)

- **User** (custom) with role + organizational scope (departments/locations); scopeless operators see only assets they custody. Roles: `admin`, `asset_manager`, `dept_manager`, `operator`, `employee`, `auditor`.
- **Reference data:** Category (subcategories, required-fields config, serial-uniqueness flag), LifecycleStatus (allowed transitions, requires_reason/approval flags), Condition, Location (site→building→floor→room), Department, CostCenter, Supplier, DisposalMethod, MaintenanceType. **In-use values deactivate, never hard-delete (BR-004)** — test-verified; deactivations audited.
- **Asset:** full attribute set per spec §7.2 (identity, ownership, location, lifecycle, purchase, warranty/service, technical, category attributes JSON validated against category definitions, governance incl. `legal_hold`). Tag globally unique across all states; `AssetTagSequence` generates `AST-000001`-form tags.
- **Assignment:** one active primary assignment per asset via partial unique index (BR-002), acknowledgement tracking, expected-return/overdue handling.
- **LifecycleEvent:** immutable, typed, actor + correlation ID, from/to status.
- **AuditEvent:** append-only, hash-chained, before/after snapshots (sensitive fields masked), service identities supported.
- **Operations entities (delivered):** MaintenanceRecord, Reservation (overdue identification via `overdue=true`), ExceptionReport, ApprovalRequest (separation of duties, immutable decisions), StocktakeSession + ExpectedItem + Observation, Attachment (validated, authorized downloads), Note, Notification + Preference, SavedView, ImportJob/ExportJob, DataQualityIssue queue.

### 11.2 Indexes and constraints

Unique asset tag; per-category serial uniqueness; partial unique active assignment; indexes on status, condition, custodian, department, location, warranty end, next maintenance due, updated_at; trigram-supported global search with exact-tag-first ranking; lifecycle/audit (asset, timestamp) indexes. Date-consistency constraints (BR-005) at DB and service layers.

### 11.3 Migrations and seed data

Django migrations only; drift guard test. `seed_dev` idempotent: 13 statuses, 6 conditions, ≥8 departments, ≥12 locations, 6 demo users (env-provided passwords), 200 assets with history. `generate_volume` creates planning-volume datasets.

---

## 12. API Contracts (v1)

Base: `/api/v1/` with **DRF-standard trailing slashes on all endpoints**. JSON in/out; ISO 8601 datetimes; money `{"amount": "1234.56", "currency": "USD"}`; related resources write as UUID strings and read as compact objects; error/pagination envelopes per §10.3; idempotency and concurrency per §4.1.

Endpoint families (authoritative contract = committed `backend/openapi.json`, drift-guarded):

| Family | Notes |
|---|---|
| `/auth/login/`, `/auth/logout/`, `/auth/csrf/`, `/auth/me/` | Session auth; `me` returns profile, role, scopes, capabilities (incl. `finance.view`) |
| `/assets/` CRUD, `/assets/check-duplicates/`, transitions, assign/transfer/return, retire/dispose/reopen, activity, attachments, notes, QR label | No DELETE on asset detail (archive only); approval-gated actions return 202 |
| `/reservations/` | Incl. `overdue=true` filter |
| `/maintenance/`, `/stocktakes/…`, `/approvals/` + decide actions, `/imports/`, `/exports/`, `/notifications/` + preferences, `/saved-views/` | Same conventions |
| `/dashboard/summary/` | Scoped KPIs with `generated_at`; non-misleading totals |
| `/reports/` catalog (14 types) + `/reports/{type}/` | Scoped, finance-gated, date filters, audited CSV export with injection mitigation |
| `/reference/{kind}/` | Admin write; deactivate-not-delete |
| `/admin/users/`, `/admin/audit-events/` | `409 LAST_ADMIN` guard; audit read restricted (`audit.read`) |
| `/healthz/`, `/readyz/` | Only unauthenticated endpoints |

Stable error codes include: `VALIDATION_FAILED`, `PERMISSION_DENIED`, `NOT_FOUND` (no existence leak), `VERSION_CONFLICT`, `STATUS_TRANSITION_INVALID`, `DUPLICATE_TAG`, `IDEMPOTENCY_KEY_REUSED`, `DISPOSAL_BLOCKED`, `APPROVAL_ALREADY_DECIDED`, `SEPARATION_OF_DUTIES`, `LAST_ADMIN`, `RATE_LIMITED`.

---

## 13. Frontend/Backend Integration Rules

1. Django owns business rules, authorization, persistence, canonical validation; Nuxt owns presentation and usability-level validation.
2. The committed OpenAPI schema is the contract: frontend types are generated from it; a drift-guard test fails on schema changes; breaking changes require a new version path.
3. Correlation IDs propagate Nuxt → Django → Celery; surfaced in UI error states as the support reference.
4. No secrets in frontend runtime config.
5. UI maps `field_errors` onto form fields, shows an error summary, and moves focus on failed submit; entered values preserved.
6. Unsafe-method retries only with `Idempotency-Key` (frontend never auto-retries non-GET).

---

## 14. Security, Privacy, Logging, Error Handling

- **Transport/headers:** HTTPS outside dev; secure headers + restrictive CSP (test-verified); CORS explicit allowlist, non-reflecting; `DEBUG=False` and fail-fast production settings (raises on missing/insecure env, short secrets, or local auth without double opt-in).
- **AuthN/Z:** HttpOnly/Secure/SameSite session cookies, session-key rotation on login, CSRF enforced (reject/accept tested), login rate limiting, generic failure messages, authorization on every endpoint; horizontal/vertical escalation tested; field-level finance gating (`finance.view`) enforced in serializers and exports.
- **Uploads:** type/extension/signature/size validation; randomized storage keys; authorized downloads.
- **Data protection:** no secrets in code/logs/browser storage/exports; CSV formula-injection mitigation; least-privilege DB role; Unicode throughout.
- **Auditability:** hash-chained append-only audit with actor/action/before-after/correlation/outcome; read restricted; correlation IDs across tiers.
- **Error handling:** stable codes; user-safe messages with recovery guidance; correlation ID on unexpected errors; retryable flag; partial bulk failures reported row-by-row.
- **Dependency governance (Rev 1.2):** DEF-104 **resolved by fix** — `happy-dom` bumped to `^20.11.2`, `npm audit fix` executed, re-audit reports 0 vulnerabilities (documented in `frontend/README.md`); QA re-captures the audit output as closure evidence in cycle 3.

---

## 15. Authentication Design

1. **Mechanism:** Django session auth; login sets HttpOnly/Secure/SameSite cookie; CSRF cookie via `GET /auth/csrf/`; Argon2 hashing; seed users via env-provided passwords only.
2. **OIDC seam:** auth isolated behind `accounts` backends and settings (`OIDC_ISSUER_URL`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` optional). No tokens in `localStorage` in either mode.
3. **Session policy:** configurable idle expiry with rotation on login; expired sessions → 401 → client redirect to `/login?next=…&reason=expired`.
4. **Authorization model:** role capabilities + object/organizational scope checks in `core.permissions`; field-level restrictions per serializer; UI hides but API denies.

---

## 16. Local Dev, Build, Deploy, Operations

- **Compose (ADR-006):** canonical `compose.yaml` and `.env.example` live under `backend/`; `scripts/dev-up.sh` auto-copies them to the repo root when absent (non-clobber). Services: `frontend`, `backend`, `postgres` (18-alpine, healthchecked), `redis`, `celery-worker`, `celery-beat`.
- **Scripts:** `dev-up.sh`, `migrate.sh`, `seed-dev.sh`, `check.sh` (ruff/mypy/migration-check/deploy-check/pytest), `export-openapi.sh`, `backup.sh`/`restore.sh` (production-guarded), `dev-down.sh` — idempotent, fail-fast, environment-labelled.
- **Reproducible installs (Rev 1.2):** `backend/uv.lock` committed; Docker build uses `uv sync --frozen`. Frontend uses `package-lock.json`.
- **Quality gates (executed green at adoption; re-execution against the frozen lock set is the cycle-3 gate):** backend 155 pytest + ruff + mypy (django-stubs); frontend 101 Vitest + lint + typecheck + Nuxt build; OpenAPI drift guard.
- **Backup/recovery:** `backend/docs/BACKUP_RESTORE.md` (scope/schedule/encryption/drill checklist/audit-chain verification step/RTO≤8 h–RPO≤24 h mapping) + scripts; the restore drill itself is environment-blocked (I-9) and tracked as MANUAL.

---

## 17. Testing Strategy and Traceability

Levels: backend unit/service/constraint → API integration (permissions, envelope, pagination, concurrency, idempotency replay) → OpenAPI contract → frontend unit/component → Playwright E2E (authored, environment-blocked) → non-functional (perf/a11y/responsive/security). A test is never marked PASSED without executed evidence. QA maintains per-requirement mapping in `testcase/`; blocked items are explicitly BLOCKED with reasons, never silently skipped.

**Evidence state at Rev 1.2:** API/unit-level PASS evidence exists for all 30 FRs, all 10 BRs, and most stack requirements. Cycle-2 closures: DEF-104 (npm audit clean), DEF-103 (uv.lock). Outstanding verification: gates re-execution against the locked dependency set (I-10), activity-feed union and email-path tests, and the environment-blocked set (I-9) to be consolidated in `testcase/verification-register.md`.

---

## 18. Definition of Done

Feature-level and release-level DoD as in `specification.md` §18, plus stack DoD (`front-back-end-stack.md` §19). Release-gating items for cycle 3: (1) all gates re-executed green against the locked dependency set with evidence filed under this run; (2) no unresolved Critical/High defects — DEF-104 fix verified by QA; (3) environment-blocked verification items presented in the register for an explicit product-owner risk decision.

---

## 19. Revision History

| Date | Cycle | Change |
|---|---|---|
| 2025-01-01 (cycle 1) | 1 | Initial design baseline authored from `specification.md`, `layout.md`, `front-back-end-stack.md`. Established: three-cycle delivery plan; session-cookie auth with OIDC seam (I-2); version-fallback policy (I-1); attachment-scanner interface (I-3); offline stocktake excluded with sync-ready schema (I-5); global tag uniqueness + per-category serial uniqueness (I-6); data model, API v1 contract, error/pagination/idempotency/concurrency conventions; dark-theme token adoption; page inventory and component hierarchy; testing and traceability strategy. |
| 2025-01-08 (cycle 1 review) | 1→2 | **Review revision.** This run's cycle-1 agent summaries were absent (I-8); review reconciled against the workspace's existing full implementation and executed QA evidence from run `run-1c738338ee96` (backend 155 pytest, frontend 88 Vitest, all gates green). Design updated to the delivered contract: trailing slashes; create response `{asset, warnings}`; approval-gated `202`; hash-chained audit; deactivate-not-delete reference data; scoped-throttle rate limiting; ADR register added (§20). I-8/I-9 recorded. Open items carried: DEF-104, DEF-103/uv.lock, FR-029/FR-023 evidence gaps, duplicate QA test ID. Cycle 2 re-planned as verification/disposition/hardening. |
| 2025-01-15 (cycle 2 review) | 2→3 | **Review revision.** Cycle-2 summaries again not filed (I-8 persists — made a hard cycle-3 DoD item). Verified by workspace inspection: **DEF-104 closed** (happy-dom `^20.11.2` + `npm audit fix` → 0 vulnerabilities; documented in `frontend/README.md`; frontend suite now 101 tests) and **DEF-103/ADR-003 closed** (`backend/uv.lock` committed; `uv sync --frozen` builds). New risk **I-10**: lockfile resolved Django 6.1/DRF 3.18 while test evidence is on 6.0.7/3.17.1 — cycle 3 must re-verify gates against the frozen set or constrain the lock. Still outstanding: FR-029 activity-union and FR-023 email-path tests, duplicate TC-ID renumber, verification register, this run's own evidence chain. Cycle 3 planned as final verification/evidence-consolidation/release-readiness cycle; no new features. |

---

## 20. Architecture Decision Register (summary)

| ADR | Decision | Rationale / status |
|---|---|---|
| ADR-001 | npm + `package-lock.json` instead of pnpm | Only npm on the environment allowlist; scripts remain pnpm-compatible. Accepted. |
| ADR-002 | Hand-rolled accessible components instead of Nuxt UI library | Permitted by layout.md §31; keeps §5.2 token palette exact. Accepted. |
| ADR-003 | ~~`backend/uv.lock` not committed~~ → **uv.lock committed (cycle 2)** | Resolved (DEF-103). Locked set pending regression verification (I-10). |
| ADR-004 | Idempotency-Key on all create/transition POSTs | Delivered and test-verified. |
| ADR-005 | Resolved versions: Django 6.x, DRF 3.x, psycopg 3.3, Celery 5.6, Python ≥3.12 | Within stack baseline via §4 rule 4; exact locked versions pending cycle-3 verification (I-10). |
| ADR-006 | Canonical `compose.yaml`/`.env.example` under `backend/` with `dev-up.sh` auto-copy to root | Agent write scopes cannot create root files; bootstrap preserved non-clobbering. Accepted. |
| ADR-007 | DEF-104 dispositioned by dependency fix (`happy-dom ^20.11.2`, `npm audit fix` → 0 vulnerabilities) | Fix preferred over risk acceptance; QA captures audit output as closure evidence in cycle 3. |
