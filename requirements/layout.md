# Asset Inventory Web Application Layout and UX Specification

## 1. Document Information

- **Application:** Asset Inventory Web Application
- **Document:** Responsive Layout, Dark Theme, and User Experience Specification
- **Version:** 1.0
- **Status:** Initial end-user layout requirements
- **Primary display modes:** Mobile phone, tablet, laptop, and desktop PC
- **Required default appearance:** Dark theme
- **Related documents:** `specification.md`, `front-back-end-stack.md`, and `detail-design-specification.md`

## 2. Purpose

This document defines the required information architecture, responsive behavior, page layouts, visual language, dark-theme design, accessibility expectations, and interaction patterns for the Asset Inventory Web Application.

The application must provide the same essential business capabilities on mobile phones and desktop PCs. Mobile layouts must prioritize field work such as searching, scanning, checking assets, updating condition, transferring assets, and performing stocktakes. Desktop layouts must support high-density tasks such as administration, bulk operations, comparison, reporting, and reviewing large asset lists.

This document describes user experience and layout requirements. Business rules are defined in `specification.md`; technology choices are defined in `front-back-end-stack.md`; exact component contracts and implementation details must be finalized in `detail-design-specification.md`.

## 3. Design Principles

The interface must follow these principles:

1. **Fast to understand:** Users must immediately recognize the current page, primary action, important status, and next step.
2. **Mobile-first responsiveness:** Start with a usable phone layout and progressively enhance it for larger screens.
3. **Dark by default:** All pages and states must be designed intentionally for a dark theme rather than produced by simply inverting light colors.
4. **Task-oriented:** Frequently used inventory actions must require as few steps as practical.
5. **Consistent:** Navigation, terminology, status presentation, forms, confirmations, and feedback must behave consistently.
6. **Accessible:** Target WCAG 2.2 Level AA, including keyboard navigation, visible focus, semantic structure, sufficient contrast, and alternatives to color-only meaning.
7. **Evidence-based:** Actions must show accurate state, timestamps, errors, warnings, and saved results.
8. **Safe:** Destructive, sensitive, or irreversible actions must be clearly distinguished and confirmed.
9. **Progressive disclosure:** Show essential information first and reveal advanced details when needed.
10. **No hidden desktop dependency:** A user must not need a desktop browser to complete ordinary operational work.

## 4. Supported Viewports and Breakpoints

Use content-driven responsive behavior, with the following target ranges as implementation guidance:

- **Compact phone:** 320 to 479 CSS pixels
- **Phone:** 480 to 767 CSS pixels
- **Tablet:** 768 to 1023 CSS pixels
- **Laptop:** 1024 to 1439 CSS pixels
- **Desktop:** 1440 CSS pixels and above

Requirements:

- The interface must remain usable at 320 CSS pixels without page-level horizontal scrolling.
- Users must be able to zoom browser content to at least 200 percent without losing core functionality.
- Layout changes must be tested around content breakpoints, not only on named device sizes.
- Dense tables may use an intentional card, stacked-row, or column-priority alternative on narrow screens.
- Dialogs must become full-screen sheets or pages on compact screens when necessary.
- Touch targets should be at least 44 by 44 CSS pixels for primary interactive controls where practical.
- Safe-area insets must be respected on devices with notches or home indicators.
- Mobile onscreen keyboards must not hide the active field or primary form actions.

## 5. Theme Requirements

### 5.1 Default Theme

- Dark theme is the default and required fully supported theme.
- The application may provide a user-selectable light or system theme later, but dark theme must not depend on a light-theme implementation.
- Theme preference should persist for the user when theme selection is enabled.
- No unthemed flash should appear during initial loading.
- Browser chrome metadata, loading screens, charts, maps if used, form controls, scrollbars where configurable, and printable content must be considered separately.

### 5.2 Dark Theme Color Tokens

Use semantic design tokens rather than hard-coded colors in individual components. The following palette is the initial visual direction and may be refined during accessibility testing:

```text
color-bg-canvas:            #090D14
color-bg-sidebar:           #0D131D
color-bg-surface:           #121A26
color-bg-surface-raised:    #182231
color-bg-input:             #0E1622
color-bg-hover:             #1D2A3A
color-border-subtle:        #263445
color-border-strong:        #3A4A5E

color-text-primary:         #F3F6FA
color-text-secondary:       #B8C4D1
color-text-muted:           #8795A6
color-text-disabled:        #667384

color-accent-primary:       #5EA2FF
color-accent-primary-hover: #83B7FF
color-accent-on-primary:    #061221
color-focus-ring:           #8CC8FF

color-success:              #4FD1A1
color-warning:              #F4C95D
color-danger:               #FF6B78
color-info:                 #63B3ED
```

Rules:

- Final text and component color combinations must meet applicable WCAG 2.2 AA contrast requirements.
- Primary body text must use `color-text-primary` or an equivalent high-contrast token.
- Secondary and muted text must remain readable and must not be used for essential instructions when contrast is insufficient.
- Borders must be visible against adjoining surfaces without becoming visually dominant.
- Focus indicators must be clearly visible against every component background.
- Alert colors must include an icon and text label, not color alone.
- Pure black backgrounds and pure white body text should be avoided across large areas to reduce visual harshness.

### 5.3 Asset Status Presentation

Each asset status must have:

- A plain-language label
- A consistent icon or symbol
- A semantic color treatment
- A high-contrast badge style
- A text equivalent for assistive technology

Suggested category treatment:

- Available, completed, verified: success treatment
- Reserved, in transit, pending approval: informational treatment
- Maintenance due, expiring, overdue: warning treatment
- Missing, lost, stolen, failed, blocked: danger treatment
- Draft, retired, disposed, archived: neutral treatment

Do not rely on green, yellow, or red alone. The exact database status must be readable in text.

### 5.4 Typography

- Use a modern system or approved sans-serif font with excellent screen readability.
- Use a consistent type scale based on approximately 14 to 16 pixels for normal body text.
- The default desktop body size should be approximately 16 pixels; compact metadata may use 14 pixels when contrast and spacing remain sufficient.
- Avoid body text smaller than 14 pixels.
- Use clear heading levels with semantic HTML.
- Asset tags, serial numbers, identifiers, API-style values, and codes may use a readable monospace font.
- Do not use all-uppercase text for long labels or messages.
- Line length for long-form content should normally stay near 60 to 80 characters.

### 5.5 Elevation and Shape

- Use restrained elevation appropriate for a dark interface.
- Distinguish surfaces through background tone, border, and shadow rather than shadow alone.
- Cards and panels should use medium rounded corners, approximately 8 to 12 pixels.
- Modals and large sheets may use approximately 12 to 16 pixel corner radii on larger screens.
- Avoid excessive glass effects, neon glows, gradients, or animation that distracts from inventory work.

## 6. Application Shell

### 6.1 Desktop and Laptop Shell

For widths of approximately 1024 pixels and above, use:

```text
+-------------------------------------------------------------------+
| Top bar: page context | global search | actions | alerts | profile |
+----------------------+--------------------------------------------+
|                      |                                            |
| Persistent sidebar   | Main content area                          |
|                      |                                            |
| Dashboard            | Breadcrumbs / page title / primary action |
| Assets               | Filters / content / detail panels          |
| Stocktakes           |                                            |
| Maintenance          |                                            |
| Reports              |                                            |
| Administration       |                                            |
|                      |                                            |
+----------------------+--------------------------------------------+
```

Desktop requirements:

- Use a persistent left navigation sidebar.
- Support expanded and collapsed sidebar modes.
- Keep the main content width fluid while applying sensible maximum widths to forms and long text.
- Full-width lists and reports may use the available content width.
- Keep the page title and main action visible near the top.
- Use a sticky table header for long desktop lists.
- Do not create nested scrolling regions unless they provide clear value and remain keyboard accessible.

### 6.2 Tablet Shell

For tablet widths:

- The sidebar may default to collapsed icon mode or become a temporary navigation drawer.
- Keep the top bar compact.
- Use two-column layouts only when each column remains comfortably usable.
- Complex forms may retain a main column plus summary panel in landscape orientation and collapse to one column in portrait orientation.
- Tables must hide lower-priority columns or provide a responsive row-detail pattern.

### 6.3 Mobile Shell

For phone widths, use:

```text
+----------------------------------+
| Header: menu | title | context   |
+----------------------------------+
| Search or page-specific toolbar  |
+----------------------------------+
|                                  |
| Single-column page content       |
|                                  |
| Cards / stacked fields / forms   |
|                                  |
+----------------------------------+
| Bottom navigation or action bar  |
+----------------------------------+
```

Mobile requirements:

- Use a single-column primary layout.
- Use a compact top app bar.
- Use bottom navigation for the most frequent destinations when validated by the final information architecture.
- Recommended bottom destinations are Home, Assets, Scan, Tasks, and More.
- The Scan action may be visually prominent but must have a text label.
- Secondary navigation belongs in a full-height drawer or the More area.
- Primary task actions may use a sticky bottom action bar when this does not hide content.
- Do not use hover-only behavior.
- Avoid placing important controls only in swipe gestures or long-press menus.
- Respect safe areas and provide enough bottom padding so content is not hidden by navigation.

## 7. Global Navigation

### 7.1 Primary Navigation

Navigation must be role-aware and may contain:

- Dashboard
- Assets
- Assignments and Transfers
- Stocktakes
- Maintenance
- Approvals
- Reports
- Imports and Exports
- Notifications
- Administration
- Help

Users must not see inaccessible modules. Hiding navigation does not replace backend authorization.

### 7.2 Navigation Behavior

- The active section must be visually and programmatically identifiable.
- Navigation labels must use plain language.
- Badges may show actionable counts such as pending approvals or overdue tasks.
- Badges must avoid unnecessary alarm and must have accessible labels.
- Preserve the user's return position when navigating from a list to a detail page and back where practical.
- Deep links must open the correct permitted page after authentication.
- Browser back and forward behavior must remain predictable.

### 7.3 Breadcrumbs

- Show breadcrumbs on desktop for nested areas such as asset detail, stocktake detail, and administration.
- On mobile, replace long breadcrumb trails with a clear back action and concise parent context.
- Breadcrumbs must not be the only method of navigation.

## 8. Global Header and Search

### 8.1 Global Header

The desktop header should include:

- Current page or organization context
- Global search
- Quick-create or action menu when authorized
- Notification indicator
- Help access
- User profile and session menu

The mobile header should include only the controls necessary for the current context. Move additional actions into an accessible overflow menu.

### 8.2 Global Asset Search

- Search must be available within one action from any primary page.
- Search must support asset tag, serial number, asset name, model, custodian, and location.
- The field must have a visible label or accessible name, not placeholder-only identification.
- Exact asset-tag or scan matches should be presented first.
- Recent searches may be shown locally when privacy rules allow.
- Search suggestions must be keyboard navigable.
- Loading, no-match, error, and restricted-result states must be clear.
- On mobile, search may expand into a dedicated full-screen search view.

## 9. Page Header Pattern

Every primary page must use a consistent header structure:

1. Breadcrumb or parent context
2. Page title
3. Short supporting description or key metadata when useful
4. Primary action
5. Secondary actions in an overflow menu when space is constrained
6. Optional status, saved-state, or last-refreshed information

On mobile:

- Keep the title concise.
- Place only one primary action prominently.
- Move low-frequency actions to an overflow menu.
- Allow long asset names to wrap without pushing actions off-screen.

## 10. Dashboard Layout

### 10.1 Desktop Dashboard

Recommended structure:

```text
Page title and scope selector                         Primary action

[KPI: Total] [KPI: Assigned] [KPI: Available] [KPI: Exceptions]

[Assets by status chart        ] [Tasks and approvals              ]
[Assets by category chart      ] [Warranty / maintenance alerts   ]

[Recent activity              ] [Stocktake progress               ]
```

Desktop requirements:

- Use a responsive 12-column grid.
- KPI cards should display a label, value, context, and optional trend without decorative clutter.
- Charts must include accessible summaries and a data-table alternative where needed.
- Selecting a KPI or chart segment should open the corresponding filtered list.
- User-specific tasks and exceptions should be more prominent than decorative analytics.

### 10.2 Mobile Dashboard

- Use one column.
- Show the most actionable cards first.
- KPI cards may use a two-column grid if each card remains readable at 320 pixels.
- Charts may be simplified, horizontally scrollable only within their own clearly indicated region, or replaced by ranked lists.
- Provide a concise `View all` link for longer task and activity lists.
- Do not require users to interpret tiny chart labels.

## 11. Asset Register and List Layout

### 11.1 Desktop List

The desktop asset register must support a data-table view with:

- Selection checkbox, when bulk actions are authorized
- Asset tag
- Asset name
- Category
- Status
- Condition
- Custodian
- Department
- Location
- Updated date
- Row actions

Requirements:

- Asset tag and asset name must remain easily identifiable.
- Support sortable column headers with clear sort direction.
- Use a sticky list toolbar and table header for long results where appropriate.
- Support configurable visible columns.
- Preserve user column preferences where permitted.
- Allow density selection only if all modes remain accessible.
- Row actions must also be reachable by keyboard.
- Selection must persist only within a clearly defined result context.

### 11.2 Mobile List

Replace the wide table with asset summary cards or stacked rows containing:

- Asset tag
- Asset name
- Status badge
- Category or model
- Current custodian
- Current location
- Important warning, such as overdue maintenance
- Accessible row action menu

Requirements:

- Tapping the main card area opens asset details.
- Interactive controls inside a card must not trigger accidental navigation.
- Provide a compact or comfortable density option only if necessary.
- Do not horizontally squeeze the desktop table into the viewport.

### 11.3 Filtering

Desktop:

- Use a visible filter bar for common filters.
- Advanced filters may open in a side panel.
- Show active filters as removable chips.
- Display the result count and a clear-all action.

Mobile:

- Use a prominent Filter button with an active-filter count.
- Open filters in a full-height bottom sheet or full-screen panel.
- Keep Apply and Clear actions visible.
- Preserve unsaved filter changes when temporarily viewing another control in the same panel.

Filters may include category, status, condition, department, location, custodian, supplier, warranty state, maintenance due state, update date, and data-quality state.

### 11.4 Pagination

- Desktop may use numbered pagination with previous and next controls.
- Mobile should use simple previous and next controls or a tested incremental-loading pattern.
- Do not implement infinite scrolling when it prevents users from reaching footer controls, understanding position, or returning to a previous result position.
- Announce result changes to assistive technology without unexpectedly moving keyboard focus.

## 12. Asset Detail Layout

### 12.1 Desktop Asset Detail

Recommended structure:

```text
Breadcrumbs
Asset tag + asset name           Status / condition       Primary action
Key identity and assignment summary

[Overview] [Assignment] [Maintenance] [Documents] [Activity] [Audit*]

Main detail content                               Context summary panel
```

The page must show, near the top:

- Asset image or category icon
- Asset tag
- Asset name
- Category, manufacturer, and model
- Status and condition
- Custodian
- Department and location
- Primary contextual action

Use tabs or section navigation for extensive information. Preserve the selected section in the URL when practical.

### 12.2 Mobile Asset Detail

- Use a compact identity header.
- Place status and condition immediately under the asset name.
- Show key assignment and location information before secondary metadata.
- Replace desktop tabs with horizontally scrollable accessible tabs, an anchored section selector, or stacked accordions.
- Use a sticky bottom action area for the main permitted action, such as Assign, Transfer, Return, or Update condition.
- Place dangerous or rare actions in an overflow menu, separated from routine actions.
- Keep identifiers selectable and provide an explicit Copy action.

### 12.3 Activity Timeline

- Display lifecycle events in reverse chronological order by default.
- Each event must show type, actor, timestamp, and meaningful summary.
- Use icons and labels, not color alone.
- Grouping by date is permitted.
- Long details should use progressive disclosure.
- Filters may narrow event type and date range.
- Sensitive details must remain hidden when the user lacks permission.

## 13. Forms

### 13.1 Form Layout

Desktop:

- Use a maximum readable form width.
- Use two columns only for short, related fields.
- Use one column for long text, complex selectors, file upload, and important explanations.
- A right-side summary or progress panel may be used for complex workflows.

Mobile:

- Use one column.
- Place field labels above inputs.
- Use input types that open the appropriate mobile keyboard.
- Keep important Save, Continue, or Submit actions available without hiding fields.
- Do not use two small fields in one row unless they remain comfortably operable at 320 pixels.

### 13.2 Form Behavior

- Clearly mark required fields using text and a consistent symbol.
- Explain optional fields when ambiguity is likely.
- Do not use placeholders as the only labels.
- Validate at helpful moments without interrupting normal entry.
- Show errors beside the affected field and summarize errors at the top after submission.
- Move focus to the error summary or first invalid field after failed submission.
- Preserve entered values after validation failures.
- Warn users before abandoning unsaved changes.
- Disable submit only when necessary; otherwise allow submission to reveal validation guidance.
- Prevent duplicate submission while a request is being processed.
- Show a clear saved result and the resulting record or next step.

### 13.3 Long Forms and Wizards

Use a step-based workflow for complex operations such as bulk import, stocktake creation, transfer approval, and disposal.

A wizard must:

- Show current step and total steps.
- Allow safe backward navigation.
- Preserve entered information.
- Validate each step appropriately.
- Provide a review screen before an irreversible commit.
- Explain whether progress is saved as a draft.
- Avoid forcing short, simple forms into unnecessary steps.

## 14. Operational Workflow Layouts

### 14.1 Assignment

The assignment flow must prioritize:

1. Asset identity and current status
2. New custodian or destination
3. Department and location
4. Assignment and expected-return dates
5. Acknowledgement requirement
6. Notes and supporting evidence
7. Review and confirmation

On mobile, scanning an asset should be available before or during the flow.

### 14.2 Transfer

The transfer flow must clearly distinguish:

- Current custody and location
- Destination custody and location
- In-transit state
- Approval requirement
- Recipient confirmation

Use a side-by-side `From` and `To` comparison on desktop and vertically stacked sections on mobile.

### 14.3 Return

The return flow must prominently capture:

- Observed condition
- Missing accessories or damage
- Return destination
- Resulting lifecycle status
- Photo or document evidence when required

### 14.4 Maintenance

The maintenance page must separate:

- Open maintenance work
- Maintenance history
- Scheduled or upcoming work
- Cost information, when authorized
- Attachments and service evidence

Overdue work must be easy to identify without relying on color alone.

### 14.5 Retirement and Disposal

- Use a clear warning treatment.
- Show unresolved assignments, reservations, transfers, or maintenance that block completion.
- Require users to review asset identity and consequences.
- Separate retirement from final disposal.
- Require explicit confirmation for final disposal.
- Do not use a vague `OK` button. Use action-specific text such as `Confirm disposal`.

## 15. Stocktake and Mobile Scanning

### 15.1 Stocktake Session Page

Desktop should show:

- Session name, scope, status, dates, and progress
- Expected, observed, missing, unexpected, moved, duplicate, and condition-mismatch counts
- Operator assignments
- Variance list and reconciliation actions
- Session activity

Mobile should prioritize:

- Session progress
- Current location
- Scan action
- Last scanned asset
- Found or exception result
- Quick condition update
- Recent scans

### 15.2 Scanner Experience

- Scanning must request camera permission only when the user initiates scanning.
- Explain why camera access is needed.
- Provide a visible scan frame and plain-language instruction.
- Provide torch control when the browser and device support it.
- Provide manual tag entry as a permanent fallback.
- Use vibration or sound feedback only when supported, allowed, and not relied upon as the sole feedback.
- Show a clear visual result after every scan.
- Distinguish successful, duplicate, unexpected, unavailable, and unknown-code results.
- Avoid automatically committing destructive changes immediately after a scan.
- Allow rapid consecutive scanning during stocktake without losing result accuracy.

### 15.3 Limited Connectivity

When connectivity is weak:

- Show connection state without blocking the entire interface unnecessarily.
- Do not claim a change is saved until the backend confirms it.
- Preserve safe in-progress input when practical.
- Provide a clear Retry action.
- If offline stocktake is implemented later, queued and synchronized observations must be visibly distinguished and protected from duplication.

## 16. Reports and Data Visualization

### 16.1 Reports Layout

Desktop:

- Use a filter panel, report summary, visualization, and detailed results.
- Keep report generation or export status visible.
- Support print-friendly output where required.

Mobile:

- Put filters in a sheet or dedicated view.
- Show headline totals and exceptions before charts.
- Replace overly complex charts with ranked lists or concise summaries.
- Let users open the underlying record list.

### 16.2 Chart Requirements

- Use a dark-theme-compatible chart palette.
- Provide sufficient contrast between adjacent series.
- Do not rely on color alone; include labels, patterns where practical, or direct values.
- Provide accessible names and text summaries.
- Tooltips must be operable by keyboard when the chart library permits.
- Avoid 3D charts.
- Avoid pie or donut charts with too many categories.
- Use consistent status colors throughout the application.

## 17. Import and Export Layout

### 17.1 Import Wizard

Use the following steps:

1. Download or review template
2. Upload CSV file
3. Map columns when required
4. Validate and preview
5. Select authorized duplicate and partial-success policy
6. Confirm import
7. Monitor processing
8. Review and download result report

The validation view must clearly show:

- Valid rows
- Warning rows
- Error rows
- Duplicate candidates
- Field and row errors

Desktop may use a table for row review. Mobile must provide summarized results and readable row-detail views rather than a compressed table.

### 17.2 Export

- Export must show selected scope, filters, format, and included fields.
- Sensitive excluded fields should be explained when appropriate.
- Large exports must show queued, processing, completed, failed, and expired states.
- Completed downloads must include a clear file name and generation time.

## 18. Administration Layout

Desktop administration may use a secondary section navigation for:

- Users and roles
- Categories and attributes
- Status and transition rules
- Locations and departments
- Suppliers and cost centers
- Notification rules
- Import templates
- Security and retention configuration

Mobile requirements:

- Administration remains usable for urgent, simple changes.
- Large permission matrices and advanced configuration may use a guided, vertically stacked editor.
- Do not present a desktop matrix shrunk below readability.
- Warn users before changes that affect many records or permissions.

## 19. Components and Interaction States

Every reusable component must define relevant states:

- Default
- Hover, where a pointer exists
- Focus-visible
- Active or pressed
- Selected
- Disabled
- Read-only
- Loading
- Empty
- Success
- Warning
- Error
- Unauthorized

### 19.1 Buttons

- Use one visually dominant primary button per contained task area.
- Use secondary buttons for alternative actions.
- Use ghost or tertiary buttons for low-emphasis actions.
- Use danger styling only for destructive actions.
- Button labels must describe the action, such as `Save asset` or `Start stocktake`.
- Icon-only buttons require an accessible name and tooltip where appropriate.
- Loading buttons must prevent duplicate submission while retaining their width.

### 19.2 Menus

- Menus must be keyboard operable.
- Do not hide the only route to a critical action in a context menu.
- Separate destructive actions from routine actions.
- Close menus on Escape and return focus to the trigger.

### 19.3 Tabs and Accordions

- Use tabs for peer sections when users frequently switch between them.
- Use accordions for vertically scanning optional sections on narrow screens.
- Tabs must support keyboard interaction and visible selection.
- Do not nest multiple tab systems unless unavoidable.

### 19.4 Tooltips

- Tooltips may explain unfamiliar icons or concise metadata.
- Essential instructions must not exist only in a tooltip.
- Tooltips must not require hover and must dismiss accessibly.

## 20. Feedback and Messaging

### 20.1 Toasts

Use temporary toast messages for non-critical confirmation, such as a successful copy or background request submission.

- Toasts must not contain the only evidence of an important result.
- Errors requiring user action must remain visible in the page or dialog.
- Toasts must be announced accessibly without interrupting users unnecessarily.
- Multiple toasts must not cover important mobile controls.

### 20.2 Inline Alerts

Use inline alerts for page-specific warnings, blocked actions, data-quality problems, or service degradation.

- Include severity icon, title, message, and action when applicable.
- Use concise language and explain recovery.
- Do not show raw technical details to general users.
- Include a correlation or support reference for unexpected failures.

### 20.3 Confirmation Dialogs

Confirmation is required for actions such as:

- Disposal
- Archiving
- Cancelling an active transfer
- Rejecting approvals when consequences are significant
- Applying stocktake reconciliation updates
- Importing updates to existing records
- Removing attachments
- Leaving a form with unsaved changes

Confirmation dialogs must name the asset or affected scope and state the consequence. On mobile, use a full-width bottom sheet or full-screen dialog when content would otherwise be cramped.

## 21. Loading, Empty, and Error States

### 21.1 Loading

- Show skeletons for predictable content structures.
- Use progress indicators for measured multi-step operations.
- Avoid indefinite spinners without text for long operations.
- Keep previous content visible during safe refreshes where practical.
- Do not shift the page dramatically when content loads.

### 21.2 Empty States

An empty state must explain:

- What is empty
- Why it may be empty
- What the user can do next

Distinguish between:

- No assets exist
- No results match filters
- The user lacks access
- Data failed to load
- A module is not configured

### 21.3 Error States

- Provide a plain-language explanation.
- Preserve user work where possible.
- Offer Retry, Back, Contact support, or another relevant recovery action.
- Use dedicated pages or views for 403, 404, service unavailable, and unexpected error conditions.
- Never use a successful visual treatment when only part of an operation succeeded.

## 22. Accessibility Requirements

The implementation must target WCAG 2.2 Level AA and include:

- Semantic landmarks, headings, lists, tables, forms, and buttons
- A keyboard-accessible skip link to main content
- Logical tab order
- Strong visible focus indicators
- No keyboard traps
- Escape support for dismissible overlays
- Focus containment and focus restoration for modal dialogs
- Accessible names and descriptions for controls
- Programmatically associated labels and errors
- Live-region announcements for important dynamic updates
- Captions or text alternatives for instructional media
- Alternative presentation for charts and visual summaries
- Sufficient color contrast in all states
- No color-only status or validation communication
- Support for browser zoom and text resizing
- Reduced-motion support
- Reflow at narrow widths without loss of functionality

Automated accessibility testing must be supplemented with manual keyboard testing and screen-reader-oriented checks for critical journeys.

## 23. Motion and Animation

- Motion must clarify state or spatial relationships rather than decorate routine actions.
- Keep common transitions brief, generally around 120 to 250 milliseconds.
- Respect `prefers-reduced-motion`.
- Do not use flashing, rapid pulsing, or parallax effects.
- Do not delay task completion to display an animation.
- Scanner feedback, drawer movement, and loading transitions must remain understandable when animation is disabled.

## 24. Content and Microcopy

- Use concise, respectful, task-oriented language.
- Use sentence case for titles, labels, buttons, and messages.
- Use the same business term consistently, such as `asset tag`, `custodian`, and `stocktake`.
- Prefer specific actions: `Transfer asset`, not `Submit`.
- Explain the consequence before destructive actions.
- Avoid blaming the user in error messages.
- Include field examples in help text where formats are strict.
- Display date, time, number, and currency according to configured locale while preserving unambiguous storage and API formats.

## 25. Desktop Efficiency Features

Desktop and laptop layouts should support:

- Keyboard shortcuts for documented, high-frequency non-destructive actions
- Multi-select and bulk actions
- Configurable table columns
- Saved filters and views
- Side-by-side comparison where useful
- Split view for list and detail only if responsive behavior and accessibility remain strong
- Copy actions for identifiers
- Efficient tab order and focus management

Shortcuts must not conflict with browser, assistive technology, or operating-system conventions. A shortcut reference must be available.

## 26. Mobile Efficiency Features

Mobile layouts should support:

- Scan-first entry to asset lookup and stocktake
- Sticky primary actions
- Camera capture for asset evidence
- Native date, number, telephone, and email input behavior where appropriate
- Compact location and custodian selectors with search
- Recent items and recent scans when privacy permits
- Clear network and save state
- One-handed access to high-frequency actions

Mobile usability must be verified on actual touch devices, not only through resized desktop browser windows.

## 27. Print Layout

The application must provide print-specific styling for approved printable content such as:

- Asset labels
- Asset summary
- Assignment receipt
- Transfer receipt
- Stocktake report
- Disposal record

Print requirements:

- Do not print navigation, interactive controls, dark page backgrounds, or decorative elements unnecessarily.
- Use a light print background with dark text to conserve ink and improve readability.
- Include title, record identity, generation time, and relevant filter context.
- Avoid splitting essential record groups across pages where practical.
- Barcode and QR-code output must remain scannable at the defined label size.

## 28. Performance Perception

- Show immediate interaction feedback.
- Use optimistic updates only for low-risk actions that can be safely reversed and reconciled.
- Lifecycle, assignment, transfer, approval, stocktake reconciliation, and disposal actions must display confirmed backend results before being represented as complete.
- Debounce search input appropriately without making the interface feel unresponsive.
- Avoid loading an entire large dataset into the browser.
- Lazy-load secondary tabs and heavy reports when appropriate.

## 29. Layout Acceptance Criteria

The layout is acceptable when all of the following are demonstrated:

1. Every mandatory end-user workflow is usable at 320 CSS pixels and at common desktop widths.
2. No ordinary mobile page requires page-level horizontal scrolling.
3. Desktop asset lists provide an efficient table experience and mobile lists provide readable cards or stacked rows.
4. The dark theme is consistently applied to pages, dialogs, forms, tables, charts, scanner views, notifications, and error states.
5. Text, controls, focus indicators, and status badges meet approved contrast requirements.
6. Core functionality is keyboard operable.
7. Important state and validation are not communicated by color alone.
8. Mobile primary actions remain visible and do not overlap content or system safe areas.
9. Search, filters, sorting, and navigation preserve understandable state.
10. Scanner workflows provide manual-entry fallback.
11. Forms preserve valid input after errors and warn before discarding unsaved changes.
12. Destructive actions have specific confirmation messages.
13. Charts have accessible labels or equivalent summaries.
14. Loading, empty, unauthorized, no-result, offline, and error states are implemented.
15. Browser zoom, text resizing, reduced motion, and responsive reflow are verified.
16. Actual touch-device testing and supported desktop-browser testing are completed.
17. Screenshots or other test evidence are retained for key viewport and theme states.

## 30. Required Responsive Test Matrix

At minimum, QA must test representative layouts at:

- 320 x 568 compact phone portrait
- 390 x 844 modern phone portrait
- 844 x 390 phone landscape
- 768 x 1024 tablet portrait
- 1024 x 768 tablet landscape
- 1280 x 720 laptop
- 1440 x 900 desktop
- 1920 x 1080 large desktop

For every representative size, test:

- Navigation
- Dashboard
- Asset register
- Filtering and search
- Asset detail
- Create or edit form
- Assignment or transfer
- Stocktake and scanning fallback
- Dialogs and notifications
- Loading, empty, and error states

Testing must also include browser zoom, keyboard-only usage, long translated-like text expansion, long asset names, large numbers, missing images, and high-density record sets.

## 31. Suggested Nuxt Component Mapping

The detailed design may map these patterns to Nuxt UI components or accessible project-specific components:

```text
AppShell
AppSidebar
AppTopBar
MobileBottomNavigation
PageHeader
GlobalAssetSearch
FilterBar
FilterDrawer
AssetTable
AssetCardList
AssetStatusBadge
AssetIdentityHeader
AssetActivityTimeline
ResponsiveFormSection
StickyActionBar
ConfirmActionDialog
FullScreenMobileSheet
ScannerPanel
KpiCard
AccessibleChartPanel
EmptyState
InlineAlert
ImportWizard
StocktakeProgress
NotificationCenter
```

Rules:

- Components must receive typed data.
- Business authorization must not be embedded only in visual components.
- Reusable components must expose accessible labels and relevant states.
- Responsive behavior must be documented and tested at component and end-to-end levels.

## 32. Open Design Decisions

The Team Lead and frontend agent must finalize:

1. Final brand colors, logo, and approved typography
2. Whether users may select light or system theme in addition to dark theme
3. Exact desktop sidebar width and collapse behavior
4. Final mobile bottom-navigation destinations
5. Whether desktop list-detail split view adds sufficient value
6. Final dashboard KPI priority by user role
7. Chart library and accessible data-table strategy
8. Exact label dimensions and barcode or QR-code format
9. Required keyboard shortcuts
10. Offline stocktake scope, if any
11. Maximum supported content length and localization expansion assumptions
12. Whether users may configure density and visible columns

These decisions must preserve the responsive, dark-theme, accessibility, and workflow requirements in this document.

## 33. Final User Experience Expectation

The completed application must feel like one coherent product across mobile phones and desktop PCs. Mobile users must be able to perform real inventory work efficiently in the field, while desktop users must be able to manage large record sets, reports, configuration, and audit activities without unnecessary navigation.

The dark theme must be comfortable, professional, high-contrast, and consistent. The interface must prioritize asset identity, status, custody, location, exceptions, and the next permitted action. Visual polish is important, but clarity, accessibility, speed, accuracy, and safe completion of inventory tasks take priority over decoration.
