# Cycle 1 — UI Shell, Theme, Navigation, and State Tests (NFR-001; LAY-2, LAY-3, LAY-4, LAY-5; FR-001 UI)

Preconditions: stack running; browser available (Playwright or manual). Pages in scope: `/login`, `/`, `/assets`, `/assets/new`, `/assets/[id]`, `/assets/[id]/edit`, `/assets/[id]/history`, `/403`, `/404`, `/error`.

---

### TC-LAY3-01 — Desktop shell: persistent collapsible sidebar + top bar
- **requirement_ids:** LAY-3, NFR-001
- **priority:** High | **type:** UI | **automation_status:** MIXED
- **steps:** Login at 1440×900. Inspect shell; collapse/expand sidebar; navigate sections.
- **expected_result:** Persistent left sidebar with role-appropriate entries (Dashboard, Assets, …; deferred modules hidden or marked); top bar with page context, global search, profile/session menu; sidebar collapse persists during session; active section visually and programmatically indicated (`aria-current`); main content fluid with sensible max widths on forms.
- **status:** NOT_RUN

### TC-LAY3-02 — Tablet shell: collapsed rail or drawer
- **requirement_ids:** LAY-3, NFR-002
- **priority:** Medium | **type:** UI/Responsive | **automation_status:** MIXED
- **steps:** View at 768×1024 and 1024×768; open/close navigation.
- **expected_result:** Sidebar defaults to icon rail or drawer; top bar compact; drawer opens/closes via keyboard and touch; focus managed on open/close.
- **status:** NOT_RUN

### TC-LAY3-03 — Mobile shell: top bar + bottom navigation
- **requirement_ids:** LAY-3, NFR-002
- **priority:** High | **type:** UI/Responsive | **automation_status:** MIXED
- **steps:** View at 390×844 and 320×568; use bottom nav; open More/drawer.
- **expected_result:** Bottom nav with Home, Assets, Scan, Tasks, More (Scan/Tasks may be accessible "coming soon" stubs per cycle plan); every item has a text label (Scan prominent but labeled); single-column content; bottom padding prevents content hidden behind nav; no hover-only interactions.
- **status:** NOT_RUN

### TC-LAY3-04 — Breadcrumbs and back behavior
- **requirement_ids:** LAY-3, NFR-001
- **priority:** Medium | **type:** UI | **automation_status:** MIXED
- **steps:** Desktop: navigate Assets → asset detail; use breadcrumb back to register. Mobile: same flow using back action. Use browser back/forward.
- **expected_result:** Breadcrumbs on desktop nested pages; mobile back action + concise parent context; list position/filters preserved on return where practical; browser back/forward predictable.
- **status:** NOT_RUN

### TC-LAY3-05 — Global search box behavior
- **requirement_ids:** FR-005, LAY-3
- **priority:** High | **type:** UI | **automation_status:** MIXED
- **steps:** From dashboard, use global search: type a tag, use arrow keys through suggestions, Enter to open; search with no matches; search while offline/failing (if simulatable).
- **expected_result:** Search reachable within one action from primary pages; visible label/accessible name (not placeholder-only); exact-tag result first; suggestions keyboard-navigable; loading, no-match, and error states distinct and clear; mobile search expands to dedicated view if designed.
- **status:** NOT_RUN

---

### TC-LAY2-01 — Dark theme applied consistently, no unstyled flash
- **requirement_ids:** LAY-2, NFR-002
- **priority:** High | **type:** UI | **automation_status:** MIXED
- **steps:** Hard-reload `/login`, `/`, `/assets` (throttle network if possible) and observe initial paint; inspect pages, dialogs, forms, tables, error states.
- **expected_result:** No light/unstyled flash on load (SSR color-scheme bootstrap present, `<html class="dark">` default); canvas/surface/border tokens per layout §5.2 applied; no pure-black large backgrounds / pure-white body text; theme consistent across all delivered pages and states.
- **status:** NOT_RUN

### TC-LAY2-02 — Semantic tokens, no hard-coded hex in components
- **requirement_ids:** LAY-2, NFR-010
- **priority:** Medium | **type:** Code/Static | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Search `frontend/` components for raw hex colors (excluding the token definition files).
- **expected_result:** Components reference semantic tokens (`bg-surface`, `text-muted`, etc.); palette hex values confined to the token/theme source of truth.
- **status:** NOT_RUN

### TC-LAY2-03 — Status badges: icon + text + semantic color
- **requirement_ids:** LAY-2, NFR-003
- **priority:** High | **type:** UI/A11y | **automation_status:** MIXED
- **steps:** View asset list and detail with varied statuses (Available, Draft, Under Maintenance, Missing… per seed).
- **expected_result:** Every status/condition badge has label text + icon + semantic color + high-contrast badge style; meaning never conveyed by color alone; screen-reader text equivalent present; exact database status readable in text.
- **status:** NOT_RUN

---

### TC-LAY4-01 — Asset detail layout and identity header
- **requirement_ids:** FR-004, LAY-4
- **priority:** High | **type:** UI | **automation_status:** MIXED
- **steps:** Open a seeded asset detail at desktop and mobile widths; switch tabs (Overview, History/Activity).
- **expected_result:** Identity header: tag (monospace, selectable with Copy affordance), name, category/manufacturer/model, status + condition badges, custodian, department/location, primary contextual action; tabs keyboard-operable; mobile: compact header, status/condition directly under name, horizontally scrollable accessible tabs or accordions; long asset names wrap without pushing actions off-screen.
- **status:** NOT_RUN

### TC-LAY4-02 — History/activity tab
- **requirement_ids:** FR-004, FR-029, LAY-4
- **priority:** High | **type:** UI | **automation_status:** MIXED
- **steps:** Open history tab for an asset with create + edit events.
- **expected_result:** Reverse-chronological timeline; each event shows type icon + label, actor, timestamp, summary; no color-only meaning; empty state if no events; long details progressively disclosed.
- **status:** NOT_RUN

### TC-LAY4-03 — Error pages 403/404/error
- **requirement_ids:** NFR-001, LAY-5
- **priority:** High | **type:** UI | **automation_status:** MIXED
- **steps:** Navigate to a nonexistent route; open an asset URL the user cannot access (scoped user); trigger/visit the generic error page if reachable.
- **expected_result:** Dedicated branded 404 and 403 pages with plain-language explanation and recovery actions (Back, Home); error view offers Retry/support reference; no stack traces; pages respect theme and a11y (heading structure, landmarks).
- **status:** NOT_RUN

### TC-LAY5-01 — Loading, empty, and unauthorized states
- **requirement_ids:** NFR-001, LAY-5
- **priority:** High | **type:** UI | **automation_status:** MIXED
- **steps:** Throttle network to observe dashboard/list skeletons; apply filters matching nothing; view as a user with empty scope (if seedable).
- **expected_result:** Skeletons match content structure (no indefinite bare spinners for long ops); empty states distinguish "no assets", "no results match filters", "no access" and suggest next actions; partial failures never shown with success styling.
- **status:** NOT_RUN

### TC-LAY5-02 — Error surfaces include correlation ID
- **requirement_ids:** NFR-001, NFR-009, LAY-5
- **priority:** Medium | **type:** UI/Integration | **automation_status:** MIXED
- **steps:** Force an API error in the UI (e.g., stop backend, attempt save) — restore service afterwards.
- **expected_result:** Inline alert shows plain-language explanation, recovery action (Retry), and the correlation/support reference; raw exceptions never displayed; user input preserved.
- **status:** NOT_RUN

### TC-LAY5-03 — Buttons, menus, dialogs interaction standards
- **requirement_ids:** NFR-001, LAY-5
- **priority:** Medium | **type:** UI | **automation_status:** MIXED
- **steps:** Inspect primary/secondary/danger buttons on delivered pages; open overflow menus and any confirmation dialogs (e.g., unsaved-changes guard); press Escape.
- **expected_result:** One dominant primary action per task area; action-specific labels (`Save asset`, not `Submit`); icon-only buttons have accessible names; menus keyboard-operable, Escape closes and returns focus to trigger; destructive actions visually separated; confirmation dialogs name the asset/scope and consequence.
- **status:** NOT_RUN

### TC-LAY6-01 — Copy/microcopy consistency spot check
- **requirement_ids:** LAY-6, NFR-001
- **priority:** Low | **type:** UI | **automation_status:** MANUAL
- **steps:** Review delivered pages for terminology.
- **expected_result:** Sentence case; consistent terms (`asset tag`, `custodian`); no user-blaming errors; strict formats show examples; no long all-caps labels; dates/numbers formatted per locale utilities.
- **status:** NOT_RUN
