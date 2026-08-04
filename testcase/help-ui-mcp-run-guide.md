# Help-Page UI Suite — Playwright MCP Run Guide

- **Suite:** `testcase/test-cases/help-guided-ui.json` (62 cases, `TC-HELP-01` … `TC-HELP-78`)
- **Source of truth for the assertions:** the copy shipped on `/help`
  (`frontend/app/pages/help.vue`). Each case's `objective` quotes the sentence it validates.
- **Runner:** the Playwright MCP server, driven interactively. Not `npm run test:e2e` —
  that runs the separate `frontend/tests/e2e/*.spec.ts` specs.
- **Status at authoring time:** every case is `NOT_RUN`. Nothing in this suite has been executed.

## 1. Why this suite exists

The other 34 suites in `test-cases/` are derived from
`detail-design-specification.md`. This one is derived from what the *application tells
its users*. It therefore doubles as a documentation-drift guard: if the Help copy
changes, `TC-HELP-04` fails first and the affected cases must be re-reviewed before
they are executed again.

## 2. Environment

| Item | Value |
|---|---|
| Base URL | `http://localhost:3000` |
| API base | `http://localhost:8000/api/v1` |
| Stack | `docker compose up -d` — 6 containers (postgres, redis, backend, celery-worker, celery-beat, frontend) |
| Seed | `./scripts/seed-dev.sh` — reference data, demo users, ~200 assets |

**Do not run this suite against `https://inventory.praponb.com`.** The hostname sits
behind Cloudflare Access; every path except `/api/v1/health/*` 302s to a one-time-PIN
challenge, so an automated browser never reaches the app. Testing the public host
would require an Access service token and is out of scope here.

### Playwright MCP server

Not registered yet — no `browser_*` tools exist until it is:

```bash
claude mcp add playwright --scope project -- npx @playwright/mcp@latest
# restart Claude Code, then:
claude mcp list          # expect: playwright — connected
```

`--scope project` writes `.mcp.json` at the repo root, matching how
`frontend/playwright.config.ts` is already committed.

### Credentials

Seeded users: `admin`, `manager`, `deptmgr`, `operator`, `employee`, `auditor`.
This suite uses **admin**, **employee** and **auditor**. The shared password is
`SEED_DEMO_PASSWORD` in the repo-root `.env` — read it at run time:

```bash
grep '^SEED_DEMO_PASSWORD=' .env | cut -d= -f2-
```

Never paste the password into this guide, into the JSON suite, into
`execution-status.json`, or into a screenshot. When capturing evidence on `/login`,
screenshot *before* filling the password field.

## 3. Test data prepared before the run

| Needed by | Data | How to get it |
|---|---|---|
| TC-HELP-13 | A tag that is an exact match **and** a strict prefix of other tags | `GET /api/v1/assets?q=<prefix>&page_size=5` — confirm ≥2 hits |
| TC-HELP-14…18 | A known serial / name / model / custodian / location | Read one asset detail first; search for values from *that* record |
| TC-HELP-56…60 | An existing asset's serial + manufacturer + model | Copy from any seeded asset; reuse them on a new create form |
| TC-HELP-66…68 | An asset UUID plus its current `version` | `GET /api/v1/assets/<uuid>` |
| TC-HELP-76 | An asset outside `employee`'s department scope | Find as `admin`, then attempt as `employee` |

Assets created by TC-HELP-54/55/59 are intentionally left in place (the app has no
hard delete); name them `QA Help …  <timestamp>` so they are identifiable.
TC-HELP-42 is the teardown for the saved view created by TC-HELP-40.

## 4. Suggested execution order

Run the groups in order — later groups depend on data and state created earlier.

| Order | Group | Cases | Session |
|---|---|---|---|
| 1 | Help page itself | TC-HELP-01 … 06 | admin |
| 2 | Global search | TC-HELP-10 … 23 | admin |
| 3 | Filters, chips, shareable URL | TC-HELP-30 … 39 | admin |
| 4 | Saved views (create → apply → delete) | TC-HELP-40 … 44 | admin |
| 5 | Registering assets | TC-HELP-50 … 61 | admin |
| 6 | Editing and concurrency | TC-HELP-65 … 69 | admin |
| 7 | Access and visibility | TC-HELP-45, 70 … 78 | employee, auditor, admin |

Group 7 last: it signs out of the admin session, which invalidates the state groups
1–6 rely on.

## 5. Driving the browser

Core loop per case: `browser_navigate` → `browser_snapshot` → act → assert on the
next snapshot. Prefer the accessibility snapshot over screenshots for assertions;
screenshots are evidence, not the oracle.

**Selectors.** Use accessible roles and names — the same ones already proven in
`frontend/tests/e2e/assets.spec.ts` and `auth.spec.ts`. Never use Tailwind class
names; they change with styling work.

| Target | Accessible handle |
|---|---|
| Sign-in fields | label `Username` / `Password`; button `Sign in` |
| Global search | `combobox` named *Search assets by tag, serial, name, model, custodian, or location* |
| Suggestions | `option` inside the `listbox` named *Search results* |
| Register text filter | label *Filter assets by tag, serial, name, model, custodian, or location* |
| Filter chips | group *Active filters*; remove button *Remove filter &lt;label&gt;*; button *Clear all* |
| Mobile filters | button *Open filters, N active* |
| Saved views | select *Saved view*; buttons *Save current view*, *Save view*, *Delete view* |
| Create form | button *Save asset* → *Save asset anyway*; fields *Asset tag*, *Asset name*, *Category* |
| Duplicate panel | heading *Possible duplicate assets*; links *Review* |
| Conflict | text *This asset was changed by someone else*; button *Reload latest data* |
| Errors | `alert` role for the form error summary and inline alerts |

**Timing.** The global search debounces 250 ms with a 2-character minimum; the
register filter box debounces 300 ms. Wait on the resulting DOM state
(`browser_wait_for` on the listbox or the result-count text), never on a fixed sleep.

**Viewports.** `browser_resize` to 1440×900 for desktop cases; 375×812 for
TC-HELP-06 and TC-HELP-39. The top-bar *New asset* and *Help* controls are `sm:`
and up — TC-HELP-02 and TC-HELP-51 fail spuriously at mobile width.

**Out-of-band mutations** (TC-HELP-66, TC-HELP-72, TC-HELP-76) go through the API,
not a second browser. Reuse the cookie-lifting pattern in
`frontend/tests/e2e/assets.spec.ts:60-85`: read `sessionid` and `csrftoken` from the
browser context, then send `PATCH /api/v1/assets/<uuid>` with `If-Match: <version>`
and `X-CSRFToken`.

## 6. Evidence and status

Per `testcase/README.md`, a case is **never** marked `PASSED` without executed
evidence referenced in the run.

- Screenshots → `testcase/evidence/help-ui/<TC-ID>.png` via `browser_take_screenshot`.
- For each executed case, update `testcase/execution-status.json`:

```json
"TC-HELP-13": {
  "test_id": "TC-HELP-13",
  "status": "PASSED",
  "actual_result": "Exact tag AST-0001 returned as the first option ahead of 3 prefix matches.",
  "evidence_path": "testcase/evidence/help-ui/TC-HELP-13.png",
  "cycle_last_executed": 3
}
```

- Statuses: `NOT_RUN` → `PASSED` / `FAILED` / `BLOCKED` / `MANUAL`. Use `BLOCKED`
  (not `FAILED`) when a precondition is missing — e.g. no seeded asset pair exists
  for TC-HELP-13.
- Any `FAILED` case gets a defect entry in the cycle's `defects.json` with the Help
  sentence it contradicts, since a failure here means either the app or its own
  documentation is wrong.

## 7. Ownership

Everything this suite produces lives under `testcase/`, which is QA-owned per
`CLAUDE.md`. Executing it must not modify `frontend/` or `backend/` source; a
failure is reported as a defect, not patched in place.
