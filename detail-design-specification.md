# Detail Design Specification — Asset Inventory Web Application

- **Document:** detail-design-specification.md
- **Version:** 1.4 (Final review — program sign-off)
- **Status:** FINAL — all 3 cycles delivered, reviewed, and signed off; residual items carry recorded risk decisions (§17)
- **Sources:** `requirements/specification.md`, `requirements/layout.md`, `requirements/front-back-end-stack.md`
- **Owner:** Team Lead agent

---

## 1. Goals, Scope, and Non-Goals

### 1.1 Goals
Build a secure, responsive, dark-themed web application that is the single source of truth for company asset inventory across the full lifecycle: registration, assignment, transfer, return, maintenance, stocktake, retirement, and disposal, with complete audit history, role/scope-based authorization, dashboard, reports, CSV import/export, and notifications.

### 1.2 In Scope (first production release)
Everything listed in specification.md §4.1, prioritized per specification.md §22 (Must Have / Should Have). Delivery sequenced across three cycles (§18); all three cycles are now complete.

### 1.3 Non-Goals (initial release)
- Native mobile apps; network-device auto-discovery; remote device control; procurement/PO processing; accounting/depreciation/GL posting; advanced contract management; GPS; RFID hardware; external customer asset management; ML predictive maintenance (specification.md §4.2).
- **Offline stocktake** (decision D-03): not in the initial release. Connectivity-loss UX per layout §15.3 (no false "saved" claims, retry) is still required.
- Live HR/finance/procurement integrations (CSV import/export and documented v1 API are the integration surface for the first release).
- Light/system user-selectable theme (decision D-05): dark theme only for v1; tokens structured so a light theme can be added later.

---

## 2. Assumptions and Unresolved Questions

### 2.1 Assumptions (validated against specification.md §20)
| ID | Assumption |
|----|-----------|
| A-01 | Internal organizational use; English UI only for v1; Unicode storage; locale-aware date/number/currency display hooks in place. |
| A-02 | No production identity provider is available during development; local session-cookie auth is the dev/test mode and OIDC integration is designed but deferred (D-01). |
| A-03 | Planning volumes: 100k assets, 5k users, 250 concurrent users, 1M lifecycle/audit events, 25k-row imports (NFR-006). |
| A-04 | Malware scanning service is not available; attachment validation is type/extension/signature/size only in v1, with a documented integration point (D-04). |
| A-05 | Approval workflows, category-specific fields, and notification rules must be configurable but ship with sensible defaults; they may be disabled for simple organizations. *Cycle 3: realized as `StatusTransitionRule.requires_approval` + `APPROVALS_ENABLED` flag; default seed rules keep approvals off.* |
| A-06 | Versions: use newest stable, mutually compatible releases of Nuxt (4.x if released/stable at implementation time, else newest stable 3.x with an ADR), Django (6.0 if available, else newest stable LTS line with an ADR), PostgreSQL (18 if available, else newest stable), Node active LTS, Python ≥3.12. Deviations recorded in `ASSUMPTIONS.md` + ADR per front-back-end-stack.md §4. |

### 2.2 Decisions Resolved by This Design
| ID | Decision |
|----|----------|
| D-01 | **Auth:** v1 implements Django session authentication (HttpOnly, Secure, SameSite=Lax cookies) + CSRF tokens for the Nuxt SPA. OIDC SSO is the documented production target via a pluggable auth backend; local auth is gated behind `APP_ENV != production` guard plus explicit `LOCAL_AUTH_ENABLED=true`. |
| D-02 | **Public identifiers:** UUIDs exposed in APIs for all primary resources; internal bigint PKs retained. Asset tag is the human-readable unique key. |
| D-03 | **Offline stocktake:** out of scope v1 (layout §32 item 10, spec §21). |
| D-04 | **Attachments:** metadata in PostgreSQL; files on local media volume in dev, S3-compatible storage in production via django-storages; direct-URL access never allowed — all downloads via authorized, time-limited backend endpoint. Malware-scan hook documented, disabled without a provider. |
| D-05 | **Theme:** dark-only v1, token-based (layout §5.2 palette as initial tokens). |
| D-06 | **Money:** `DecimalField`, API representation `{ "amount": "1234.56", "currency": "USD" }`; never binary float. |
| D-07 | **Concurrency:** integer `version` column on Asset and other material records; clients send `If-Match: <version>` (or `version` in body); mismatch → `409 VERSION_CONFLICT`. |
| D-08 | **Idempotency:** `Idempotency-Key` header supported on create/transition endpoints where duplicates are harmful (asset create, assignment, transfer, return, reservation, checkout, maintenance create, stocktake observation, import commit, retire/dispose/reopen). Stored keys scoped per user+endpoint with 24h TTL. **Status: fully implemented and verified** — replay returns the byte-identical first response (DRF `JSONEncoder` snapshot); key reuse → `409 IDEMPOTENCY_KEY_REUSED`; exactly-once proven on asset create, assign, transfer, return, reserve, maintenance create, stocktake observations, dispose. |
| D-09 | **Pagination:** cursor-style page-number pagination: `?page=&page_size=` (default 25, max 100) with envelope `{count, next, previous, results}`. |
| D-10 | **Async:** Celery + Redis included in compose; used for import/export/notifications. In test/local mode, `CELERY_TASK_ALWAYS_EAGER` fallback permitted. *Verified eager-mode for import/export; notification due-reminder task tested directly (beat schedule is ops config, see §18 handoff).* |
| D-11 | **Rendering:** Nuxt SSR for shell/sign-in/public pages; authenticated inventory pages render client-side after auth bootstrap (`ssr: true` globally with client-only data fetching for private data; no private data in payloads/static cache). |
| D-12 | **Hosting:** Docker Compose is the supported local/CI environment; production target is generic OCI containers behind a reverse proxy (platform intentionally not fixed per stack §15). |
| D-13 | **Settings:** `config.settings.production` fails fast if required env (secret key, DB, allowed hosts, CORS/CSRF origins) is missing or insecure; `DEBUG=false` enforced. |
| D-14 | **Barcode/QR:** QR code (Model 2) encoding the asset tag plus app deep-link URL (`/scan?tag=...`); generated server-side as SVG/PNG; print label 50×25mm initial spec. Browser camera scanning via a JS QR library; manual entry always available. *API + scan page delivered; browser E2E execution environment-blocked (post-release backlog).* |
| D-15 | **Charts:** accessible chart library optional; every chart ships with a summary + table fallback. **Final:** accessible ranked bar lists + table fallbacks satisfy this decision for v1; no chart library added. |

### 2.3 Implementation Decisions Register (ADRs recorded by implementing agents)
| ADR | Decision | Rationale / status |
|-----|----------|--------------------|
| ADR-001 | **npm + package-lock.json** used for frontend instead of pnpm. | Only npm commands are allowlisted in the build environment; package.json scripts remain package-manager agnostic so pnpm works for developers. Accepted (stack §4 item 4). |
| ADR-002 | **Hand-rolled accessible components + Tailwind CSS v4** instead of the Nuxt UI library. | Permitted by layout.md §31 ("accessible project-specific components"); keeps the §5.2 token palette exact; matches Nuxt 4 toolchain. Accepted. |
| ADR-003 | **backend/uv.lock not committed.** | No `uv` in any program environment; Dockerfile installs from pyproject ranges. **Risk-accepted for release** (documented in backend README); generate + commit at the first uv-capable environment and switch Dockerfile to `--frozen`. |
| ADR-004 | **Idempotency-Key (D-08) deferral.** | **Closed** (Cycle 2 implementation; Cycle 3 replay coverage completed). |
| ADR-005 | **Django 6.0.7 on Python 3.14 sandbox** (project floor ≥3.12). | Suite verified on 3.12–3.14 per backend README. Accepted. |
| ADR-006 | **Root bootstrap files resolved procedurally.** | Agent write scopes cannot create repo-root files. `scripts/dev-up.sh` auto-copies canonical `backend/compose.yaml` + `backend/.env.example` to the repo root when absent (non-clobber, env-banner notice). **Verified by QA inspection in Cycle 3; DEF-101/DEF-102 closed.** Full boot evidence remains Docker-blocked (post-release backlog). |
| ADR-007 | **Cross-scope resource access returns 404, not 403** (incl. export downloads, notifications, approvals). | Consistent scope-hidden convention (§11.2); avoids existence leaks. Accepted; normative. |
| ADR-008 | **Approval-held actions return `202 {"approval": {...}}`.** (Rev 1.3) | When the matched `StatusTransitionRule` has `requires_approval=true`, transfer/dispose hold the action and return 202 with the created ApprovalRequest; nothing mutates until approval executes it atomically (disposal blockers re-checked at execution). Default seed rules keep `requires_approval=false`, so immediate-execution behavior is unchanged unless an admin opts in (A-05). Accepted; normative clarification 12 (§11.1). |
| ADR-009 | **Report export is synchronous CSV.** (Rev 1.3) | `POST /reports/:type/export` returns the CSV directly (rows capped at 500 + `truncated` flag), formula-sanitized and audited. Asset-list exports (FR-019) remain async ExportJobs. Rationale: report result sets are already bounded by the 500-row execution cap. Accepted; normative clarification 13. |
| ADR-010 | **Data-quality v1 queue is computed on read.** (Rev 1.3) | `GET /data-quality/issues` computes current flags on read; there is no persistent issue identity, so the Rev-1.2-planned per-issue resolve endpoint was intentionally not built. Resolution happens through the normal edit/workflow endpoints, preserving audit history per FR-028. Accepted; §11.3 row updated. |

### 2.4 Open Questions for Product Owner (tracked, non-blocking for dev)
Final org/site structure; production IdP details; exact permission matrix; approval thresholds; asset-tag format/label spec; category-specific field catalog; supported currencies; notification channels/timing; retention periods and legal hold; final RTO/RPO (interim: RTO ≤8h, RPO ≤24h); performance SLAs; whether logical assets (licenses) are included; first-release integrations. (specification.md §21)

### 2.5 Defect Register — Final Disposition (confirmed at Rev 1.4)
| Defect | Severity | Final disposition |
|---|---|---|
| DEF-001/DEF-101 — root `compose.yaml` | High | **Closed (Cycle 3, ADR-006):** dev-up.sh auto-copy verified by QA inspection; boot verification carried to post-release backlog. |
| DEF-002/DEF-102 — root `.env.example` | Medium | **Closed (Cycle 3, ADR-006)** with DEF-101. |
| DEF-003 — idempotency deferral (D-08) | High | **Closed (Cycle 2)**; replay coverage completed Cycle 3. |
| DEF-004/DEF-103 — `uv.lock` | Medium | **Accepted risk for release (ADR-003);** generate in first uv-capable environment. |
| DEF-005 → DEF-104 — npm-audit critical transitive dev dependency, undispositioned | High | **Open with recorded Team Lead conditional risk acceptance (§17, Rev 1.3; confirmed Rev 1.4).** Mandatory follow-ups: README disposition entry + `npm audit` verification/patch at first capable environment. |
| DEF-006 — reference-data DELETE semantics | Medium | **Closed (Cycle 2).** |
| QA housekeeping — duplicate `TC-FR-020-01` | Low | **Closed (Cycle 3):** renumbered to `TC-FR-020-07`. |
| Environment-blocked verification (browser/Docker) | — | Not defects; documented residual verification backlog (§17). |

---

## 3. Personas and User Journeys

### 3.1 Personas (from specification.md §5)
1. **System Administrator** — users/roles/config/reference data; full visibility.
2. **Asset Manager** — full asset lifecycle operations, stocktakes, approvals, org-wide reports.
3. **Department Manager** — department-scoped visibility, approvals, stocktake confirmation.
4. **Inventory Operator/Technician** — registration, scanning, assignments, maintenance updates within scope.
5. **Employee/Custodian** — own assigned assets, acknowledge, report damaged/missing/lost/stolen, request actions.
6. **Auditor/Read-Only** — permitted read + report export; no mutations.

### 3.2 Key Journeys (canonical; E2E tests derive from these)
- **J-1 Register and assign a new laptop** (spec §11.1) — delivered C1 (registration) + C2 (assignment); API verified; E2E spec authored.
- **J-2 Transfer an asset to another office** (spec §11.2) — delivered C2; approval-gated variant added C3; API verified.
- **J-3 Perform a stocktake** (spec §11.3) — delivered C2 (execution/reconciliation/variance); API verified.
- **J-4 Record repair and return to service** (spec §11.4) — delivered C2; API verified.
- **J-5 Retire and dispose of an asset** (spec §11.5) — delivered C3 (blockers, terminal state, reopen, approval-gated disposal); API verified.
- **J-6 Sign in, search, and open an asset** — delivered C1; API verified.
- **J-7 Bulk import assets from CSV** — delivered C2; API verified.
*All seven journeys have executed API-level evidence; browser-level E2E execution is environment-blocked and carried as the top item of the post-release verification backlog.*

---

## 4. Functional Requirements (with Acceptance Criteria)

Requirement IDs reuse specification.md identifiers for stable traceability. Full acceptance criteria are normative in specification.md §9; deltas/design notes below. **All 30 functional requirements are delivered; statuses reflect QA-executed evidence.**

- **FR-001 Authentication** — Session-cookie login (v1), OIDC-pluggable. Generic failure messages; expired sessions redirect to sign-in with return URL; login/logout/failed-login audit events. **Verified** (CSRF reject/accept, rotation, 429 throttling).
- **FR-002 Authorization** — Role + organizational scope enforced in DRF permission classes on every endpoint; UI hides but never enforces. **Verified** (cross-scope 404s per ADR-007, 403s, finance gating, role gates across all endpoints).
- **FR-003 Asset Creation** — Category-driven required fields; server-generated/validated-unique tag; non-blocking duplicate warnings; atomic create + lifecycle + audit; Draft save; idempotent. **Verified.**
- **FR-004 Asset Viewing/Editing** — Detail tabs; field-level finance permissions; 409 stale version (BR-009); audited before/after updates. **Verified.**
- **FR-005 Search/Filter/Sort/Pagination** — Global search exact-tag-first; server-side scoped filters; URL query state. **Verified** (combined filters/ordering, `assigned` boolean).
- **FR-006 Saved Views** — CRUD own; publish shared; default selection. **Verified.**
- **FR-007 Assignment** — Assignability validation; atomic close-prior (BR-002); acknowledgement; lifecycle + audit. **Verified.**
- **FR-008 Transfer** — Origin/destination/reason/evidence; In Transit; recipient confirmation; optional approval (ADR-008 202-held pattern). **Verified** (incl. approval-gated variant, Cycle 3).
- **FR-009 Return/Check-In** — Condition, damage, destination, resulting status; closes assignment. **Verified** (incl. idempotency replay, Cycle 3).
- **FR-010 Reservation/Checkout** — Overlap conflict prevention (409 `RESERVATION_CONFLICT`); overdue identification; full lifecycle. **Verified (complete, Cycle 3):** `GET /reservations` scoped list (visible assets ∪ own requests) with `status`/`asset`/`requester`/`overdue=true` filters + `/reservations` page with overdue badges.
- **FR-011 Maintenance/Repair** — Typed records; restricted cost; Under Maintenance handling; next-due; history. **Verified.**
- **FR-012 Warranty/Expiry Tracking** — Configurable windows; icon+text identification; notification hooks (warranty-30d due reminders, deduped per asset-day); exportable warranty report (90-day default window, in the FR-021 catalog). **Verified (Cycle 3).**
- **FR-013 Lost/Stolen/Missing/Damaged** — Exception reports with evidence; resolution preserves original event (BR-003); manager notifications on report. **Verified.**
- **FR-014 Retirement/Disposal** — Approval-capable; BR-006 blockers → `409 DISPOSAL_BLOCKED` with blocker list (manager/admin `force` override, operator denied); disposed terminal (further transitions 409); admin-only reopen with mandatory justification returning to `retired`, disposal data preserved (BR-003); disposed searchable to authorized users; Idempotency-Key on all three transitions. **Verified (Cycle 3, 8 tests).**
- **FR-015 Attachments/Images** — Type/signature/size validation; authorized downloads only; audited operations. **Verified.**
- **FR-016 Notes/Comments** — Author+timestamp; append-only corrections; visibility permissions. **Verified.**
- **FR-017 Barcode/QR** — Server-generated QR labels; print; browser scanning + manual fallback; non-destructive unknown code. **Implemented/verified at API + unit level**; camera-scanning browser E2E environment-blocked (post-release backlog).
- **FR-018 Bulk Import (CSV)** — Template → mapping → validate/preview → policy → idempotent async commit → row-level result report; formula sanitization. **Verified.**
- **FR-019 Export** — Filter + permission-respecting UTF-8 CSV; formula-injection mitigation; async large exports; audited. **Verified** (asset-list exports async; report exports synchronous per ADR-009).
- **FR-020 Dashboard** — Scoped KPIs incl. overdue returns, maintenance due, warranty expiring, missing, open exceptions, recent activity; links to filtered lists; no cross-scope totals. **Verified (Cycle 3):** full KPI set covered by executed backend tests (TC-FR-020-04).
- **FR-021 Reports** — Exactly the 14 default reports; date ranges/filters (400 on bad format, 404 unknown type); totals reconcile with permitted scope (dept-manager evidence); finance columns gated; sanitized audited CSV export (ADR-009); rows capped 500 + `truncated`. **Verified (Cycle 3).**
- **FR-022 Stocktake** — Sessions, observations, outcome classification, reconciliation before master-data updates, variance on close, role gates, idempotent scan. **Verified.**
- **FR-023 Notifications** — In-app center (own-only, unread filter, idempotent mark-read, cross-user 404); preferences (mandatory `approval.decided`/`compliance.notice` non-mutable → 400); dedupe (partial unique constraint); email only when SMTP configured with safe failure logging; event fan-out wired (assignment→custodian, exception→managers, approval requested/decided); daily due-reminder generator. **Verified (Cycle 3)** — residual: live SMTP dispatch path environment-blocked (post-release backlog).
- **FR-024 Approvals** — Configurable via `StatusTransitionRule.requires_approval` + `APPROVALS_ENABLED`; held actions return 202 (ADR-008); approve executes atomically; reject/return with comments; separation-of-duties (`409 SEPARATION_OF_DUTIES`); immutable decisions (`409 APPROVAL_ALREADY_DECIDED`); scoped inbox + own requests. **Verified (Cycle 3, 7 tests).**
- **FR-025 Audit History** — Tamper-evident hash chain; actor/action/target/before-after/correlation; restricted read; no application edit/delete. **Verified**, incl. Cycle-3 read API `GET /admin/audit-events` (admin/auditor; filters action/target/correlation/actor/outcome).
- **FR-026 Reference Data Admin** — Full catalog; deactivate-not-delete (BR-004); audited. **Verified** (API Cycle 2; admin UI Cycle 3 with two-step deactivate + reactivate).
- **FR-027 User Admin** — List/search users; role/scope/department/activation management; `409 LAST_ADMIN` guard (demote + deactivate, second-admin escape); non-editable `password`/`username` (400; secrets never displayed); audited before/after. **Verified (Cycle 3, 5 tests).**
- **FR-028 Data Quality** — Rule engine flags (missing/duplicate/mismatch/expired/warranty); errors-before-warnings severity; scoping; computed-on-read queue (ADR-010) with resolution via normal edit/workflow endpoints preserving audit. **Verified (Cycle 3).**
- **FR-029 Activity Feed** — Combined chronological permitted events; permission-aware sensitivity. **Verified.**
- **FR-030 Archiving/Retention** — No physical delete anywhere; `legal_hold` on Asset (admin-only mutation, 403 otherwise); `ARCHIVE_RETENTION_DAYS` server config; archive preserves references/history. **Verified (Cycle 3)** — retention rules are server-configured; the admin settings page documents the policy (no retention endpoint by design).

## 5. Non-Functional Requirements

Normative text in specification.md §14; design resolutions below.

- **NFR-001 Usability / NFR-002 Responsive / NFR-003 Accessibility** — Implemented through §7/§8 and layout.md; WCAG 2.2 AA target. **Implemented in code across all pages** (dialog semantics, focus management, live regions, icon+text status treatments); axe + responsive-matrix browser verification environment-blocked all three cycles — documented manual procedures + authored Playwright/axe specs carried to post-release backlog (§17 risk record).
- **NFR-004 Performance** — Targets: dashboard p95 ≤3s; search/detail p95 ≤2s; long operations async. **Implemented:** async import/export/notifications; N+1 guard verified at volume (list endpoint ≤5 queries, actual 2, Cycle-3 `assertNumQueries` bound); full latency-at-volume run environment-blocked (post-release backlog).
- **NFR-005 Availability** — Atomic transactions; idempotent retryable jobs; unauthenticated health endpoints. **Verified.**
- **NFR-006 Scalability** — Planning baseline A-03. **Partially verified:** `generate_volume` command (repeatable, unique tags) + query-count discipline at generated volume; full ~100k p95 run environment-blocked (post-release backlog).
- **NFR-007 Security** — TLS outside local; Argon2id; session protections; CSRF; headers; CORS allowlist; rate limiting; upload validation; secret hygiene; no stack traces to clients. **Verified at API level** for all executable items (throttling, CSRF, rotation, headers, CORS, scope-hiding, Cycle-3 endpoint security sweep). **Open High:** DEF-104 (npm-audit dev dependency) — recorded conditional risk acceptance, §17.
- **NFR-008 Privacy** — Data minimization; field-level finance/personal restrictions; no unmasked production data in non-prod. **Verified** for implemented surfaces.
- **NFR-009 Auditability** — Correlation IDs propagated Nuxt → Django → Celery; echoed in responses/errors. **Verified.**
- **NFR-010 Maintainability** — Configurable transitions/attributes/notifications; authoritative migrations; externalized config; typed code; all gates green at Cycle-3 close (ruff 147 files, mypy 145 files, nuxi typecheck, lints). **Verified.**
- **NFR-011 Observability** — Structured JSON logs with correlation_id; PII masking; audit separate from diagnostics. **Implemented.**
- **NFR-012 Backup/Recovery** — `scripts/backup.sh` (gzipped pg_dump), `scripts/restore.sh` (production guard, ON_ERROR_STOP), `backend/docs/BACKUP_RESTORE.md` (procedure + drill checklist incl. audit-chain `verify_chain()` step; interim RTO ≤8h / RPO ≤24h). **Implemented/inspection-verified (Cycle 3);** physical drill is MANUAL (Docker-blocked, post-release backlog).
- **NFR-013 Browser Support** — Latest two stable majors of Edge/Chrome/Firefox/Safari. **In progress:** matrix verification environment-blocked; documented as residual with manual-procedure fallback.
- **NFR-014 Localization** — English v1; i18n catalog; Unicode storage; locale-aware formatting. **Implemented** (Unicode import/export verified).

---

## 6. Page Inventory and Navigation

Role-aware; inaccessible modules hidden (and denied server-side). Routes use Nuxt file-based routing under `/`. **All pages delivered as of Cycle 3; every "Soon" badge cleared.**

| Route | Page | Roles (min) | Status |
|---|---|---|---|
| `/login` | Sign in | public | ✅ C1 |
| `/` | Dashboard (KPIs, alerts, data-quality link) | all authenticated | ✅ C2 |
| `/assets` | Asset register (table/cards, filters, saved views) | all (scoped) | ✅ C1 |
| `/assets/new` | Create asset | Operator+ | ✅ C1 |
| `/assets/[id]` | Asset detail (Overview; Retire/Dispose/Reopen actions by role) | all (scoped) | ✅ C1/C3 |
| `/assets/[id]/edit` | Edit asset | Operator+ | ✅ C1 |
| `/assets/[id]/history` | Activity feed / history | all (scoped) | ✅ C2 |
| `/assets/[id]/assign`, `/transfer`, `/return` | Workflow dialogs/pages | Operator+ | ✅ C2 |
| `/assets/[id]/maintenance` | Maintenance tab/records | Operator+ | ✅ C2 |
| `/assets/[id]/documents` | Attachments + notes | all (scoped) | ✅ C2 |
| `/assets/[id]/label` | QR label print | Operator+ | ✅ C2 |
| `/scan` | Scanner + manual tag entry | Operator+ (Employee lookup) | ✅ C2 |
| `/assignments` | Assignment/transfer work queue | Operator+ | ✅ C2 |
| `/reservations` | Reservations list incl. overdue filter/badges | Operator+ | ✅ C3 |
| `/stocktakes`, `/stocktakes/[id]`, `/stocktakes/[id]/count` | Stocktake sessions + mobile count | Manager (create), Operator (count) | ✅ C2 |
| `/maintenance` | Maintenance work list | Operator+ | ✅ C2 |
| `/imports`, `/imports/[id]` | Import wizard + results | Operator+ | ✅ C2 |
| `/exports` | Export center | all (scoped) | ✅ C2 |
| `/data-quality` | Data-quality work queue (severity filters, resolve via edit/workflows) | Operator+ | ✅ C3 |
| `/approvals` | Approval inbox (pending default, SoD hints, decision dialog) | DeptManager+ | ✅ C3 |
| `/reports`, `/reports/[type]` | Reports catalog + viewer (filters, totals, drill-through, export) | DeptManager+/auditor (scoped) | ✅ C3 |
| `/notifications` | Notification center + preferences | all | ✅ C3 |
| `/admin`, `/admin/users`, `/admin/reference-data`, `/admin/workflows`, `/admin/audit`, `/admin/settings` | Administration (users, reference data, read-only transition rules, audit events, retention documentation) | Admin (audit: admin/auditor) | ✅ C3 |
| `/help` | Help | all | ✅ C1 |
| `/403`, `/404`, `/error` | Error pages | all | ✅ C1 |

**Navigation:** Desktop/laptop (≥1024px): persistent collapsible left sidebar (Dashboard, Assets, Assignments, Reservations, Stocktakes, Maintenance, Reports, Imports/Exports, Approvals, Notifications, Administration, Help) + top bar (page context, global search, quick-create, notifications with unread count, help, profile). Tablet: collapsed icon rail or drawer. Mobile: top app bar + bottom nav (Home, Assets, Scan, Tasks, More) + drawer. Breadcrumbs on desktop nested pages; mobile back action + parent context. Active section programmatically identifiable (`aria-current`). Deep links re-auth then land correctly (incl. notification deep links).

---

## 7. Responsive, Theme, and Accessibility Design

- **Breakpoints (guidance):** 320–479 / 480–767 / 768–1023 / 1024–1439 / ≥1440. Content-driven; no page-level horizontal scroll at 320px; 200% zoom safe; ≥44×44px touch targets; safe-area insets respected; mobile keyboards must not hide active field/actions.
- **Theme tokens:** CSS custom properties + Tailwind v4 `@theme` generated from layout §5.2 palette (canvas `#090D14`, sidebar `#0D131D`, surface `#121A26`, raised `#182231`, input `#0E1622`, hover `#1D2A3A`, borders `#263445`/`#3A4A5E`, text `#F3F6FA`/`#B8C4D1`/`#8795A6`/`#667384`, accent `#5EA2FF`/hover `#83B7FF`/on-primary `#061221`, focus ring `#8CC8FF`, success `#4FD1A1`, warning `#F4C95D`, danger `#FF6B78`, info `#63B3ED`). AA contrast for every pairing; semantic token references only. No flash of unstyled theme; `<html class="dark">` default. *(Implemented, ADR-002.)*
- **Status presentation:** every status/condition/severity has label + icon + semantic color + high-contrast badge + screen-reader text; never color alone (incl. Cycle-3 overdue badges, data-quality severities, disposal states).
- **Typography/elevation:** system sans stack; 16px body desktop (14px minimum metadata); monospace for tags/serials; 8–12px radii; restrained elevation.
- **Responsive patterns:** register table ↔ cards; dialogs → full-screen sheets on compact; filters → bottom sheet with Apply/Clear; numbered pagination desktop / prev-next mobile; dashboard grid collapse.
- **Accessibility (WCAG 2.2 AA):** semantic landmarks/headings; skip link; logical tab order; visible focus; no traps; Escape closes overlays with focus restore; labeled controls; error association + summary with focus move; live regions; chart summaries + table alternatives; `prefers-reduced-motion`. **Verification status:** patterns implemented and unit-reviewed across all pages incl. Cycle-3 dialogs (reservation, approval decision, lifecycle-end); automated axe + manual keyboard/SR passes remain environment-blocked — authored specs + documented manual procedures carried to the post-release backlog (§17).

---

## 8. Frontend Architecture

### 8.1 Stack
Nuxt 4, Vue 3 Composition API, `<script setup lang="ts">`, TypeScript strict, Tailwind CSS v4 (ADR-002), npm + package-lock.json (ADR-001). Rendering per D-11. Vitest + Vue Test Utils unit tests (**88 passing at program close**, 13 files); Playwright + axe-core E2E authored for all three cycles (execution environment-blocked). Production build **3.07 MB / 786 kB gzip**.

### 8.2 Directory / Component Hierarchy
```
frontend/
├── app.vue / app.config.ts
├── assets/css/ (tokens, base)
├── components/
│   ├── shell/      AppShell, AppSidebar, AppTopBar, MobileBottomNavigation, AppDrawer
│   ├── layout/     PageHeader, EmptyState, InlineAlert, ConfirmActionDialog, FullScreenMobileSheet, StickyActionBar, LoadingSkeleton
│   ├── asset/      AssetTable, AssetCardList, AssetStatusBadge, AssetConditionBadge, AssetIdentityHeader,
│   │               AssetActivityTimeline, AssetForm, DuplicateWarningPanel, AssetActionBar,
│   │               AssetReservationDialog (C2), AssetLifecycleEndDialog (C3: retire/dispose/reopen)
│   ├── search/     GlobalAssetSearch, SearchSuggestions
│   ├── filters/    FilterBar, FilterDrawer, ActiveFilterChips
│   ├── dashboard/  KpiCard, AccessibleChartPanel, TasksPanel, ActivityPanel
│   ├── scan/       ScannerPanel, ManualTagEntry
│   ├── approval/   ApprovalDecisionDialog (C3)
│   ├── notification/ (center + preferences UI, C3)
│   └── admin/      (users table/edit dialog, reference-data manager, C3)
├── composables/    useApi, useAuth, useAssets, useAssetFilters (URL-synced), useSavedViews, usePermissions, useToast, useCorrelationId
├── middleware/     auth.global.ts (UX redirect only)
├── pages/          per §6 route table
├── services/api/   auth, assets, referenceData, search, dashboard, savedViews, lifecycle, imports,
│                   stocktakes, reservations, approvals, notifications, reports, admin, dataQuality
├── types/          generated from OpenAPI + hand-written view models (app/types/control.ts C3)
├── utils/          reservation.ts (C2), report.ts (C3: column normalization, money D-06 formatting, record links)
└── tests/          unit (Vitest), e2e (Playwright; render-level smoke incl. dialogs, skip without stack)
```

### 8.3 State Management
- Server data via typed services + composables; backend is source of truth; no duplicated server caches.
- Filters/pagination/sort in URL query params. Session/current user via `useAuth` (`/auth/me`). No Pinia (never needed). Toasts via composable; errors via centralized envelope mapping. Cycle-3 note: notification-preferences and report responses are normalized client-side against array/envelope/container shapes (defensive tolerance documented as contract clarifications 14–15).

### 8.4 API Client Rules
Single `useApi` wrapper over `$fetch`: `API_BASE_URL` runtime config; `X-Correlation-ID` (UUIDv4) + CSRF on unsafe methods; credentials `include`; typed `ApiError` mapping; timeouts (15s default, 60s uploads); retries only idempotent GET/HEAD; **never retries unsafe methods** (verified); `Idempotency-Key` attached by lifecycle/import services; never displays raw exceptions. **Verified.**

### 8.5 Form & UX Standards
Required markers; validate on blur/submit; error summary + per-field errors; focus to summary; preserve values; unsaved-changes guard; duplicate-submit prevention; specific button labels; destructive confirmations naming asset + consequence; wizards per layout §13.3. Cycle-3 additions: BR-006 `409 DISPOSAL_BLOCKED` blockers listed verbatim as non-destructive warning tone; comments mandatory on approval reject/return; backend SoD errors surfaced inline; all lifecycle-end actions await confirmed responses (integration rule 6).

---

## 9. Backend Architecture

### 9.1 Stack
Django 6.0.7 (ADR-005), DRF 3.17.1, Python ≥3.12, psycopg 3.3.4, django-filter 25.2, drf-spectacular 0.30.0, Celery 5.6.3 + Redis, qrcode 8.2, argon2-cffi, django-storages (prod), uv + lockfile (pending, ADR-003). PostgreSQL only. **155 pytest passing at program close** (26 test files).

### 9.2 Project Layout & Service Boundaries
```
backend/
├── manage.py, pyproject.toml
├── config/settings/{base,local,test,production}.py, urls.py, asgi.py, wsgi.py, celery.py
├── apps/
│   ├── accounts/        users, roles, scopes, auth endpoints, admin user endpoints (C3)
│   ├── reference_data/  categories, statuses, conditions, locations, departments, cost centers, suppliers, attribute definitions, transition rules
│   ├── assets/          asset CRUD, tags, search, attachments metadata, notes, retire/dispose/reopen (C3)
│   ├── assignments/     assignment, transfer, return, reservation services (+ GET /reservations C3)
│   ├── maintenance/     maintenance records, warranty/expiry queries
│   ├── stocktakes/      sessions, observations, reconciliation
│   ├── reporting/       dashboard aggregations, 14-report catalog + export (C3), saved views, data-quality queue
│   ├── approvals/       approval requests, decisions, SoD (C3)
│   ├── notifications/   in-app notifications, preferences, due-reminder generator + Celery task (C3)
│   ├── audit/           audit events, hash chain, admin read API (C3)
│   └── core/            error envelope, pagination, permissions base, idempotency, throttling, correlation middleware, health
├── docs/                BACKUP_RESTORE.md (C3)
└── tests/               26 files (155 tests)
```
**Boundaries:** lifecycle mutations live in explicit service functions in `transaction.atomic()` with row locks where invariants require; services emit LifecycleEvent + AuditEvent atomically; approval-held mutations execute only on approval (ADR-008); no business side effects in signals; serializers = representation + boundary validation. Core hardening: `ScopedSimpleRateThrottle` (C2), JSONEncoder idempotency snapshots (C2).

### 9.3 Roles & Scopes Model
Roles: `system_admin`, `asset_manager`, `department_manager`, `operator`, `employee`, `auditor`. Scopes: M2M `UserScope` (user × department/location/business-unit). Permission classes combine role capability map + scope predicate; admins unrestricted; scopeless operators see custody assets only. Field-level finance restrictions via `finance.view`. Cycle-3 additions: approver roles (dept/asset manager, admin) with SoD; `audit.read` capability (admin/auditor); admin user-management guarded by `LAST_ADMIN`.

---

## 10. Data Model

All tables: `id` bigint PK internal, `uuid` public unique, `created_at`/`updated_at` timestamptz UTC, `created_by`/`updated_by` FK where applicable. Money: numeric(14,2)+currency char(3). `record_status` active/archived; no hard delete of business records (verified — no physical delete anywhere).

### 10.1 Core Entities (final v1 schema)
- **User** (+`UserProfile`): display name, department FK, locale, timezone, role, active flag. **UserScope**: user × (department|location|business_unit).
- **Department, Location, CostCenter, Supplier**: name, unique code, active flag, description.
- **Category** (name, code, parent, active); **CategoryAttributeDefinition** (category FK, key, label, type, required, options JSON, unique/restricted flags).
- **AssetStatus** / **AssetCondition** (code, label, icon, semantic_treatment, active, sort_order); **StatusTransitionRule** (from/to status, requires_reason/evidence/**approval**, allowed_roles) — approval gating realized C3 (ADR-008).
- **Asset**: full field set per Rev 1.0/1.1 (tag unique immutable, category/status/condition/department/location/custodian FKs, serial, manufacturer/brand/model, parent_asset, external_ids JSONB, acquisition/finance fields, warranty/contract dates, maintenance dates/interval, technical fields, category_attributes JSONB, lifecycle dates incl. disposal method/reason, data_quality_status, version, record_status) **+ `legal_hold` boolean (C3, admin-only mutation, FR-030).**
- **Assignment**: partial unique index one active primary assignment per asset (BR-002). **Verified.**
- **Reservation**: asset, requester, period, purpose, status; overlap prevention (409). **Verified** incl. overdue identification (end < now ∧ status ∈ requested/confirmed/checked_out).
- **MaintenanceRecord**: typed, provider/technician, dates, restricted cost+currency, result, next_due.
- **TransferRecord**: from/to custodian+location+department, requester, reason, status (pending_approval|in_transit|received|cancelled), approval FK, evidence, confirmed_by/at.
- **ApprovalRequest** (C3): type, requester, asset FK, payload JSONB, reason, status, approver, decided_at, comments; **immutable after decision** (409 on re-decide); SoD enforced (requester ≠ approver, 409).
- **StocktakeSession / StocktakeObservation**: full outcome classification. **Verified.**
- **LifecycleEvent**: append-only; actor (user or service identity), correlation_id.
- **AuditEvent**: append-only SHA-256 hash chain; UPDATE/DELETE revoked for app role. **Verified.**
- **Attachment / Note**: per Rev 1.0/1.1. **Verified.**
- **SavedView**: owner, name, config JSONB, shared, is_default.
- **Notification** (C3): recipient, type, title, body, link, read_at, dedupe_key with **partial unique constraint** (unread dedupe); preferences per user/type with mandatory-type protection.
- **ImportJob / ExportJob**: status machine, counts, result_file, correlation_id.
- **IdempotencyRecord**: key, user, endpoint, request_hash, JSON-encoded response snapshot, 24h TTL.
- **AssetTagSequence**: locked counter for server-side tag generation.

*Migration note (C3, awareness): `assets/0002_asset_legal_hold` is an empty bridge migration resolving a leaf conflict with the pre-existing `0002_attachments_notes`; `0003_asset_legal_hold` carries the field. Harmless; optional cleanup in maintenance window.*

### 10.2 Integrity Rules
Unique asset tag all-time (BR-001); partial unique active assignment (BR-002); row-local date checks (BR-005); BR-004 deactivate-not-delete on referenced reference data (verified); disposal blockers BR-006 (open assignment, open maintenance, active reservation, non-terminal status — enumerated in 409 response); conditional serial uniqueness per category; partial unique notification dedupe.

### 10.3 Indexing
Per Rev 1.0/1.1 set (tag, serial, FK fields, warranty_end, next_maintenance_due, timestamps, assignment(asset, returned_at), lifecycle(asset, occurred_at), audit(target, correlation)). N+1 discipline verified at generated volume (list ≤5 queries, actual 2). pg_trgm evaluation deferred to the post-release 100k latency run.

### 10.4 Seed Data (dev, non-sensitive)
Roles + demo users per role; ~8 departments, ~12 locations, 6 cost centers, 8 suppliers; 13 statuses + 6 conditions + default transition rules (approval flags off by default, A-05); 5 categories with attribute definitions; ~200 assets with assignments/lifecycle; 1 open stocktake; saved views. **Verified.** `generate_volume` management command (repeatable, unique `VOL-` tags) provides the NFR-006 dataset.

---

## 11. API Contracts (v1, base `/api/v1/`)

### 11.1 Conventions
JSON; ISO 8601 TZ datetimes; money object (D-06); UUIDs in URLs; server-side filter/sort/pagination (D-09); `Idempotency-Key` on unsafe retry-sensitive POSTs (D-08); `If-Match`/version on updates (D-07); `X-Correlation-ID` echoed; OpenAPI at `/api/v1/schema/`, exported `backend/openapi.json` with drift-guard (green with all Cycle-3 endpoints).

**Contract clarifications (normative):**
1. DRF trailing slashes on all endpoints.
2. `POST /assets/` → `201 { "asset": {...}, "warnings": [...] }`; `tag` optional on write (server generates `AST-*`).
3. Duplicate pre-check: `POST /assets/check-duplicates`, `POST /assets/:uuid/check-duplicates` → non-blocking `warnings`.
4. `PATCH /assets/:uuid/` accepts `If-Match: <version>` **or** body `version`; stale → `409 VERSION_CONFLICT`; missing → `400 VALIDATION_FAILED`.
5. Related fields write as UUID strings, read as compact objects; filters accept UUIDs (category/department/location) or UUID-or-code (status/condition); dashboard links use status codes.
6. `GET /auth/me` → `{ uuid, username, display_name, email, role, scopes[], capabilities[] }`; finance fields gated by `finance.view`.
7. Reference-data/saved-views lists may return arrays or paginated envelopes; clients handle both.
8. Money is always `{ "amount": "1234.56", "currency": "USD" }`.
9. Cross-scope access → **404** (existence not leaked), incl. export downloads, notifications, approvals (ADR-007).
10. Reference-data DELETE deactivates in-use rows: `200 { "active": false }`, idempotent, audited (`reference.<type>.deactivate`); rows never destroyed (BR-004).
11. Overlapping active reservation → `409 RESERVATION_CONFLICT` (non-destructive; UI warning tone).
12. **(ADR-008)** When the matched transition rule has `requires_approval=true`, `POST /assets/:uuid/{transfer|dispose}` → `202 { "approval": {...} }` and mutate nothing; the held action executes atomically on approval (blockers re-checked). With approval rules off (default), behavior is immediate 200/201.
13. **(ADR-009)** `POST /reports/:type/export` returns the CSV **synchronously** (≤500 rows, `truncated` flag, formula-sanitized, audited `report.export`). Asset-list exports (FR-019) remain async ExportJobs.
14. `GET /reports/:type` → `{ columns?, rows, totals?, generated_at? }`; when `columns` is undeclared, clients infer from the first row (frontend normalizes).
15. **(ADR-010)** `GET /data-quality/issues` is a computed-on-read queue; there is **no** per-issue resolve endpoint — resolution happens through normal edit/workflow endpoints (audit-preserving per FR-028).

### 11.2 Error Envelope (all non-2xx)
```json
{ "error": { "code": "ASSET_STATUS_TRANSITION_INVALID", "message": "user-safe text", "field_errors": {"field": ["msg"]}, "correlation_id": "uuid", "retryable": false } }
```
Stable codes: VALIDATION_FAILED, AUTHENTICATION_REQUIRED, PERMISSION_DENIED, NOT_FOUND, VERSION_CONFLICT, STATUS_TRANSITION_INVALID, ASSIGNMENT_CONFLICT, RESERVATION_CONFLICT, DISPOSAL_BLOCKED, DUPLICATE_TAG, IMPORT_ROW_INVALID, IDEMPOTENCY_KEY_REUSED, SEPARATION_OF_DUTIES, APPROVAL_ALREADY_DECIDED, LAST_ADMIN, RATE_LIMITED, INTERNAL_ERROR. HTTP mapping: 400/401/403/404 (also scope-hiding)/409/413/415/429/500; **202 for approval-held actions** (ADR-008).

### 11.3 Endpoint Summary (v1 — final)
| Group | Endpoints | Status |
|---|---|---|
| Auth | `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `GET /auth/csrf` | ✅ |
| Reference data | `GET/POST/PATCH /reference-data/{type}[/:uuid]`, `GET /reference-data/transition-rules`, DELETE → deactivate (BR-004) | ✅ |
| Assets | `GET/POST /assets`, `GET/PATCH /assets/:uuid`, check-duplicates ×2, `GET /assets/:uuid/{history|activity|label}`, `POST /assets/:uuid/notes`, `GET/POST/DELETE /assets/:uuid/attachments` | ✅ |
| Lifecycle | `POST /assets/:uuid/{assign|transfer|return|reserve|checkout|report-exception}` | ✅ |
| Lifecycle end | `POST /assets/:uuid/{retire|dispose|reopen}` (Idempotency-Key; BR-006; ADR-008 approval option) | ✅ C3 |
| Reservations | `GET /reservations` (scoped; `status`/`asset`/`requester`/`overdue=true`) | ✅ C3 |
| Maintenance | `GET/POST /maintenance`, `GET/PATCH /maintenance/:uuid`, `POST /maintenance/:uuid/complete` | ✅ |
| Stocktakes | sessions CRUD-lite, observations, start/reconcile/close, variance | ✅ |
| Search | `GET /search/assets?q=` | ✅ |
| Dashboard | `GET /dashboard/summary` (full scoped KPI set) | ✅ |
| Data quality | `GET /data-quality/issues` (computed queue, ADR-010) | ✅ C3 |
| Saved views | `GET/POST/PATCH/DELETE /saved-views[/:uuid]` | ✅ |
| Import/Export | template, `POST /imports`, status, commit, result; `POST /exports`, status, download | ✅ |
| Approvals | `GET /approvals`, `POST /approvals/:uuid/{approve|reject|return}` | ✅ C3 |
| Notifications | `GET /notifications` (`unread` filter), `POST /notifications/:uuid/read`, `GET/PATCH /notifications/preferences` | ✅ C3 |
| Reports | `GET /reports` (14-type catalog), `GET /reports/:type`, `POST /reports/:type/export` (sync, ADR-009) | ✅ C3 |
| Admin | `GET/PATCH /admin/users[/:uuid]` (LAST_ADMIN guard), `GET /admin/audit-events` | ✅ C3 |
| Health | `GET /health/live`, `GET /health/ready` | ✅ |

---

## 12. Authentication Design

- **v1:** Django session auth (HttpOnly, Secure non-local, SameSite=Lax, rotated on login, 12h absolute/30min idle configurable). CSRF via CsrfViewMiddleware + `/auth/csrf`. Argon2id (fallback PBKDF2). Login rate-limited (`ScopedSimpleRateThrottle`), generic failures, lockout/backoff documented. **All verified by executed tests.**
- **Production target:** OIDC SSO via pluggable backend; server-side session remains the browser credential; local auth hard-disabled in production unless `LOCAL_AUTH_ENABLED=true` (startup fail per D-13). **Fail-fast verified by inspection.**
- **Session expiry UX:** 401 → `/login?next=…&reason=expired`; deep links honored (incl. notification deep links). **Implemented.**
- **Audit:** login success/failure/logout recorded. **Verified.**

---

## 13. Security, Privacy, Logging, Error Handling

- **Transport/Headers:** TLS outside local; HSTS, X-Content-Type-Options, Referrer-Policy, restrictive CSP, frame-ancestors 'none'; CORS explicit allowlist, no wildcard with credentials. **API-level verification executed;** live compose-level checks environment-blocked (backlog).
- **Rate limiting:** login + import/export throttles via `ScopedSimpleRateThrottle`; 429 `RATE_LIMITED` retryable. **Verified.**
- **Uploads:** allowlist type/extension/signature/size (10MB default); sanitized filenames; random storage keys; authorized download only; scan hook (D-04). **Verified.**
- **Exports:** UTF-8 CSV (BOM documented); formula-injection mitigation on import (sanitize/flag) and export (prefix `'`); verified both directions incl. report exports (`'=dangerous` evidence).
- **Privacy:** field-level finance/personal restrictions; log masking; no unmasked production data in non-prod. **Verified for implemented surfaces.**
- **Dependency security:** frontend lockfile committed; **DEF-104 open** — Cycle-1 critical npm-audit transitive dev dependency under recorded conditional risk acceptance (§17) pending `npm audit` access. Backend: uv.lock pending (ADR-003 accepted risk); pip-freeze inventory verified.
- **Logging:** structured JSON (timestamp, level, service, correlation_id, user, path, status, latency); audit ≠ diagnostics. Notification delivery failures logged without confidential content (verified by design/tests; SMTP path backlog).
- **Error handling:** envelope §11.2; unhandled → 500 `INTERNAL_ERROR` + correlation ID, stack trace server-side only. **Verified;** Cycle-2/3 tests eliminated all discovered stray 500 paths.

---

## 14. Frontend/Backend Integration Rules

1. Django owns business rules/authorization/persistence/canonical validation; Nuxt owns presentation/UX validation/feedback.
2. All traffic via the typed `/api/v1/` client; no arbitrary component fetches. **Verified.**
3. OpenAPI is the contract; drift-guard fails the build on drift; regenerated with all C3 endpoints. Breaking changes require `/api/v2/`.
4. Dates ISO 8601 TZ; money decimal-string + ISO currency; consistent pagination envelope.
5. Correlation IDs both directions; surfaced as support references.
6. Lifecycle/approval/stocktake/disposal actions await confirmed backend responses before success UI (no optimistic completion). **Verified pattern incl. C3 lifecycle-end dialog; approval-held 202 surfaced as "pending approval" state (ADR-008).**
7. Permission-driven UI from `/auth/me` role/scopes/capabilities; backend re-enforces everything. Cycle-3 gating: Retire/Dispose → system_admin/asset_manager; Reopen → admin; approvals inbox → DeptManager+; reports → Manager+/auditor; admin → admin (audit also auditor).

---

## 15. Testing Strategy & Traceability

### 15.1 Levels — final executed evidence base
- **Backend:** pytest + pytest-django. **155 tests passing** (26 files): workflows 15, maintenance 7, attachments/notes 7, bulk 9, csv_utils 4, stocktakes 5, security 10+, reference_data 4, search/dashboard 4+2, assets 16, auth 7, audit 8, openapi 6, health 2, migrations/seed 2, models 3, **+ C3:** admin 5, approvals 7, dataquality_dashboard 5, idempotency_replay 3, notifications 6, reports 8, reservations 2, retention_volume 2, retire_dispose 8. Tests found and fixed 4 real defects in C2.
- **Frontend:** **88 unit tests passing** (13 files) incl. report/reservation/scan logic; Playwright + axe E2E authored for all cycles (execution environment-blocked).
- **QA (testcase/):** ~157 designed cases across 3 cycles (60 + 53 + 44). Executed outcomes — C1: 39 passed; C2: 84 passed; C3: 38 passed (33 new + 5 previously-blocked closures); 2 failed (both DEF-104 governance, dispositioned in §17); 2 manual (backup drill, prod fail-fast); remaining blocked = browser/Docker-dependent + SMTP, all with per-case justification.

### 15.2 Traceability
Requirement IDs: FR-001…FR-030, NFR-001…NFR-014, BR-001…BR-010 (specification.md); LAY-1…LAY-8 (layout.md); STK-1…STK-6 (front-back-end-stack.md). QA IDs `TC-<REQID>-<nn>` (C3 duplicate renumbered to `TC-FR-020-07`). `requirements_json` statuses derive from QA evidence only; `verified` requires executed evidence.

### 15.3 Quality Gates — final status
Backend: ruff format/check (147 files), mypy (145 files), pytest, makemigrations check, drift-guard — **all green**. Frontend: lint (0/0), typecheck (exit 0; cosmetic volar notice), unit tests, production build — **all green**. Repo: lockfiles present (uv.lock exception, ADR-003), no `.env` committed, `.gitignore` verified. Environment-blocked gates: E2E/axe, compose boot, npm audit — dispositioned per §17.

---

## 16. Local Dev, Build, Deploy, Operations

### 16.1 Local
Compose services: `frontend`, `backend` (dev runserver), `postgres`, `redis`, `celery-worker`, `celery-beat`, optional `minio`. Canonical `compose.yaml` + `.env.example` live in `backend/`; **`scripts/dev-up.sh` auto-copies them to the repo root when absent (ADR-006, QA-verified C3)** — clean-checkout bootstrap works without root-write permission. Scripts: `dev-up.sh`, `migrate.sh`, `seed-dev.sh`, `check.sh`, `dev-down.sh`, `backup.sh`, `restore.sh` (all `set -euo pipefail`, env banners). `.gitignore` ignores `.env` with `!.env.example` exception.

### 16.2 Build
Frontend: Nuxt production build (3.07 MB / 786 kB gzip verified). Backend: immutable OCI image, ASGI server in production, non-root containers, health/readiness, graceful shutdown. (`uvicorn_smoke_import` allowlist entry is FastAPI-oriented, N/A to Django; startup covered by pytest + system checks.)

### 16.3 Deploy/Operate (documented target; platform per D-12)
Separate web/worker/scheduler processes; migrations as controlled single-runner release step; private-network PostgreSQL/Redis; attachments on object storage; centralized logs/metrics/alerts; automated encrypted backups per `backend/docs/BACKUP_RESTORE.md` (gzipped pg_dump; restore with production guard + ON_ERROR_STOP; drill checklist incl. audit-chain `verify_chain()`; interim RTO ≤8h / RPO ≤24h); rollback = previous image + backward-compatible migrations. Ops wiring note: `send_due_reminders` beat schedule documented, to be added to `config/celery.py` beat config at deployment (post-release backlog).

### 16.4 Documentation Deliverables — final
Root README; frontend/backend READMEs (current through C3, deviations + ADR-003 risk re-assertion); env reference; OpenAPI docs; `backend/docs/BACKUP_RESTORE.md`; ADR register (§2.3); `ASSUMPTIONS.md`. Outstanding doc task: frontend README DEF-005/DEF-104 disposition entry (post-release plan §1).

---

## 17. Definition of Done — Final Risk & Release Record

Per specification.md §18 plus: authorization enforced UI+backend; all UI states implemented; audit events recorded; automated tests passing with retained evidence; docs updated; **no unresolved critical/high defects without a recorded risk decision**; traceability updated from QA evidence only.

**Recorded Team Lead risk decisions (final, confirmed at Rev 1.4):**
1. **DEF-104 (High, open — conditional risk acceptance, Rev 1.3).** The Cycle-1 npm-audit finding concerns a **transitive dev dependency**. Basis for acceptance: (a) dev dependencies are excluded from the Nuxt production build artifact (verified build output 3.07 MB / 786 kB gzip contains only runtime bundles); (b) no reachable exploit path in the shipped application has been identified by any agent across three cycles; (c) verification tooling (`npm audit`) is unavailable in every program environment — this is an environment limitation, not evidence of absence. **Conditions (mandatory follow-ups, post-release plan §1):** frontend README disposition entry citing the specific package/version; `npm audit` executed at the first capable environment; immediate patch/remove if the package is found in shipped output or has a reachable exploit path; release notes must carry DEF-104 as open-accepted until then. This converts the undispositioned governance gap (TC-DEF-005-02/TC-REL-001 failure) into a recorded decision as required by this DoD, without claiming a fix that has no evidence.
2. **DEF-103/ADR-003 (Medium, accepted):** uv.lock absent (no uv in any environment); generate at first capable environment.
3. **Environment-blocked verification (accepted, documented):** browser-level (E2E J-1…J-7, axe, responsive matrix, XSS probes, live headers) and Docker-level (compose boot, backup drill, ~100k perf run, SMTP) verification could not execute in any program environment. These ship as authored test suites + documented manual procedures + an ordered post-release backlog — not as silent passes. Executed evidence base: 155 backend + 88 frontend automated tests, 161 QA-verified case passes across three cycles.
4. **Closed during the program:** DEF-001/002 (→ DEF-101/102, closed via ADR-006), DEF-003 (idempotency, closed C2), DEF-006 (BR-004, closed C2), all Cycle-2 mandatory coverage gaps (closed C3), TC-FR-020-01 ID collision (renumbered C3).

**Release-readiness statement (confirmed at Rev 1.4 final review):** All executable quality gates green on both sides; all FR-001…FR-030 delivered with executed API-level evidence; OpenAPI drift-guard green; docs current. The release candidate is approved **with** the open-accepted items above stated in the release notes.

---

## 18. Delivery Plan (3 Cycles) — Program Complete

- **Cycle 1 (complete):** Foundation — scaffold, auth, data model, asset CRUD/search, reference data, saved views, dashboard (basic), audit chain, app shell + dark theme. Outcome: backend 55/55, frontend 52/52; DEF-001…006; 36 QA blocked.
- **Cycle 2 (complete):** Workflows — assignment/transfer/return/reservation, maintenance, attachments/notes, QR, CSV import/export, stocktakes, activity feed, dashboard KPIs, data-quality v1, exception reports; idempotency (ADR-004) + BR-004 fixes; security/filter test closures. Outcome: backend 109/109, frontend 77/77; QA 84 passed; 4 real defects found & fixed by new tests; DEF-101/102/103 carried.
- **Cycle 3 (complete — reviewed at Rev 1.3):** Control & polish — `GET /reservations` + page (FR-010 complete), approvals + SoD (FR-024, ADR-008), notifications (FR-023), 14-report catalog (FR-021, ADR-009), admin UIs (FR-026/027/030 + audit read), retire/dispose/reopen (FR-014, J-5), mandatory gap tests (FR-028, TC-FR-020-04, idempotency transfer/return/reserve), ADR-006 bootstrap closure, backup/restore docs+scripts (NFR-012), volume command + N+1 bound (NFR-006 partial). Outcome: backend 155/155 + ruff + mypy; frontend 88/88 + lint + typecheck + build; QA 38 passed / 2 failed (DEF-104 governance → dispositioned §17) / 2 manual / blocked backlog documented.
- **Post-release:** standing handoff plan — DEF-104 follow-ups, ordered environment-dependent verification backlog (compose boot → E2E/axe/responsive → 100k perf → backup drill → SMTP → uv.lock), and small engineering backlog (Celery beat wiring, spectacular/volar cosmetics).

---

## 19. Revision History

| Rev | Date (cycle) | Author | Changes |
|---|---|---|---|
| 1.0 | Cycle 1 (initial_design) | Team Lead | Initial complete design authored from specification.md v1.0, layout.md v1.0, front-back-end-stack.md v1.0. Resolved decisions D-01…D-15. Sequenced scope across 3 cycles; established requirement ID scheme and traceability. No contradictions found between inputs; version-availability risks handled via A-06 ADR policy. |
| 1.1 | Cycle 1 (review) | Team Lead | Reviewed Cycle-1 deliverables. Added §2.3 ADR register (ADR-001…005), §11.1 normative contract clarifications 1–8, Cycle-1 as-built status throughout, root-file ownership assignment (DEF-001/002 root cause), DoD risk decision for DEF-001, Cycle-2 scheduling of DEF-006 + blocked security/filter tests. Requirement statuses updated from QA evidence only. |
| 1.2 | Cycle 2 (review) | Team Lead | Reviewed Cycle-2 deliverables. Closed ADR-004/DEF-003 + DEF-006 + blocked security/filter batch. Added ADR-006 (procedural root bootstrap via dev-up.sh auto-copy) and ADR-007 (cross-scope 404). Added `GET /reservations` + `/reservations` page (FR-010 completion), contract clarifications 9–11, §2.5 carried-defect register, Cycle-2 as-built status/counts. Mandated Cycle-3 tests for FR-028/TC-FR-020-04/idempotency-transfer-return-reserve; QA ID renumber. No scope weakened. |
| 1.3 | Cycle 3 (review) | Team Lead | Reviewed Cycle-3 deliverables. Reconciled four backend contract deltas as ADR-008 (approval-held `202 {approval}`), ADR-009 (synchronous report export), ADR-010 (computed-on-read data-quality queue; reverted unbuilt resolve endpoint), plus report-viewer response shape (clarification 14). Marked all FR-001…FR-030 delivered/verified per executed QA evidence; DEF-101/102 closed; §2.5 converted to final disposition register; test counts final (155 backend / 88 frontend / 161 QA passes). Recorded DEF-104 conditional risk acceptance in §17 with mandatory follow-ups. Issued release-readiness statement and post-release handoff plan. No scope weakened. |
| 1.4 | Cycle 3 (final_review — program sign-off) | Team Lead | **Final full-program review:** re-read all cycle summaries and QA execution reports (C1: 55/55 backend, 52/52 frontend, QA 39 passed + DEF-001…003 filed; C2: 109/109, 77/77, QA 84 passed; C3: 155/155, 88/88, QA 38 passed + DEF-104). Confirmed all evidence chains are consistent with the Rev 1.3 record — no new discrepancies, no undocumented deviations, no scope changes. **Definition of Done status confirmed (§17):** all FR-001…FR-030 delivered with executed API-level evidence; every NFR/BR/LAY/STK item either verified or carrying a recorded decision; all executable quality gates green at close; traceability (72 requirements) final; the defect register carries no undispositioned Critical/High item (DEF-104 open with recorded conditional acceptance + mandated follow-ups; DEF-103 accepted risk; environment-blocked verification documented as backlog, not silent). **This document is FINAL at Rev 1.4.** Standing work continues only via the post-release handoff plan. |

---