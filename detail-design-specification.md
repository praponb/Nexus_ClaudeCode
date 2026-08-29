# Asset Inventory Web Application — Detailed Design Specification

- **Document:** detail-design-specification.md
- **Version:** 1.0 (Cycle 1 — initial design)
- **Sources:** `requirements/specification.md`, `requirements/layout.md`, `requirements/front-back-end-stack.md`
- **Status:** Initial design for implementation

---

## 1. Goals, Scope, and Non-Goals

### 1.1 Goals
Deliver a secure, responsive, dark-themed web application that is the single source of truth for company assets across their lifecycle: registration, assignment, transfer, return, maintenance, stocktake, retirement, and disposal, with full audit history, role/scope-based authorization, dashboards, reports, CSV import/export, and barcode/QR support.

### 1.2 In Scope (this build)
All "Must Have" and "Should Have" items from specification.md §22: authentication, authorization, asset CRUD with unique tags, search/filter/sort/pagination, saved views, assignment/transfer/return/reservation, status & condition management with configurable transitions, maintenance, warranty/expiry tracking, lost/stolen/missing/damaged reporting, retirement & disposal workflow, attachments, notes, barcode/QR representation and browser scanning, CSV bulk import/export, dashboard, reports, stocktake sessions, in-app notifications (email behind config flag), configurable approvals, audit history, reference-data and user administration, data-quality queue, activity feed, archiving, dark theme, responsive layout, WCAG 2.2 AA.

### 1.3 Non-Goals (initial release)
Native mobile apps, network discovery, remote device control, procurement/PO processing, depreciation/GL posting, advanced contract management, GPS, RFID hardware, external-customer asset management, predictive maintenance, offline stocktake (deferred — see §3), light theme (dark is the only shipped theme; token structure allows adding light later).

---

## 2. Technology Stack (fixed by front-back-end-stack.md)

| Layer | Choice |
|---|---|
| Frontend | Nuxt 4, Vue 3 Composition API, TypeScript strict, Nuxt UI + Tailwind CSS, Pinia (only where genuinely shared), pnpm |
| Backend | Django 6.0, Django REST Framework, Python 3.12+, Psycopg 3, uv |
| Database | PostgreSQL 18 (UTF-8, UTC timestamptz) |
| Async | Celery + Redis (imports, exports, notifications, reminders, data-quality checks) |
| Object storage | S3-compatible in production; local filesystem media in dev only |
| API | Versioned JSON REST under `/api/v1/`, OpenAPI via drf-spectacular |
| Local dev | Docker Compose (`frontend`, `backend`, `postgres`, `redis`, `celery-worker`, `celery-beat`, optional MinIO) |

**Version verification rule (from stack doc §4.4):** at implementation start, Backend/Frontend agents verify Nuxt 4 ↔ Node LTS and Django 6.0 ↔ DRF ↔ Python compatibility. If a recommended major version is not mutually supported, use the newest mutually supported stable major and record the reason in `ASSUMPTIONS.md` (repo root) and an ADR.

---

## 3. Assumptions and Unresolved Questions

**Assumptions (design decisions made by Team Lead):**
1. Internal organizational use; English-only UI; Unicode storage; i18n-ready string handling.
2. **Authentication default:** Django session-cookie auth (HttpOnly, Secure, SameSite=Lax) with CSRF protection is the shipped mechanism. A local-dev login page plus seed users provide access. OIDC SSO is an integration point (mozilla-django-oidc behind `OIDC_ENABLED` settings flag), documented but not enabled without product-owner IdP details.
3. **Offline stocktake is excluded** from this release (Could Have; open decision in layout.md §32). Scanner UX always offers manual tag entry.
4. **Malware scanning:** pluggable `AttachmentScanner` interface; default implementation validates type/signature/size only. A real scanner is wired via settings when the organization provides one.
5. **Charts:** lightweight, project-owned accessible SVG/CSS chart components (bar/donut with text summaries and data-table alternative). No heavy chart dependency; avoids dark-theme/accessibility risk.
6. **Mobile bottom navigation:** Home, Assets, Scan, Tasks, More (per layout.md §6.3 recommendation).
7. **Hosting platform:** container images + Compose for dev; production deployment documented generically (reverse proxy TLS, separate web/worker/beat, managed PostgreSQL). Specific platform TBD by product owner.
8. Approval workflows, notification channels beyond in-app, and email are configurable and may be disabled; defaults: approvals required for disposal and write-off only; email disabled until SMTP configured.
9. Planning volumes per NFR-006: 100k assets, 5k users, 250 concurrent users, 1M lifecycle/audit events, 25k-row imports.

**Unresolved questions for product owner (do not block build):** final permission matrix detail, tag format/label spec, supported currencies, retention periods, RTO/RPO confirmation, IdP choice, whether logical assets (licenses) are enabled, offline stocktake need. Defaults are chosen above and recorded here.

---

## 4. Personas and User Journeys

Personas (mapped to Django groups, see §11): System Administrator, Asset Manager, Department Manager, Inventory Operator/Technician, Employee/Custodian, Auditor (read-only), Viewer (read-only, added 2026-08-28 for the public demo — global read of the register with no write, no finance fields, and deliberately no audit-log access, since audit rows carry client IP addresses).

Key journeys (from specification.md §11, all must pass E2E):
1. Register and assign a new laptop (operator → employee acknowledgement).
2. Transfer an asset between offices (approval → In Transit → receipt confirmation).
3. Perform a stocktake (create session → scan → variance → reconcile → close).
4. Record repair and return to service.
5. Retire and dispose of an asset (blocked checks → approval → disposal evidence).

---

## 5. Functional Requirements (with acceptance criteria)

Source FRs are normative (specification.md §9). The design refines them into contracts below; acceptance criteria in the source document apply unchanged.

| Design ref | Source | Design summary |
|---|---|---|
| D-FR-001 | FR-001 Auth | Session login/logout/me endpoints; unauthenticated API → 401 `AUTH_REQUIRED`; generic login failure message; security audit event on login. |
| D-FR-002 | FR-002 AuthZ | Role + organizational-scope (department/location) checks in every endpoint via DRF permission classes + scoped querysets; 403 `PERMISSION_DENIED` without data leakage; field-level restrictions for financial/personal fields via serializer field gating. |
| D-FR-003 | FR-003 Create | `POST /assets/` with category-driven required-field validation, server-side tag generation (`AST-` + zero-padded sequence, configurable), duplicate warning endpoint (`/assets/duplicate-check/`), draft save, atomic create + lifecycle event + audit. |
| D-FR-004 | FR-004 View/Edit | Asset detail aggregates identity, current assignment, warranty, location; PATCH with `version` optimistic concurrency → 409 `VERSION_CONFLICT`; field-level edit rules; change audit with before/after. |
| D-FR-005 | FR-005 Search | `GET /assets/` supports `search` (tag, serial, name, model, custodian name, location), filters (category, status, condition, department, location, custodian, supplier, warranty_state, dates), ordering, pagination; exact tag match → `GET /assets/by-tag/{tag}` for scan/deep link. |
| D-FR-006 | FR-006 Saved views | `/saved-views/` CRUD; `is_shared` restricted to authorized roles; per-user default flag. |
| D-FR-007 | FR-007 Assign | `POST /assets/{id}/assign/` — validates assignable status, closes prior active assignment in one transaction, sets status Assigned, optional acknowledgement tracking; lifecycle + audit events. |
| D-FR-008 | FR-008 Transfer | `POST /assets/{id}/transfer/` creates Transfer record (origin, destination, reason, requester); if approval configured → ApprovalRequest; on approval asset → In Transit; `POST /transfers/{id}/confirm-receipt/` closes old assignment, opens new, restores status. |
| D-FR-009 | FR-009 Return | `POST /assets/{id}/return/` captures condition, damage/missing accessories, destination; closes assignment; resulting status per rules (Available / Under Maintenance / Retired). |
| D-FR-010 | FR-010 Reservation | `/reservations/` with period-conflict validation (DB exclusion constraint on overlapping active reservations per asset), checkout/return/cancel/expire transitions; overdue flag computed and filterable. |
| D-FR-011 | FR-011 Maintenance | `/maintenance-records/`; start may set asset Under Maintenance; completion restores allowed status, sets last/next maintenance dates; attachments allowed. |
| D-FR-012 | FR-012 Warranty | `warranty_state` filter (active/expiring_30/expiring_60/expiring_90/expired), Celery-beat daily job creates notifications; report + export. |
| D-FR-013 | FR-013 Exceptions | `POST /assets/{id}/report-exception/` (missing/lost/stolen/damaged) with evidence; status change; resolution recorded as new event, never edit of original. |
| D-FR-014 | FR-014 Retire/Dispose | `retire` and `dispose` actions; BR-006 block checks (active assignment/reservation/transfer/open maintenance) unless approved exception; disposal terminal; reopen requires admin + justification (new corrective event). |
| D-FR-015 | FR-015 Attachments | Metadata in PostgreSQL, bytes in object storage; presigned/time-limited download URLs via backend authorization check; type/size/signature validation; audited upload/download/delete. |
| D-FR-016 | FR-016 Notes | `/assets/{id}/notes/`; author+timestamp; edits create superseding note (original retained); visibility per role. |
| D-FR-017 | FR-017 Barcode/QR | QR encodes asset deep-link URL `/scan/{tag}`; label print view (light print CSS); browser scanning via camera with manual fallback; unknown code → clear non-destructive result. |
| D-FR-018 | FR-018 Import | Celery-based CSV import wizard: template download → upload → validate (UTF-8, formula-injection neutralization on read) → preview with row/field errors → policy (reject/update/create; partial allowed) → commit (idempotent via job + idempotency key) → result file. Max 25k rows. |
| D-FR-019 | FR-019 Export | Async CSV export respecting filters + field permissions; UTF-8 BOM; formula-injection mitigation (prefix `'` on leading `= + - @`); job status polling; audited. |
| D-FR-020 | FR-020 Dashboard | `GET /dashboard/summary/` returns scoped KPIs (total, by status, by category, assigned/unassigned, overdue returns, maintenance due, warranty expiring, missing, recent activity) + `generated_at`. |
| D-FR-021 | FR-021 Reports | `/reports/{name}/` for the 14 default reports; filters + date ranges; totals computed from same scoped queryset as lists (reconciliation guaranteed); export when authorized. |
| D-FR-022 | FR-022 Stocktake | Session (scope, locations, operators, dates, snapshot at start) → items expected list frozen at start → observations (scan or manual; time, operator, location, condition, note/image) → computed outcomes (found, missing, unexpected, duplicate, moved, condition_mismatch) → review + apply reconciliation (transactional) → close with variance report. |
| D-FR-023 | FR-023 Notifications | In-app notification center (unread/history, mark-read); Celery beat jobs for due-date/expiry/overdue events with dedupe key; email channel behind SMTP config; mandatory vs optional classes. |
| D-FR-024 | FR-024 Approvals | Generic ApprovalRequest (target content-type/id, requester, reason, payload snapshot, status, decision, comments); separation-of-duties check (`requester != approver` when enabled); immutable history. |
| D-FR-025 | FR-025 Audit | Append-only `audit_events` table (no update/delete via app); actor, action, target, before/after JSON, correlation_id, outcome, timestamp; restricted search/export. |
| D-FR-026 | FR-026 Reference data | `/reference-data/{type}/` admin CRUD; deactivate-not-delete for in-use values; ordering + description; audited. |
| D-FR-027 | FR-027 User admin | `/admin/users/` list/role+scope assignment/activate/deactivate; guard against removing last active system admin; audited; secrets never displayed. |
| D-FR-028 | FR-028 Data quality | Nightly Celery job + on-save checks populate `data_quality_issues` (missing required, invalid refs, duplicates, expired assignments, inconsistent lifecycle); severity error/warning; work-queue endpoint + resolve action. |
| D-FR-029 | FR-029 Activity feed | `GET /assets/{id}/activity/` merges lifecycle events, assignments, transfers, maintenance, stocktake observations, notes — reverse chronological, permission-filtered. |
| D-FR-030 | FR-030 Archive | `record_status` active/archived; archive action with eligibility checks; no hard delete of operational records; retention config documented. |

---

## 6. Non-Functional Requirements

| Design ref | Source | Design commitment |
|---|---|---|
| D-NFR-001 | NFR-001 Usability | Consistent terminology, grouped forms, explicit confirmations, full state coverage (loading/empty/success/warning/error). |
| D-NFR-002 | NFR-002 Responsive | Breakpoints per layout.md §4; no page-level horizontal scroll ≥320px; card lists on mobile. |
| D-NFR-003 | NFR-003 Accessibility | WCAG 2.2 AA; axe-core in E2E; manual keyboard checklist per critical journey. |
| D-NFR-004 | NFR-004 Performance | **Targets (p95, at planning volumes, test env = Compose stack):** dashboard < 3s, filtered search < 2s, asset detail < 2s, interaction feedback < 500ms; imports/exports/reports async. Indexed query paths per §10.4. |
| D-NFR-005 | NFR-005 Reliability | Multi-record mutations in DB transactions; idempotent jobs with bounded retries; `/health/live` and `/health/ready`. Availability target 99.5% is a production-platform concern (documented). |
| D-NFR-006 | NFR-006 Scalability | Schema + indexes sized for 100k assets / 1M events; pagination caps; jobs for bulk work. |
| D-NFR-007 | NFR-007 Security | See §12. |
| D-NFR-008 | NFR-008 Privacy | Minimal personal data (name, email, department); field-level gating; no production data in dev seeds. |
| D-NFR-009 | NFR-009 Auditability | Append-only audit; correlation IDs propagated Nuxt → Django → Celery. |
| D-NFR-010 | NFR-010 Maintainability | Status transitions, category attributes, notification timing configurable via DB/admin; migrations versioned; settings externalized. |
| D-NFR-011 | NFR-011 Observability | Structured JSON logs (timestamp, severity, service, correlation_id); no secrets/PII in logs; metrics endpoints documented. |
| D-NFR-012 | NFR-012 Backup | Documented pg_dump + object-storage backup procedure; RTO ≤ 8h / RPO ≤ 24h initial target; restore test procedure documented. |
| D-NFR-013 | NFR-013 Browsers | Latest two majors of Edge/Chrome/Firefox/Safari; Playwright matrix covers Chromium/Firefox/WebKit. |
| D-NFR-014 | NFR-014 Localization | English UI; all user strings via constants; ISO 8601 API dates; locale-aware display formatting; Unicode storage. |

---

## 7. Page Inventory and Navigation

Routes (Nuxt file-based). All authenticated routes client-rendered (`ssr: false` for the app shell) except sign-in/help which may SSR. No confidential data in public payload caches.

| Route | Page | Roles |
|---|---|---|
| `/login` | Sign in | public |
| `/` | Dashboard (KPIs, charts, tasks, alerts, recent activity) | all |
| `/assets` | Asset register (table desktop / cards mobile, filters, saved views) | all scoped |
| `/assets/new` | Create asset | Operator+ |
| `/assets/[id]` | Asset detail: Overview, Assignment, Maintenance, Documents, Activity, Audit* tabs | scoped |
| `/assets/[id]/edit` | Edit asset | Operator+ |
| `/scan` | Scanner + manual tag entry | Operator+ (all for lookup) |
| `/scan/[tag]` | Scan resolution → asset or unknown-code state | scoped |
| `/assignments` | Assignments & transfers work queue | Operator+ |
| `/maintenance` | Maintenance dashboard (open/scheduled/history) | Operator+ |
| `/stocktakes`, `/stocktakes/[id]` | Stocktake list and session (progress, scan, variance) | Manager/Operator |
| `/approvals` | Pending approvals | approvers |
| `/reports`, `/reports/[name]` | Report catalog and viewer | scoped |
| `/imports`, `/exports` | Import wizard, export jobs | Manager+ |
| `/notifications` | Notification center | all |
| `/admin` (users, reference-data, statuses, categories, attributes, notification rules) | Administration | Admin |
| `/my-assets` | Employee's assigned assets + report actions | Employee |
| `/help` | Help/shortcut reference | all |
| `/403`, `/404`, error pages | Error states | all |

Navigation: desktop persistent collapsible sidebar; tablet icon/drawer; mobile top bar + bottom nav (Home, Assets, Scan, Tasks, More) + drawer. Role-aware items; hiding is UX-only — backend enforces. Breadcrumbs on desktop nested pages; mobile back action. Deep links resume after login.

---

## 8. Responsive and Accessibility Requirements

- Breakpoints (guidance): 320–479, 480–767, 768–1023, 1024–1439, ≥1440. Content-driven; usable at 320px without horizontal scroll; 200% zoom without loss of function.
- Desktop: 12-column grid, sticky table headers, max readable form widths, side summary panels for wizards.
- Mobile: single column, labels above inputs, sticky bottom action bars where safe, full-screen sheets for dialogs/filters, 44×44px touch targets, safe-area insets, no hover-only behavior.
- Dark theme tokens from layout.md §5.2 implemented as Tailwind theme tokens (single source in `frontend/app.config.ts` + CSS variables); no unthemed flash (inline theme script / default-dark HTML class); status = icon + label + semantic color, never color alone; pure black/white avoided on large areas.
- Typography: system sans stack, 16px body (14px metadata minimum), monospace for tags/serials, sentence case.
- Accessibility: semantic landmarks, skip link, focus-visible ring token, focus trap + restore in modals, Escape dismissal, aria-live for toasts/results, chart text alternatives + data tables, `prefers-reduced-motion` respected, errors associated to fields + summary with focus management.
- Print: light-background print stylesheet for labels, asset summary, receipts (assignment/transfer), stocktake report, disposal record; QR remains scannable.

---

## 9. Frontend Design

### 9.1 Architecture
- `frontend/` Nuxt 4 + TS strict, `<script setup lang="ts">`, ESLint, Vitest + Vue Test Utils, Playwright (in `testcase/`).
- Feature-based organization under `features/` (dashboard, assets, assignments, maintenance, stocktakes, imports, reports, notifications, approvals, admin, auth) plus `components/ui` primitives.

### 9.2 Component hierarchy (per layout.md §31)
```
AppShell
├── AppSidebar / MobileBottomNavigation / AppTopBar (GlobalAssetSearch, NotificationCenter, user menu)
└── <NuxtPage>
    ├── PageHeader (breadcrumb, title, primary action, overflow)
    ├── DashboardPage → KpiCard, AccessibleChartPanel, TaskList, ActivityList
    ├── AssetsPage → FilterBar/FilterDrawer (chips), AssetTable (desktop) / AssetCardList (mobile), PaginationBar, SavedViewMenu
    ├── AssetDetailPage → AssetIdentityHeader, AssetStatusBadge, tab panels, AssetActivityTimeline, StickyActionBar
    ├── AssetFormPage → ResponsiveFormSection(s), DuplicateWarningDialog, ConfirmActionDialog
    ├── workflow dialogs → AssignDialog, TransferDialog (From/To compare), ReturnDialog, MaintenanceDialog, RetireDisposeWizard
    ├── StocktakeSessionPage → StocktakeProgress, ScannerPanel, VarianceList
    ├── ImportWizard (8 steps per layout.md §17.1)
    └── shared: EmptyState, InlineAlert, FullScreenMobileSheet, ErrorState, Skeleton loaders
```

### 9.3 State management
- `useState`/composables default; Pinia stores only for: session/user, notification badge count, saved-view cache. Server data via composables (`useAssets`, `useAsset`, …) wrapping the typed client; no duplicated server state across stores.
- Filters/pagination/sort in URL query params (bookmarkable); list→detail→back preserves position via query.
- Theme: dark-only class strategy; token CSS variables.

### 9.4 API client
- `utils/apiClient.ts` around `$fetch`: base URL from runtime config (`API_BASE_URL`), injects `X-CSRFToken` (from cookie) and `X-Correlation-ID` (uuid per request, propagated), maps error envelope to typed `ApiError` (code, message, field_errors, correlation_id), 401 → redirect to `/login?next=`, no retry of non-idempotent requests unless `Idempotency-Key` set (auto-generated for create/action posts).
- TypeScript types generated from backend OpenAPI (openapi-typescript) into `types/api.d.ts`; CI validates drift.

### 9.5 Forms and feedback
- Required marked with text+asterisk; client validation mirrors server rules but server is canonical; failed submit → error summary + focus first invalid; values preserved; unsaved-changes guard; submit disabled while pending (loading button keeps width); success → toast + resulting record link; destructive actions → ConfirmActionDialog naming asset + consequence with action-specific button text.

---

## 10. Backend Design

### 10.1 Project layout (per stack doc §7.2)
`config/settings/{base,local,test,production}.py`; apps: `accounts`, `assets`, `assignments`, `maintenance`, `stocktakes`, `reporting`, `notifications`, `audit`, `reference_data`, plus `core` (middleware, pagination, errors, permissions) and `files` (attachments). Business rules in `services.py` per app (transactions here); serializers = representation + boundary validation; no business side effects in signals.

### 10.2 Data model (key entities; all have `id` UUID public PK, `created_at`, `updated_at`; money = `DecimalField` + `currency CharField(3)`; timestamps `timestamptz` UTC)

- **accounts.User** (extends AbstractUser): email unique, display_name, role (M2M Group), department_scope (M2M Department, empty = all per role), is_active.
- **reference_data:** Department, Location (site/building/floor/room fields, hierarchical self-FK optional), CostCenter, Supplier, Category(parent self-FK for subcategory, required_fields JSONB config), StatusDefinition(key, label, is_terminal, allowed_transitions JSONB, active), ConditionDefinition, DisposalMethod, MaintenanceType, AttributeDefinition(category FK, key, label, field_type, required, options JSONB, restricted bool).
- **assets.Asset:** asset_tag (unique, immutable), name, description, category FK, serial_number (index), manufacturer, brand, model, status FK, condition FK, department FK, location FK, custodian FK(User, null), cost_center FK, supplier FK, acquisition_type, purchase_date, purchase_price+currency (restricted), po_reference, invoice_reference, warranty_provider/start/end, service_contract_ref/end, last_maintenance_at, next_maintenance_due, expected_life_end, retired_at, disposed_at, disposal_method/reason, parent_asset self-FK, barcode_value, external_source/external_id (unique together, null allowed), category_attributes JSONB (validated against AttributeDefinition), data_quality_status, record_status (active/archived), **version IntegerField** (optimistic concurrency), created_by/updated_by.
- **assignments.Assignment:** asset FK, custodian FK, department FK, location FK, assigned_at, expected_return_at, returned_at, status (active/closed), acknowledgement_required/acknowledged_at/acknowledged_by, notes. Partial unique index: one active assignment per asset.
- **assignments.Transfer:** asset FK, from_custodian/from_location, to_custodian/to_location, reason, requested_by, status (pending_approval/in_transit/completed/cancelled/rejected), approval FK, requested_at/completed_at, evidence.
- **assignments.Reservation:** asset FK, requester, start_at, end_at, purpose, status (reserved/checked_out/returned/cancelled/expired); exclusion constraint preventing overlapping active periods per asset.
- **assets.LifecycleEvent:** asset FK, event_type, actor FK, at, from_status, to_status, summary, payload JSONB, correlation_id.
- **maintenance.MaintenanceRecord:** asset FK, type FK, issue, technician/provider, started_at, completed_at, cost+currency (restricted), result, notes, status(open/completed/cancelled).
- **approvals.ApprovalRequest:** content_type/object_id (generic), requester, approver, reason, payload_snapshot JSONB, status (pending/approved/rejected/returned), decided_at, comments.
- **stocktakes.StocktakeSession:** name, scope JSONB (locations/departments/categories), operators M2M, start/due dates, status (draft/active/reconciling/closed), snapshot_at, instructions. **StocktakeItem:** session, asset, expected_location, outcome. **StocktakeObservation:** session, asset(nullable for unknown), tag_scanned, observed_by, observed_at, observed_location, observed_condition, note, image FK.
- **files.Attachment:** asset FK (+ generic FK for maintenance/disposal evidence), storage_key, original_name (sanitized), content_type, size, uploaded_by, scan_status, created_at.
- **assets.Note:** asset FK, author, body, created_at, superseded_by self-FK.
- **notifications.Notification:** user FK, type, title, body, link, dedupe_key (unique), read_at, created_at, channel log.
- **audit.AuditEvent:** actor FK (+service_name), action, target_type/target_id, before JSONB, after JSONB, correlation_id, outcome, at. Append-only (DB revoke UPDATE/DELETE for app role documented; app never issues them).
- **assets.SavedView:** user FK, name, config JSONB, is_shared, is_default.
- **jobs.ImportJob / ExportJob:** user, file/storage_key, status (queued/processing/completed/failed), policy JSONB, result_summary JSONB, result_file_key, idempotency_key unique, correlation_id, timestamps.
- **assets.DataQualityIssue:** asset FK, rule_key, severity, message, status(open/resolved), detected_at, resolved_by/at.

### 10.3 Migrations and seed data
- One initial migration per app; constraints (unique asset_tag, partial unique active assignment, check constraints for date ordering where expressible, e.g. warranty_end ≥ warranty_start).
- `seed-dev.sh` runs a management command creating: groups/permissions for the 6 seeded roles; default statuses (13 per spec §8.1) with transition map; conditions (6); demo departments (3), locations (2 sites), cost centers, suppliers, categories (Laptop, Monitor, Phone, Furniture, Vehicle-equipment) with attribute definitions; users `admin`, `manager`, `operator`, `deptmanager`, `employee`, `auditor` (password `change-me-dev` documented, dev only); ~50 sample assets with assignments, maintenance, one stocktake. No real personal data.

### 10.4 Indexing
Indexes on: asset_tag (unique), serial_number, (status), (condition), (category), (custodian), (department), (location), warranty_end, next_maintenance_due, created_at/updated_at, (external_source, external_id); trigram (`pg_trgm`) indexes on name/serial/asset_tag for search; assignments (asset, status) partial; audit (target_type, target_id), (at).

### 10.5 Service boundaries and transactions
- `assets/services.py`: create_asset, update_asset (version check), change_status (validates transition map, reason/approval requirements), retire, dispose (BR-006 checks).
- `assignments/services.py`: assign, initiate_transfer, confirm_receipt, return_asset, reserve/checkout — each `@transaction.atomic`, closing prior assignment, writing LifecycleEvent + AuditEvent in the same transaction.
- `stocktakes/services.py`: start (snapshot expected items), record_observation (idempotent per session+tag), compute_variance, apply_reconciliation (reviewed updates only), close.
- `reporting/services.py`: shared scoped querysets reused by dashboard/reports/exports to guarantee reconciliation.
- `notifications/services.py`: emit(type, users, payload, dedupe_key) — insert-or-ignore; beat jobs call this.
- `jobs/services.py`: import pipeline (parse → validate → preview → commit), export pipeline; idempotent via job id + unique idempotency keys; bounded Celery retries with backoff.

---

## 11. API Contracts (summary — canonical contract = generated OpenAPI)

**Conventions:** base `/api/v1/`; JSON; list envelope `{ "results": [...], "page": 1, "page_size": 25, "count": 1234 }` (default 25, max 200); errors use the stack-doc envelope `{ "error": { code, message, field_errors, correlation_id } }`; ISO 8601 datetimes with TZ; money `{ "amount": "1234.56", "currency": "USD" }`; mutation POSTs accept `Idempotency-Key` (replay returns stored response, 24h); PATCH requires `version` in body → stale = 409 `VERSION_CONFLICT`; stable error codes (`AUTH_REQUIRED`, `PERMISSION_DENIED`, `VALIDATION_ERROR`, `NOT_FOUND`, `VERSION_CONFLICT`, `ASSET_STATUS_TRANSITION_INVALID`, `ASSET_NOT_ASSIGNABLE`, `DISPOSAL_BLOCKED`, `DUPLICATE_TAG`, `RESERVATION_CONFLICT`, `IMPORT_VALIDATION_FAILED`, `RATE_LIMITED`, …).

**Endpoint groups:**
- `POST /auth/login/`, `POST /auth/logout/`, `GET /auth/me/`, `GET /auth/csrf/`
- `GET|POST /assets/`, `GET|PATCH /assets/{id}/`, `GET /assets/by-tag/{tag}/`, `POST /assets/duplicate-check/`
- `POST /assets/{id}/assign|transfer|return|retire|dispose|report-exception|archive/`
- `GET /assets/{id}/activity/`, `GET|POST /assets/{id}/notes/`, `GET|POST|DELETE /assets/{id}/attachments/`, `GET /attachments/{id}/download/` (authorized, redirect to time-limited URL)
- `GET /assignments/`, `GET /transfers/`, `POST /transfers/{id}/confirm-receipt/`, `GET|POST /reservations/`, `POST /reservations/{id}/checkout|return|cancel/`
- `GET|POST /maintenance-records/`, `POST /maintenance-records/{id}/complete/`
- `GET|POST /stocktakes/`, `GET /stocktakes/{id}/`, `POST /stocktakes/{id}/start|close/`, `POST /stocktakes/{id}/observations/`, `GET /stocktakes/{id}/variance/`, `POST /stocktakes/{id}/reconcile/`
- `GET /approvals/`, `POST /approvals/{id}/approve|reject|return/`
- `GET|POST /saved-views/`, `PATCH|DELETE /saved-views/{id}/`
- `GET|POST /imports/`, `GET /imports/{id}/`, `GET /imports/template/`, `GET /imports/{id}/result/`
- `POST /exports/`, `GET /exports/{id}/`, `GET /exports/{id}/download/`
- `GET /dashboard/summary/`, `GET /reports/`, `GET /reports/{name}/`
- `GET /notifications/`, `POST /notifications/{id}/read/`, `POST /notifications/read-all/`
- `GET|POST /reference-data/{type}/`, `PATCH|DELETE /reference-data/{type}/{id}/`
- `GET|POST /admin/users/`, `PATCH /admin/users/{id}/`
- `GET /audit-events/` (Admin/Auditor only), `GET /data-quality/`, `POST /data-quality/{id}/resolve/`
- `GET /health/live/`, `GET /health/ready/` (public, minimal)

Status codes: 200/201/204; 400 VALIDATION_ERROR; 401; 403; 404; 409; 429; 500 (generic message + correlation_id only).

---

## 12. Security, Privacy, Logging, Error Handling

- Transport: HTTPS outside dev; HSTS, secure headers middleware; restrictive CSP (no inline scripts beyond nonce'd theme bootstrap); CORS explicit allowlist; CSRF on cookie-authenticated mutations (double-submit via `X-CSRFToken`).
- Sessions: HttpOnly/Secure/SameSite=Lax cookies, 30-minute idle timeout (`SESSION_IDLE_SECONDS`, sliding), rotation on login; expired → 401 → UI redirect. Never tokens in localStorage.
- Rate limiting (Redis-backed) on login, search, and import/export. Implemented 2026-08-28: throttle counters live in the default cache, which must be Redis — the Django default (`LocMemCache`) is per-process and would multiply every limit by the gunicorn worker count and reset it on each deploy.
- Throttle identity comes from one explicitly trusted client-IP header (`TRUSTED_CLIENT_IP_HEADER`, `CF-Connecting-IP` behind Cloudflare) then `REMOTE_ADDR`. **`X-Forwarded-For` is never trusted** — it is caller-supplied, so keying on it lets an attacker rotate the header for a fresh bucket per request.
- Per-account lockout on failed sign-ins, counted per username so a distributed attack cannot sidestep the per-IP limit. Counted for unknown usernames too, so the lockout cannot be used to enumerate accounts; exempt usernames are configurable for shared public accounts.
- Two-factor authentication (TOTP, RFC 6238) required for roles in `MFA_REQUIRED_ROLES`. Sign-in is two-phase and never establishes a session until the second factor is satisfied. Recovery codes are single-use and stored hashed; a used time-step is recorded to refuse replay.
- Input: server-side validation everywhere; ORM parameterization; CSV formula-injection mitigation in/out; upload type+signature+size validation; filenames sanitized; downloads authorized per request.
- Output: Vue auto-escaping; no `v-html` on user data; API errors never leak stack traces/paths/settings; generic 500 with correlation_id.
- Secrets: the checked-in `backend/.env` and `scripts/templates/.env` hold names/placeholders only (there is deliberately no `.env.example`); production settings fail fast on missing or insecure values; DEBUG off in production; ALLOWED_HOSTS/CSRF trusted origins explicit. The real root `.env` is gitignored — which also means production configuration is not backed up by `git push`, and a regression there leaves no trace in git.
- Privacy: employee PII limited to name/email/department; financial fields (purchase_price, costs, proceeds) gated by `view_financials` permission at serializer level and excluded from exports/reports when unauthorized.
- Logging: structured JSON via `structlog`-style config (timestamp, level, service, correlation_id from `X-Correlation-ID` middleware, user id hash); correlation ID created at Nuxt, forwarded to Celery tasks; PII/secrets masked; audit events (business) kept separate from diagnostic logs.

---

## 13. Frontend/Backend Integration Rules

1. Django = source of truth for rules, authZ, persistence, canonical validation. Nuxt = presentation, UX validation, feedback.
2. OpenAPI schema generated (`./manage.py spectacular --file openapi.yaml`), committed to `backend/openapi.yaml`; frontend types regenerated; CI fails on unchecked drift.
3. Only the typed client calls the API; components never fetch directly.
4. List pagination/filter metadata consistent; filters mirrored in URL query.
5. Correlation IDs both directions; user-facing unexpected errors show the ID.
6. Non-idempotent retries only with Idempotency-Key.
7. Optimistic UI allowed only for low-risk reversible actions (e.g., note add); lifecycle/assignment/transfer/approval/stocktake/disposal wait for confirmed backend result.
8. Breaking API change → `/api/v2/`; deprecation documented.

---

## 14. Testing Strategy and Traceability

**Backend (pytest, pytest-django, factory_boy; PostgreSQL in CI):** model/constraint tests, service unit tests (transitions, BR rules, transactions), serializer validation, API integration incl. authZ matrix (each role × endpoint, horizontal/vertical escalation), OpenAPI contract test, concurrency (stale version, double-assign), import/export (valid/invalid/duplicate/Unicode/large), attachment authZ, audit completeness, job idempotency. Quality gates: ruff format/check, mypy, `makemigrations --check`, `check --deploy`, pytest.

**Frontend (Vitest + Vue Test Utils):** composables, api client error mapping, key components (AssetStatusBadge, FilterBar, forms, dialogs) with state coverage (loading/empty/error/unauthorized); `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`.

**E2E/QA (Playwright, `testcase/`):** journeys J1–J5 (§4); auth flows; permission matrix spot checks via UI + direct API; axe-core accessibility scans per page + keyboard walkthrough; responsive matrix per layout.md §30 (8 viewport sizes × core pages); scanner manual-fallback; import/export round-trip; evidence (screenshots/traces) stored under `testcase/evidence/`.

**Traceability:** test IDs prefixed by area — `QA-E2E-###` (journeys/pages), `QA-A11Y-###`, `QA-RESP-###`, `BE-API-###`, `BE-SVC-###`, `FE-UT-###`. The QA agent maintains `testcase/traceability.md` mapping REQ-ids → test IDs. No test marked passed without executed evidence.

---

## 15. Local Development, Build, Deploy, Operations

- Root scripts (idempotent, fail-fast, env-labeled): `scripts/dev-up.sh` (compose up), `scripts/migrate.sh`, `scripts/seed-dev.sh`, `scripts/check.sh` (all lint/type/test gates), `scripts/dev-down.sh`.
- Compose services: frontend (Nuxt dev, :3000), backend (Django, :8000), postgres:18, redis, celery-worker, celery-beat, optional minio.
- Backend quality: `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy .`, `uv run python manage.py makemigrations --check --dry-run`, `uv run python manage.py check --deploy` (with safe CI settings), `uv run pytest`.
- Frontend quality: `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`, `pnpm test:e2e`.
- Production (documented): immutable OCI images (non-root), ASGI server for Django (uvicorn/gunicorn-uvicorn), Nuxt node server behind reverse proxy with TLS, separate web/worker/beat, managed PostgreSQL with encrypted backups + PITR, migration as controlled release step, S3 bucket private with presigned access, health/readiness endpoints, centralized logs + alerts. RTO ≤ 8h, RPO ≤ 24h target; restore procedure tested and documented in README/ops docs.
- Docs required at completion: root README (setup/commands), env-var reference, authZ explanation, ADRs for any stack deviation, `ASSUMPTIONS.md` for version fallbacks.

---

## 16. Definition of Done (this project)

Per specification.md §18 plus stack doc §19: acceptance criteria implemented; authZ enforced UI + API; validation/loading/empty/error states done; audit events recorded; automated tests added and executed with evidence; accessibility + responsive verified against the layout.md §29–30 matrices; docs updated; no unresolved critical/high defects without recorded risk decision; all quality-gate commands pass.

---

## 17. Requirement Traceability

Maintained in machine-readable form by the Team Lead (`requirements_json` each cycle: REQ-1…REQ-30 = FR-001…FR-030; REQ-31…REQ-40 = BR-001…BR-010; REQ-41…REQ-54 = NFR-001…NFR-014; REQ-55…REQ-61 = layout requirements; REQ-62…REQ-71 = stack requirements; REQ-72+ = deferred/decisions). QA mirrors this in `testcase/traceability.md`.

---

## 18. Revision History

| Rev | Cycle | Changes |
|---|---|---|
| 1.0 | Cycle 1 (initial design) | First complete design synthesized from specification.md, layout.md, front-back-end-stack.md. Resolved open decisions: local session auth default with OIDC integration point; offline stocktake deferred; pluggable attachment scanner (validate-only default); lightweight accessible custom charts; Home/Assets/Scan/Tasks/More bottom nav; container-based hosting with platform TBD; defined p95 performance targets per NFR-004; defined data model, API surface, service boundaries, and 3-cycle delivery split. No contradictions found between source documents; noted version-verification fallback (stack doc §4.4) for Nuxt 4 / Django 6.0 / PostgreSQL 18 compatibility. |
