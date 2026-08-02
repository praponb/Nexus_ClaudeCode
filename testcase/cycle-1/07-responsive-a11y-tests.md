# Cycle 1 — Responsive Matrix and Accessibility Tests (NFR-002, NFR-003; LAY-1, LAY-6, LAY-7, LAY-8)

Scope note: the layout §30 matrix is executed for **delivered pages only** (login, dashboard, asset register, asset detail, create/edit form, error pages). Assignment/stocktake/report rows of the matrix are deferred to later cycles.

Preconditions: Playwright or manual browsers; axe-core available (E2E integration or browser extension).

---

### TC-NFR-002-01 — Responsive matrix smoke (8 viewports)
- **requirement_ids:** NFR-002, LAY-1, LAY-7
- **priority:** Critical | **type:** Responsive | **automation_status:** MIXED
- **test_data / viewports:** 320×568, 390×844, 844×390, 768×1024, 1024×768, 1280×720, 1440×900, 1920×1080.
- **steps:** At each viewport, for each delivered page: verify navigation pattern correct for the breakpoint, no page-level horizontal scroll, content readable, primary actions reachable, dialogs usable. Capture a screenshot per page×viewport as evidence.
- **expected_result:** All delivered pages usable at every matrix size; layout switches (sidebar/drawer/bottom-nav; table/cards; dialog/full-screen sheet) occur at sensible breakpoints; no clipped or overlapping controls; touch targets ≥44×44px on touch sizes.
- **status:** NOT_RUN

### TC-NFR-002-02 — 320px minimum width, no horizontal scroll
- **requirement_ids:** NFR-002, LAY-1, LAY-8
- **priority:** Critical | **type:** Responsive | **automation_status:** MIXED
- **steps:** At 320×568, traverse: login → dashboard → register (with long asset names + large numbers) → detail → create form; check `document.documentElement.scrollWidth <= 320` per page and visually.
- **expected_result:** No page-level horizontal scrolling anywhere; long identifiers wrap/truncate gracefully; form fields and Save actions reachable.
- **status:** NOT_RUN

### TC-NFR-002-03 — 200% browser zoom safe
- **requirement_ids:** NFR-002, NFR-003, LAY-1
- **priority:** High | **type:** Responsive/A11y | **automation_status:** MANUAL
- **steps:** At desktop width, zoom to 200%; repeat the critical paths (login, register list, asset detail, create/edit).
- **expected_result:** No loss of content or functionality; no overlapping text/controls; reflow acceptable; sticky elements don't obscure content.
- **status:** NOT_RUN

### TC-NFR-002-04 — Content stress: long text, big numbers, missing data
- **requirement_ids:** NFR-002, LAY-7
- **priority:** Medium | **type:** Responsive | **automation_status:** MIXED
- **test_data:** asset with 200-char name, long unbroken serial string, large counts in KPIs, asset with missing optional image/data.
- **steps:** Render list + detail + dashboard with the stress data at 320px and 1440px; also simulate translated-like ~30% text expansion on labels.
- **expected_result:** No layout breakage, truncation with accessible full text (title/tooltip not required if copy action exists); missing data shows graceful placeholders/empty states.
- **status:** NOT_RUN

---

### TC-NFR-003-01 — axe-core automated scan on delivered pages
- **requirement_ids:** NFR-003, LAY-6, LAY-8
- **priority:** Critical | **type:** Accessibility | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Run axe-core against: `/login`, `/`, `/assets`, `/assets/new`, `/assets/[id]`, `/assets/[id]/edit`, `/403`, `/404` (authenticated context where needed). Record all violations.
- **expected_result:** Zero critical/serious violations; any moderate/minor findings logged as defects with severity and repro.
- **status:** NOT_RUN

### TC-NFR-003-02 — Keyboard-only pass: sign-in
- **requirement_ids:** NFR-003, LAY-6
- **priority:** Critical | **type:** Accessibility | **automation_status:** MANUAL
- **steps:** Using keyboard only (Tab/Shift+Tab/Enter/Escape): load `/login`, complete and submit the form, handle a failed login, then a successful one.
- **expected_result:** Logical tab order; every control reachable and operable; visible focus indicator on every stop; error summary receives focus after failed submit; skip link available and functional.
- **status:** NOT_RUN

### TC-NFR-003-03 — Keyboard-only pass: asset register → detail → edit
- **requirement_ids:** NFR-003, LAY-6
- **priority:** Critical | **type:** Accessibility | **automation_status:** MANUAL
- **steps:** Keyboard only: from dashboard navigate to register; operate filter controls, sort a column, paginate; open a row's asset; switch to history tab; open edit; change a field; save; dismiss the unsaved-changes guard via keyboard when cancelling.
- **expected_result:** All functionality operable; row actions reachable by keyboard; tabs support arrow-key interaction per pattern; dialogs/sheets trap focus while open and restore focus on close; Escape dismisses overlays; no keyboard traps anywhere.
- **status:** NOT_RUN

### TC-NFR-003-04 — Forms accessibility: labels, errors, required markers
- **requirement_ids:** NFR-003, LAY-6, LAY-4
- **priority:** High | **type:** Accessibility | **automation_status:** MIXED
- **steps:** On `/assets/new`, inspect with dev tools/screen reader heuristics: label association, required indication, error association; submit with errors.
- **expected_result:** Every input has a programmatically associated label (no placeholder-only labels); required fields indicated by text + symbol exposed to AT; errors linked via `aria-describedby`/equivalent; error summary at top with focus moved to it on failed submit.
- **status:** NOT_RUN

### TC-NFR-003-05 — Focus visibility on all surfaces
- **requirement_ids:** NFR-003, LAY-6
- **priority:** High | **type:** Accessibility | **automation_status:** MANUAL
- **steps:** Tab through header, sidebar, cards, table rows, menus, dialogs on dark backgrounds.
- **expected_result:** Focus ring (`#8CC8FF` token or equivalent) clearly visible against every background (canvas, surface, raised, input, hover); never removed by CSS without replacement.
- **status:** NOT_RUN

### TC-NFR-003-06 — Contrast spot check of theme tokens
- **requirement_ids:** NFR-003, LAY-2, LAY-8
- **priority:** High | **type:** Accessibility | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Compute WCAG contrast ratios for used pairings: text-primary/secondary/muted/disabled on canvas/surface/raised/input; accent-on-primary on accent; badge text on badge backgrounds; danger/warning/success text on their surfaces.
- **expected_result:** Normal text ≥4.5:1, large text/UI indicators ≥3:1 for every pairing actually used; violations filed as defects with the offending token pair.
- **status:** NOT_RUN

### TC-NFR-003-07 — Live regions and dynamic updates
- **requirement_ids:** NFR-003, LAY-6
- **priority:** Medium | **type:** Accessibility | **automation_status:** MANUAL
- **steps:** Apply filters, paginate, trigger a toast (e.g., saved view created), and observe DOM live regions.
- **expected_result:** Result-count/list changes announced via polite live region without moving focus; toasts announced accessibly without interrupting; dynamic alerts use appropriate roles.
- **status:** NOT_RUN

### TC-NFR-003-08 — Reduced motion
- **requirement_ids:** NFR-003, LAY-6
- **priority:** Medium | **type:** Accessibility | **automation_status:** MIXED
- **steps:** Emulate `prefers-reduced-motion: reduce`; navigate, open drawer/dialogs, trigger loading states.
- **expected_result:** Animations/transitions eliminated or reduced to instant/near-instant; no parallax/flashing; functionality unaffected.
- **status:** NOT_RUN

### TC-NFR-003-09 — Landmarks and heading structure
- **requirement_ids:** NFR-003, LAY-6
- **priority:** Medium | **type:** Accessibility | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Audit each delivered page for `header`/`nav`/`main`/`footer` landmarks, exactly one `h1`, logical heading hierarchy.
- **expected_result:** Semantic landmarks present; skip link targets `main`; heading levels not skipped; nav regions labeled.
- **status:** NOT_RUN
