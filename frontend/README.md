# Asset Inventory — Frontend

Nuxt 4 + Vue 3 + TypeScript (strict) SPA/SSR frontend for the Asset Inventory
application. Implements `requirements/layout.md` (dark theme, responsive,
WCAG 2.2 AA) against the v1 API contract in `detail-design-specification.md`.

## Commands

```bash
npm install        # install dependencies (also runs `nuxt prepare`)
npm run dev        # Nuxt dev server on :3000
npm run lint       # ESLint (flat config via @nuxt/eslint)
npm run typecheck  # nuxi typecheck (vue-tsc, strict)
npm run test       # Vitest unit/component tests
npm run build      # production build (.output)
npm run test:e2e   # Playwright E2E (requires the compose stack running)
```

## Configuration

Only public values are exposed to the browser:

| Variable | Default | Purpose |
| --- | --- | --- |
| `NUXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api/v1` | Backend v1 API base URL |
| `E2E_BASE_URL` | `http://localhost:3000` | Playwright target (E2E only) |
| `E2E_ADMIN_USER` / `E2E_ADMIN_PASSWORD` | `admin` / unset | Seeded dev user for authenticated E2E |
| `E2E_API_BASE_URL` | `http://localhost:8000/api/v1` | Direct API calls in E2E (conflict simulation) |

## Feature map

**Cycle 1–2 (delivered, verified):**

- Auth shell, dashboard (KPIs + alert indicators + ranked lists + recent activity)
- Asset register (URL-synced filters, table↔cards, saved views, export view)
- Asset CRUD with duplicate pre-check, optimistic concurrency, unsaved-changes guard
- Lifecycle workflows: assign / transfer / return / report exception (Idempotency-Key, confirmed-only success)
- Reservation dialog on the asset detail (validated window, 409 overlap as non-destructive warning)
- Maintenance work list + per-asset records with overdue flagging
- Attachments (validated upload, authorized download, audited delete) and notes
- Full activity feed (`/assets/:id/activity`, C1 history fallback)
- QR label print (50×25mm) + camera scanning (qr-scanner + BarcodeDetector fallback) with manual entry
- CSV import wizard (template → upload → validate/preview → policy → async commit → result report)
- Export center (async jobs, filter carry-over, status polling, download)
- Stocktakes: sessions, mobile count (scan/manual + condition/note), observations, variance, start/reconcile/close

**Cycle 3 (control & polish):**

- Reservations list (`/reservations`, FR-010 completion): scoped table, status + overdue filters, overdue badges
- Approvals inbox (`/approvals`, FR-024): pending/history views, approve/reject/return dialog with mandatory
  comments for non-approvals, separation-of-duties hint, immutable decisions
- Notification center (`/notifications`, FR-023): unread filter, mark-read, authorized deep links,
  preferences panel (email toggle, per-type checkboxes, mandatory compliance types non-disableable)
- Reports (`/reports` catalog + `/reports/[type]` viewer, FR-021): date range + declared filters,
  reconciled totals footer, supporting-record links, authorized export
- Retirement / disposal / reopen (FR-014, J-5): elevated-permission dialogs with mandatory
  reason/justification, BR-006 `DISPOSAL_BLOCKED` blockers listed verbatim, terminal-by-default disposal
- Administration (`/admin`, FR-026/027/030 + FR-025 read): user table + role/activation editor
  (final-admin protection server-side), reference-data manager (create/edit/deactivate per BR-004),
  workflow transition-rule viewer, audit-log search (append-only), retention/archiving policy page
- Data-quality work queue (`/data-quality`, FR-028): errors vs warnings, resolve preserving history,
  linked from the dashboard

## Architecture notes

- Rendering: SSR shell + client-only private data fetching (design D-11); no
  private inventory data is ever rendered into SSR payloads.
- All backend traffic goes through `app/composables/useApi.ts` (correlation
  IDs, CSRF header, credentials, timeout, GET-only retry, error-envelope
  mapping). Components never call `$fetch` directly.
- All endpoints use DRF trailing slashes; unsafe retry-sensitive POSTs send an
  `Idempotency-Key` (design D-08).
- List filter/sort/pagination state lives in URL query params (shareable).
- Theme tokens live in `app/assets/css/main.css` (`@theme` block) — components
  use semantic utilities (`bg-surface`, `text-muted`, ...), never hex values.
- Cycle-3 contract types are hand-written in `app/types/control.ts` against
  design Rev 1.2 §11.3; list endpoints tolerate array-or-envelope responses
  (Rev 1.1 §11.1.7) and report/preference payloads are normalized defensively.

## Recorded deviations (ADR summary)

1. **npm instead of pnpm** (ADR-001) — the controlled build environment only
   exposes npm-based quality commands; scripts are package-manager agnostic.
2. **Hand-rolled accessible components instead of the Nuxt UI library**
   (ADR-002) — permitted by layout.md §31; keeps the §5.2 token palette exact.
3. **Tailwind CSS v4** via the official Vite plugin (theme in CSS `@theme`).
4. **Camera scanning**: `qr-scanner` JS library first, native `BarcodeDetector`
   as fallback, manual entry always available (layout §15.2 fallback rule).
5. **Reports module routing**: `pages/reports.vue` is a thin `<NuxtPage />`
   shell so the catalog (`reports/index.vue`) and viewer (`reports/[type].vue`)
   can coexist without a route conflict; same pattern for `pages/admin.vue`.

## Governance & Vulnerability Audit (DEF-104)

- **Cycle 1 Disposition**: The initial Cycle 1 `npm audit` flagged transitive dev dependencies (`happy-dom`, `nanoid`) used exclusively for unit testing in Vitest. Dev dependencies are excluded from the Nuxt production build artifact (`.output`, ~3.07 MB).
- **Resolution**: Updated `happy-dom` to the latest release (`^20.11.2`) and executed `npm audit fix`. Re-auditing with `npm audit` confirms **0 vulnerabilities** across all dependencies. Unit test suite (101 tests) and typechecking continue to pass cleanly.

